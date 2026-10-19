"""Lớp dịch vụ: giao diện duy nhất để app công ty (hoặc AI sau này) gọi vào.

Mọi hàm nhận/trả dict JSON-được. Giờ là giờ địa phương của người dùng (naive, không
mang múi giờ); múi giờ lấy từ LICHVIET_TZ (mặc định Asia/Ho_Chi_Minh), xem tz.py.
Việc *gửi* nhắc không nằm ở đây: app công ty gọi due_reminders() rồi tự gửi qua
kênh thông báo sẵn có, xong gọi mark_fired().
"""
import calendar
import difflib
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from . import store
from .parser import parse_vi, fold
from .lunar import lunar_to_solar
from .tz import local_now
from .ai import LLMClient
from .stt import STTClient

REPEATS = (None, "daily", "weekly", "monthly", "lunar_yearly")


def _add_months(dt: datetime, n: int) -> datetime:
    y, m = divmod(dt.month - 1 + n, 12)
    y, m = dt.year + y, m + 1
    return dt.replace(year=y, month=m, day=min(dt.day, calendar.monthrange(y, m)[1]))


class Service:
    def __init__(self, db_path: str = ":memory:", clock=local_now, llm: Optional[LLMClient] = None,
                 stt: Optional[STTClient] = None):
        self._db_path = db_path
        self._local = threading.local()   # mỗi luồng HTTP một kết nối: transaction không lẫn giữa các yêu cầu
        self._shared = store.connect(db_path) if db_path == ":memory:" else None
        self.clock = clock
        self.llm = llm if llm is not None else LLMClient()
        self.stt = stt if stt is not None else STTClient()
        # sổ cụm từ đã học: một cụm chỉ được dùng sau khi người dùng xác nhận (bấm Lưu) từng đó lần
        self.learn_min = int(os.environ.get("LICHVIET_LEARN_MIN", "2"))
        self.catchup_days = int(os.environ.get("LICHVIET_CATCHUP_DAYS", "7"))   # nhắc bù khi máy từng tắt
        self._ai_cache = {}   # câu -> kết quả AI, để bấm Lưu không phải hỏi AI lần nữa

    @property
    def con(self):
        if self._shared is not None:
            return self._shared
        c = getattr(self._local, "con", None)
        if c is None:
            c = self._local.con = store.connect(self._db_path)
        return c

    # ---------- ghi ----------
    def create(self, title: str, start: datetime, *, duration_min=None, all_day=False,
               repeat=None, remind_before_min=None, notes=None, lunar=None) -> dict:
        """lunar = (ngày, tháng) âm lịch; dùng cùng repeat="lunar_yearly" (giỗ, sinh nhật âm)."""
        if not title.strip():
            raise ValueError("thiếu tiêu đề")
        if repeat not in REPEATS:
            raise ValueError("repeat không hợp lệ")
        if repeat == "lunar_yearly" and not lunar:
            raise ValueError("lặp theo âm lịch cần có ngày tháng âm")
        ld, lm = lunar if lunar else (None, None)
        title = title.strip()
        # lưu trùng (cùng tên, cùng giờ, cùng kiểu lặp) thì trả lại việc cũ, không tạo bản sao
        for row in self.con.execute("SELECT * FROM events WHERE start=? AND COALESCE(repeat,'')=?",
                                    (store.fmt(start), repeat or "")):
            if row["title"].casefold() == title.casefold():
                return {**dict(row), "duplicate": True}
        now = store.fmt(self.clock())
        cur = self.con.execute(
            "INSERT INTO events(title,start,duration_min,all_day,repeat,remind_before_min,notes,created,updated,"
            "lunar_day,lunar_month) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (title, store.fmt(start), duration_min, int(all_day), repeat,
             remind_before_min, notes, now, now, ld, lm))
        self.con.commit()
        return self.get(cur.lastrowid)

    def update(self, event_id: int, **fields) -> dict:
        allowed = {"title", "start", "duration_min", "all_day", "repeat", "remind_before_min", "notes",
                   "lunar_day", "lunar_month"}
        bad = set(fields) - allowed
        if bad:
            raise ValueError("trường không hợp lệ: %s" % ", ".join(sorted(bad)))
        if not fields:
            return self.get(event_id)
        if "repeat" in fields and fields["repeat"] not in REPEATS:
            raise ValueError("repeat không hợp lệ")
        if "start" in fields and isinstance(fields["start"], datetime):
            fields["start"] = store.fmt(fields["start"])
        if "all_day" in fields:
            fields["all_day"] = int(fields["all_day"])
        sets = ", ".join("%s=?" % k for k in fields)
        cur = self.con.execute("UPDATE events SET %s, updated=? WHERE id=?" % sets,
                               (*fields.values(), store.fmt(self.clock()), event_id))
        if cur.rowcount == 0:
            raise KeyError(event_id)
        self.con.execute("DELETE FROM fired WHERE event_id=?", (event_id,))
        self.con.commit()
        return self.get(event_id)

    def delete(self, event_id: int) -> bool:
        cur = self.con.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.con.execute("DELETE FROM fired WHERE event_id=?", (event_id,))
        self.con.commit()
        return cur.rowcount > 0

    # ---------- đọc ----------
    def get(self, event_id: int) -> Optional[dict]:
        row = self.con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None

    def _lunar_occurrences(self, ev: dict, s: datetime, lo: datetime, hi: datetime):
        d, m = ev["lunar_day"], ev["lunar_month"]
        if not d or not m:
            return
        for ly in range(lo.year - 1, hi.year + 2):
            sd = None
            for use in ([d, 29] if d == 30 else [d]):  # tháng thiếu không có 30 thì cúng ngày 29
                sd = lunar_to_solar(use, m, ly)
                if sd:
                    break
            if not sd or sd < s.date():
                continue
            o = datetime.combine(sd, s.time())
            if lo <= o < hi:
                yield o

    def _occurrences(self, ev: dict, lo: datetime, hi: datetime):
        s = store.parse(ev["start"])
        rep = ev["repeat"]
        if not rep:
            if lo <= s < hi:
                yield s
            return
        if rep == "lunar_yearly":
            yield from self._lunar_occurrences(ev, s, lo, hi)
            return
        step = {"daily": lambda i: s + timedelta(days=i),
                "weekly": lambda i: s + timedelta(weeks=i),
                "monthly": lambda i: _add_months(s, i)}[rep]
        i = 0
        if rep != "monthly":
            unit = 1 if rep == "daily" else 7
            i = max(0, int((lo - s).total_seconds() // 86400) // unit - 1)
        for _ in range(100000):
            o = step(i)
            if o >= hi:
                return
            if o >= lo:
                yield o
            i += 1

    def list_range(self, lo: datetime, hi: datetime) -> list:
        """Các lần xảy ra trong [lo, hi), đã bung lịch lặp, sắp theo giờ."""
        out = []
        for row in self.con.execute("SELECT * FROM events"):
            ev = dict(row)
            for o in self._occurrences(ev, lo, hi):
                out.append({**ev, "occurrence": store.fmt(o)})
        return sorted(out, key=lambda e: (e["occurrence"], e["id"]))

    def day(self, d: datetime) -> list:
        lo = d.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.list_range(lo, lo + timedelta(days=1))

    def conflicts(self, start: datetime, duration_min: Optional[int], exclude_id=None) -> list:
        """Sự kiện có giờ trùng khoảng [start, start+duration). Mặc định 60 phút."""
        dur = timedelta(minutes=duration_min or 60)
        out = []
        for e in self.list_range(start - timedelta(days=1), start + dur):
            if e["all_day"] or e["id"] == exclude_id:
                continue
            es = store.parse(e["occurrence"])
            ee = es + timedelta(minutes=e["duration_min"] or 60)
            if es < start + dur and start < ee:
                out.append(e)
        return out

    # ---------- câu lệnh tiếng Việt ----------
    def _ai_extract(self, text: str):
        """Hỏi AI, nhớ kết quả 10 phút: bản nháp và lúc bấm Lưu dùng chung một câu trả lời."""
        key = " ".join(fold(text).split())
        hit = self._ai_cache.get(key)
        if hit and time.time() - hit[0] < 600:
            self.llm.last = {**hit[2], "detail": "dùng lại kết quả lần hỏi vừa rồi"}
            return hit[1]
        ex = self.llm.extract(text)
        if ex:
            if len(self._ai_cache) > 50:
                self._ai_cache.clear()
            self._ai_cache[key] = (time.time(), ex, dict(self.llm.last))
        return ex

    def _apply_phrases(self, text: str):
        """Thay các cụm từ đã học (đủ số lần xác nhận) bằng cách nói bộ luật hiểu được."""
        rows = self.con.execute("SELECT src,dst FROM phrases WHERE hits>=? ORDER BY length(src) DESC",
                                (self.learn_min,)).fetchall()
        used = []
        for row in rows:
            f = fold(text)
            m = re.search(r"(?<![a-z0-9])" + re.escape(row["src"]) + r"(?![a-z0-9])", f)
            if m:
                text = text[:m.start()] + row["dst"] + text[m.end():]
                used.append(row["src"])
                self.con.execute("UPDATE phrases SET uses=uses+1 WHERE src=?", (row["src"],))
        if used:
            self.con.commit()
        return text, used

    def _learn(self, text: str, ex: dict, r_ai) -> None:
        """Sau khi người dùng Lưu một bản nháp do AI hỗ trợ: rút ra cụm từ lạ và cách nói đơn giản tương ứng.

        Cụm lạ = phần tên việc mà bộ luật còn dư so với tên AI tách ra. Cách nói tương ứng =
        đoạn ngắn nhất của "when" mà thay vào cụm lạ thì bộ luật cho ra đúng ngày giờ AI đã đưa.
        Có kiểm tra lại như vậy nên không học những thứ không tái hiện được.
        """
        try:
            now = self.clock()
            r0 = parse_vi(text, now)
            tw, aw = r0.title.split(), ex["title"].split()
            ops = [o for o in difflib.SequenceMatcher(
                None, [fold(w) for w in tw], [fold(w) for w in aw]).get_opcodes() if o[0] != "equal"]
            if len(ops) != 1 or ops[0][0] != "delete":
                return
            src_words = [fold(w).strip(",.;:") for w in tw[ops[0][1]:ops[0][2]]]
            if not 1 <= len(src_words) <= 4 or any(any(c.isdigit() for c in w) for w in src_words):
                return
            f = fold(text)
            m = re.search(r"(?<![a-z0-9])" + r"\s+".join(re.escape(w) for w in src_words) + r"(?![a-z0-9])", f)
            if not m:
                return
            src = " ".join(src_words)
            ww = ex["when"].split()
            dst = None
            for n in range(1, min(4, len(ww)) + 1):
                for i in range(len(ww) - n + 1):
                    cand = " ".join(ww[i:i + n])
                    if fold(cand) == src:
                        continue
                    r3 = parse_vi(text[:m.start()] + cand + text[m.end():], now)
                    if not r3.missing and not r3.unsure and r3.start == r_ai.start and r3.all_day == r_ai.all_day:
                        dst = cand
                        break
                if dst:
                    break
            if not dst:
                return
            t = store.fmt(now)
            row = self.con.execute("SELECT dst,hits FROM phrases WHERE src=?", (src,)).fetchone()
            if row is None:
                self.con.execute("INSERT INTO phrases(src,dst,hits,created,updated) VALUES(?,?,1,?,?)",
                                 (src, dst, t, t))
            elif fold(row["dst"]) == fold(dst):
                self.con.execute("UPDATE phrases SET hits=hits+1, updated=? WHERE src=?", (t, src))
            else:   # AI đổi ý: bắt đầu đếm lại từ đầu với cách hiểu mới
                self.con.execute("UPDATE phrases SET dst=?, hits=1, updated=? WHERE src=?", (dst, t, src))
            self.con.commit()
        except Exception:
            pass   # học hỏi chỉ là phần thêm, không bao giờ được làm hỏng việc lưu

    # ---------- học cách nghe của giọng người dùng ----------
    def _apply_heard(self, text: str) -> str:
        """Sửa chữ nhận giọng bằng các lỗi nghe đã được người dùng sửa đủ số lần (cùng ngưỡng với cụm từ)."""
        rows = self.con.execute("SELECT src,dst FROM heard WHERE hits>=? ORDER BY length(src) DESC",
                                (self.learn_min,)).fetchall()
        for row in rows:
            toks = text.split()
            ft = [fold(t).strip(",.;:!?") for t in toks]
            sw = row["src"].split()
            n = len(sw)
            for i in range(len(toks) - n + 1):
                if ft[i:i + n] == sw:
                    tail = toks[i + n - 1][len(toks[i + n - 1].rstrip(",.;:!?")):]
                    toks[i:i + n] = [row["dst"] + tail]
                    text = " ".join(toks)
                    self.con.execute("UPDATE heard SET uses=uses+1 WHERE src=?", (row["src"],))
                    self.con.commit()
                    break
        return text

    def transcribe(self, wav: bytes) -> str:
        return self._apply_heard(self.stt.transcribe(wav))

    def learn_heard(self, heard: str, fixed: str) -> int:
        """Người dùng sửa chữ nhận giọng rồi mới gửi: nhớ cặp "nghe ra X nhưng ý là Y".
        Chỉ học thay thế ngắn (1 đến 3 từ), phía nghe sai không chứa số; thay đổi nội dung (đổi giờ, đổi tên) thì bỏ qua."""
        a = [w for w in (heard or "").split()]
        b = [w for w in (fixed or "").split()]
        fa = [w.lower().strip(",.;:!?") for w in a]   # giữ dấu: "tạng" và "tăng" khác nhau, khác với cách so khớp
        fb = [w.lower().strip(",.;:!?") for w in b]
        ops = [o for o in difflib.SequenceMatcher(None, fa, fb).get_opcodes() if o[0] != "equal"]
        if not ops or len(ops) > 2:
            return 0
        t = store.fmt(self.clock())
        learned = 0
        for tag, i1, i2, j1, j2 in ops:
            if tag != "replace" or not 1 <= i2 - i1 <= 3 or not 1 <= j2 - j1 <= 3:
                continue
            raw_src = " ".join(fa[i1:i2])
            src = fold(raw_src)
            dst = " ".join(b[j1:j2]).strip(",.;:!?")
            if not src or any(c.isdigit() for c in src) or raw_src == dst.lower():
                continue
            if not any(c.isdigit() for c in dst):   # sửa chữ thành chữ: chỉ học khi hai bên đọc gần giống nhau
                if difflib.SequenceMatcher(None, src, fold(dst)).ratio() < 0.5:
                    continue
            row = self.con.execute("SELECT dst FROM heard WHERE src=?", (src,)).fetchone()
            if row is None:
                self.con.execute("INSERT INTO heard(src,dst,hits,created,updated) VALUES(?,?,1,?,?)", (src, dst, t, t))
            elif fold(row["dst"]) == fold(dst):
                self.con.execute("UPDATE heard SET hits=hits+1, updated=? WHERE src=?", (t, src))
            else:
                self.con.execute("UPDATE heard SET dst=?, hits=1, updated=? WHERE src=?", (dst, t, src))
            learned += 1
        self.con.commit()
        return learned

    def heard_list(self) -> list:
        return [dict(r) for r in self.con.execute("SELECT * FROM heard ORDER BY hits DESC, uses DESC")]

    def forget_heard(self, src: str) -> bool:
        cur = self.con.execute("DELETE FROM heard WHERE src=?", (fold(src).strip(),))
        self.con.commit()
        return cur.rowcount > 0

    def phrases(self) -> list:
        """Sổ cụm từ đã học (để xem hoặc kiểm tra)."""
        return [dict(r) for r in self.con.execute("SELECT * FROM phrases ORDER BY hits DESC, uses DESC")]

    def forget_phrase(self, src: str) -> bool:
        cur = self.con.execute("DELETE FROM phrases WHERE src=?", (fold(src).strip(),))
        self.con.commit()
        return cur.rowcount > 0

    # ---------- câu lệnh tiếng Việt ----------
    def from_text(self, text: str, *, save: bool = False) -> dict:
        """Phân tích câu lệnh. save=False: chỉ trả bản nháp để người dùng xác nhận."""
        text2, memo = self._apply_phrases(text)   # cụm từ đã học: khỏi gọi AI
        r = parse_vi(text2, self.clock())
        used_ai = False
        ai_note = None
        ex = None
        if r.missing or r.unsure:  # chỉ gọi AI khi luật chưa hiểu hoặc còn cụm ngày lạ
            ex = self._ai_extract(text)
            if ex and (ex["title"] or ex["when"]):
                r2 = parse_vi((ex["title"] + " " + ex["when"]).strip(), self.clock())
                better = len(r2.missing) < len(r.missing) or (r.unsure and not r2.unsure and not r2.missing)
                if better:
                    r, used_ai = r2, True
                else:
                    self.llm.last = {**self.llm.last, "status": "not_better",
                                     "detail": "AI trả lời nhưng kết quả vẫn chưa hiểu được ngày giờ"}
            ai_note = dict(self.llm.last)
        draft = {"title": r.title, "start": store.fmt(r.start) if r.start else None,
                 "all_day": r.all_day, "duration_min": r.duration_min, "repeat": r.repeat,
                 "remind_before_min": r.remind_before_min, "warnings": r.warnings, "used_ai": used_ai, "ai": ai_note,
                 "lunar": list(r.lunar) if r.lunar else None, "memory": memo or None}
        if r.missing:
            return {"status": "need_info", "missing": r.missing, "draft": draft}
        now = self.clock()
        if r.start < (now.replace(hour=0, minute=0, second=0, microsecond=0) if r.all_day else now) and not r.repeat:
            draft["warnings"] = list(draft["warnings"]) + ["thời điểm này đã qua, bạn kiểm tra lại ngày giờ"]
        conflicts = [] if r.all_day else self.conflicts(r.start, r.duration_min)
        res = {"status": "draft", "draft": draft, "conflicts": conflicts}
        if save:
            ev = self.create(r.title, r.start, duration_min=r.duration_min, all_day=r.all_day,
                             repeat=r.repeat, remind_before_min=r.remind_before_min, lunar=r.lunar)
            res.update(status="saved", event=ev)
            if used_ai and ex and not ev.get("duplicate"):
                self._learn(text, ex, r)   # người dùng đã xác nhận: ghi nhớ cách nói này
        return res

    # ---------- sao lưu / khôi phục ----------
    def export_all(self) -> dict:
        """Toàn bộ dữ liệu người dùng (việc, cụm từ đã học) để lưu thành tệp. Gỡ app là mất volume, nên cần cái này."""
        evs = [dict(r) for r in self.con.execute("SELECT * FROM events ORDER BY id")]
        fired = [dict(r) for r in self.con.execute("SELECT * FROM fired")]
        return {"format": "lichviet-backup", "version": 1, "exported": store.fmt(self.clock()),
                "events": evs, "fired": fired, "phrases": self.phrases(), "heard": self.heard_list()}

    def import_all(self, data: dict) -> dict:
        """Nhập lại từ tệp sao lưu. Gộp thêm, không xóa gì: việc trùng (cùng tên, giờ, kiểu lặp) bị bỏ qua."""
        if not isinstance(data, dict) or data.get("format") != "lichviet-backup":
            raise ValueError("đây không phải tệp sao lưu của Trợ lý thời gian")
        try:
            res = self._import_rows(data)
            self.con.commit()
            return res
        except Exception as e:
            self.con.rollback()   # không nhập nửa chừng
            if isinstance(e, ValueError):
                raise
            raise ValueError("tệp sao lưu không hợp lệ: %s" % type(e).__name__)

    def _import_rows(self, data: dict) -> dict:
        added = skipped = 0
        idmap = {}
        for e in data.get("events", []):
            if not isinstance(e, dict):
                raise ValueError("tệp sao lưu không hợp lệ: việc không đúng dạng")
            title = (e.get("title") or "").strip()
            start = e.get("start")
            if not title or not start:
                skipped += 1
                continue
            store.parse(start)   # sai định dạng thì báo lỗi, không nhập nửa chừng
            rep = e.get("repeat") or None
            if rep not in REPEATS:
                skipped += 1
                continue
            if rep == "lunar_yearly" and not (e.get("lunar_day") and e.get("lunar_month")):
                skipped += 1
                continue
            dup = [r for r in self.con.execute("SELECT id,title FROM events WHERE start=? AND COALESCE(repeat,'')=?",
                                               (start, rep or "")) if r["title"].casefold() == title.casefold()]
            if dup:
                idmap[e.get("id")] = dup[0]["id"]
                skipped += 1
                continue
            now = store.fmt(self.clock())
            cur = self.con.execute(
                "INSERT INTO events(title,start,duration_min,all_day,repeat,remind_before_min,notes,created,updated,"
                "lunar_day,lunar_month) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (title, start, e.get("duration_min"), int(bool(e.get("all_day"))), rep, e.get("remind_before_min"),
                 e.get("notes"), e.get("created") or now, now, e.get("lunar_day"), e.get("lunar_month")))
            idmap[e.get("id")] = cur.lastrowid
            added += 1
        for f in data.get("fired", []):
            if f.get("event_id") in idmap:   # lần nhắc đã gửi: giữ nguyên để không nhắc lại
                self.con.execute("INSERT OR IGNORE INTO fired VALUES(?,?)", (idmap[f["event_id"]], f["occ_start"]))
        learned = 0
        for ph in data.get("phrases", []):
            if ph.get("src") and ph.get("dst"):
                t = store.fmt(self.clock())
                cur = self.con.execute("INSERT OR IGNORE INTO phrases(src,dst,hits,uses,created,updated) VALUES(?,?,?,?,?,?)",
                                       (ph["src"], ph["dst"], int(ph.get("hits") or 0), int(ph.get("uses") or 0),
                                        ph.get("created") or t, t))
                learned += cur.rowcount
        for h in data.get("heard", []):
            if h.get("src") and h.get("dst"):
                t = store.fmt(self.clock())
                self.con.execute("INSERT OR IGNORE INTO heard(src,dst,hits,uses,created,updated) VALUES(?,?,?,?,?,?)",
                                 (h["src"], h["dst"], int(h.get("hits") or 0), int(h.get("uses") or 0),
                                  h.get("created") or t, t))
        return {"added": added, "skipped": skipped, "phrases": learned}

    # ---------- nhắc việc ----------
    def _stages(self, ev: dict) -> list:
        """Các mốc nhắc của một việc: (hậu tố khóa, nhắc trước bao lâu, loại)."""
        on_time = ("", timedelta(minutes=ev["remind_before_min"] or 0), "on_time")
        if ev["repeat"] == "lunar_yearly":  # giỗ: nhắc sớm để còn chuẩn bị
            return [("#7d", timedelta(days=7), "prepare_7d"),
                    ("#1d", timedelta(days=1), "prepare_1d"), on_time]
        return [on_time]

    def due_reminders(self) -> list:
        """Các lần nhắc đã đến giờ mà chưa gửi.

        Mỗi phần tử có "key": truyền key đó (hoặc "occurrence" với việc thường) vào
        mark_fired() sau khi gửi. Việc thường nhắc đúng giờ (trừ remind_before_min);
        việc cả ngày nhắc lúc 8h sáng; giỗ (lặp âm lịch) nhắc thêm trước 7 ngày và 1 ngày.
        """
        now = self.clock()
        out = []
        horizon_hi = now + timedelta(days=8)
        for row in self.con.execute("SELECT * FROM events"):
            ev = dict(row)
            # Việc lặp ngày/tuần/tháng: chỉ nhìn lùi 1 ngày (tránh dồn hàng loạt lần nhắc cũ sau khi máy tắt lâu).
            # Việc một lần và giỗ: nhìn lùi catchup ngày để nhắc bù khi máy từng tắt.
            back = 1 if ev["repeat"] in ("daily", "weekly", "monthly") else self.catchup_days
            for o in self._occurrences(ev, now - timedelta(days=back), horizon_hi):
                base = o.replace(hour=8, minute=0) if ev["all_day"] else o
                due = []
                for suffix, delta, kind in self._stages(ev):
                    fire_at = base - delta
                    if fire_at > now:
                        continue
                    if ev["created"] > store.fmt(fire_at):
                        continue  # việc tạo sau mốc này (kể cả việc lưu với giờ đã qua), không nhắc
                    due.append((suffix, kind))
                if not due:
                    continue
                suffix, kind = due[-1]  # chỉ giữ mốc gần nhất đã tới, bỏ các mốc cũ hơn chưa kịp gửi
                key = store.fmt(o) + suffix
                sent = self.con.execute("SELECT 1 FROM fired WHERE event_id=? AND occ_start=?",
                                        (ev["id"], key)).fetchone()
                if not sent:
                    out.append({"event_id": ev["id"], "title": ev["title"], "occurrence": store.fmt(o),
                                "key": key, "kind": kind, "days_left": (o.date() - now.date()).days,
                                "all_day": bool(ev["all_day"]),
                                "remind_before_min": ev["remind_before_min"] or 0})
        return sorted(out, key=lambda x: (x["occurrence"], x["key"]))

    def mark_fired(self, event_id: int, occurrence: str) -> None:
        """occurrence: truyền "key" của lần nhắc (với việc thường key trùng occurrence)."""
        self.con.execute("INSERT OR IGNORE INTO fired VALUES(?,?)", (event_id, occurrence))
        self.con.commit()
