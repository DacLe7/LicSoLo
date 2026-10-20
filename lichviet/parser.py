"""Bộ phân tích câu lệnh lịch tiếng Việt theo luật (không dùng AI).

Hỗ trợ có dấu và không dấu. Sau này LLM chỉ cần trích cụm thời gian thô;
việc quy đổi ra ngày giờ luôn do file này làm.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from typing import Optional

from .lunar import lunar_to_solar, next_solar, next_lunar_monthly


def fold(s: str) -> str:
    """Bỏ dấu, chữ thường; giữ nguyên độ dài để chỉ số khớp với văn bản gốc."""
    out = []
    for ch in s.lower():
        if ch == "đ":
            out.append("d")
            continue
        d = unicodedata.normalize("NFD", ch)
        out.append(d[0] if d else ch)
    return "".join(out)


NUMW = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9,
        "muoi": 10, "muoi mot": 11, "muoi hai": 12}
WEEKDAYS = {"hai": 0, "ba": 1, "tu": 2, "nam": 3, "sau": 4, "bay": 5,
            "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5, "cn": 6, "nhat": 6}


@dataclass
class ParseResult:
    title: str = ""
    start: Optional[datetime] = None
    all_day: bool = False
    duration_min: Optional[int] = None
    repeat: Optional[str] = None          # daily | weekly | monthly | yearly | lunar_yearly | lunar_monthly
    remind_before_min: Optional[int] = None
    warnings: list = field(default_factory=list)
    unsure: bool = False   # còn cụm ngày mà luật không hiểu
    lunar: Optional[tuple] = None   # (ngày, tháng) âm lịch nếu câu nói theo âm lịch

    @property
    def missing(self):
        m = []
        if not self.title:
            m.append("title")
        if self.start is None:
            m.append("start")
        return m


def _mask(f: str, m: re.Match) -> str:
    return f[:m.start()] + " " * (m.end() - m.start()) + f[m.end():]


def _unit_min(n: int, unit: str) -> int:
    return n * {"phut": 1, "gio": 60, "tieng": 60, "ngay": 1440, "tuan": 10080}[unit]


def _valid_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


_ANNIV = re.compile(r"\b(?:sinh\s+nhat|ky\s+niem|thoi\s+noi)\b")


def _next_anniversary(dd: int, mm: int, today: date, year: Optional[int] = None) -> Optional[date]:
    """Ngày bắt đầu cho việc lặp hằng năm theo dương lịch: lần gần nhất chưa qua.

    29/2: lấy ngày 29/2 của năm nhuận gần nhất (có thể đã qua) để các năm không nhuận
    rơi vào 28/2 mà năm nhuận vẫn đúng 29/2 (bung lịch lặp tính từ ngày bắt đầu).
    """
    if _valid_date(2000, mm, dd) is None:   # 2000 là năm nhuận: loại 31/4, 30/2...
        return None
    if (mm, dd) == (2, 29):
        if year is not None:
            return _valid_date(year, 2, 29)
        y = today.year
        while _valid_date(y, 2, 29) is None:
            y -= 1
        return date(y, 2, 29)
    if year is not None:
        d = _valid_date(year, mm, dd)
        if d is None or d >= today:
            return d
    d = date(today.year, mm, dd)
    return d if d >= today else date(today.year + 1, mm, dd)


_PERIOD_VI = {"sang": "sáng", "trua": "trưa", "chieu": "chiều", "toi": "tối", "dem": "đêm", "khuya": "khuya"}
_NEXT_UNITS = {"tuan", "thang", "nam", "lan", "dip", "ky"}
# "ăn tối", "bữa trưa", "ca sáng", "cơm tối", "tiệc tối": buổi là một phần tên việc
_MEAL_BEFORE = {"an": "ăn", "bua": "bữa", "ca": "ca", "com": "cơm", "tiec": "tiệc"}


def _shift_months(dt: datetime, n: int) -> datetime:
    """Cộng/trừ n tháng, ngày cuối tháng thì kẹp lại (31/3 - 1 tháng = 28/2 hoặc 29/2)."""
    y, mo = divmod(dt.year * 12 + dt.month - 1 + n, 12)
    mo += 1
    for dd in range(dt.day, 27, -1):
        d = _valid_date(y, mo, dd)
        if d:
            break
    else:
        d = date(y, mo, dt.day)
    return datetime.combine(d, dt.time()).replace(second=0, microsecond=0)


def _parse_core(text: str, now: datetime) -> ParseResult:
    f = fold(text)
    f0_core = f
    spans = []  # (start, end) đã dùng, để cắt khỏi tiêu đề
    r = ParseResult()

    def take(pattern, flags=0):
        nonlocal f
        m = re.search(pattern, f, flags)
        if m:
            spans.append((m.start(), m.end()))
            f = _mask(f, m)
        return m

    # 1) nhắc trước: "nhắc (tôi) trước 2 ngày", "nhắc (tôi) 2 ngày trước", "báo trước 30 phút"
    who = r"(?:(?:toi|em|anh|chi)\s+)?"
    m = take(r"\b(?:nhac|bao)\s+" + who + r"truoc\s+(\d+)\s*(phut|gio|tieng|ngay)\b") or \
        take(r"\b(?:nhac|bao)\s+" + who + r"(\d+)\s*(phut|gio|tieng|ngay)\s+truoc\b")
    if m:
        r.remind_before_min = _unit_min(int(m.group(1)), m.group(2))
    take(r"\b(?:nhac|giup)\s+toi\b")  # "tôi" ở đây là đại từ, không phải buổi tối

    # 2) thời lượng
    m = take(r"\b(?:keo\s+dai|trong|mat)\s+(\d+)\s*(phut|gio|tieng)\b")
    if m:
        r.duration_min = _unit_min(int(m.group(1)), m.group(2))

    # 3) lặp lại
    day = None
    m = take(r"\b(?:moi|hang)\s+ngay\b")
    if m:
        r.repeat = "daily"
    elif take(r"\b(?:moi|hang)\s+nam\b(?!\s*(?:phut|gio|tieng|ngay|hom|tuan|thang|lan)\b)"):
        r.repeat = "yearly"   # "sinh nhật 20/11 hằng năm" (dương lịch); âm lịch đổi thành lunar_yearly ở parse_vi
    else:
        m = take(r"\b(?:moi|hang)\s+thang\b")
        if m:
            r.repeat = "monthly"
        else:
            m = take(r"\b(?:moi|hang)\s+tuan\b")
            if m:
                r.repeat = "weekly"
            else:
                m = take(r"\bmoi\s+(?:thu\s+(hai|bay|ba|tu|nam|sau|[2-7])|(chu\s+nhat))\b")
                if m:
                    r.repeat = "weekly"
                    day = WEEKDAYS["cn" if m.group(2) else m.group(1)]
                else:
                    # "mỗi sáng 7h", "hằng tối" = mỗi ngày; "mỗi sáng thứ hai" = hằng tuần (thứ để luật thứ trong tuần đọc).
                    # Chỉ bỏ chữ "mỗi/hằng", giữ buổi để đoán giờ. Câu có dấu phải đúng chữ ("mời tối" không phải "mỗi tối").
                    for m in re.finditer(r"\b(?:moi|hang)\s+(?=(?:sang|trua|chieu|toi|dem)\b)", f):
                        if f0_core != text.lower() and not re.match(r"(?i)(?:mỗi|hằng|hàng)\s", text[m.start():]):
                            continue
                        weekday = re.match(r"(?:sang|trua|chieu|toi|dem)\s+(?:thu\s+(?:hai|ba|tu|nam|sau|bay|[2-7])|chu\s+nhat)\b",
                                           f[m.end():])
                        r.repeat = "weekly" if weekday else "daily"
                        spans.append(m.span())
                        f = _mask(f, m)
                        break

    # 4) sau N phút/giờ/ngày  (tương đối so với bây giờ)
    rel = None
    rel_days = False
    # "sau 3 ngày", "3 ngày nữa", "2 tuần nữa"; "3 ngày trước", "1 tuần trước" (đã qua)
    # "sau 2 giờ chiều" là mốc giờ, không phải 2 tiếng nữa; "ngày 5 tháng tới" là ngày cụ thể
    not_clock = r"(?!\s*(?:sang|trua|chieu|toi|dem|khuya)\b)"
    not_dom = r"(?<!ngay )(?<!mung )(?<!mong )"
    m = take(r"\bsau\s+(\d+)\s*(phut|gio|tieng|ngay|tuan)\b" + not_clock) or \
        take(r"\b" + not_dom + r"(\d+)\s*(phut|gio|tieng|ngay|tuan)\s+nua\b") or \
        take(r"\b" + not_dom + r"(\d+)\s*(ngay|tuan)\s+toi\b")   # "3 giờ tới" dễ lẫn "3 giờ tối"
    mm_ = None if m else (take(r"\bsau\s+(\d+)\s*(thang|nam)\b(?!\s*\d)") or
                          take(r"\b" + not_dom + r"(\d+)\s*(thang|nam)\s+(?:nua|toi)\b"))
    if m:
        rel_days = m.group(2) in ("ngay", "tuan")
        rel = now + timedelta(minutes=_unit_min(int(m.group(1)), m.group(2)))
        if rel_days:
            rel = rel.replace(second=0, microsecond=0)
    elif mm_:
        rel_days = True
        rel = _shift_months(now, int(mm_.group(1)) * (12 if mm_.group(2) == "nam" else 1))
    else:
        m = take(r"\b(\d+)\s*(ngay|hom|tuan)\s+(?:ve\s+)?truoc\b") or \
            take(r"\b" + not_dom + r"(\d+)\s*(thang|nam)\s+(?:ve\s+)?truoc\b")
        if m:
            rel_days = True
            if m.group(2) in ("thang", "nam"):
                rel = _shift_months(now, -int(m.group(1)) * (12 if m.group(2) == "nam" else 1))
            else:
                n = int(m.group(1)) * (7 if m.group(2) == "tuan" else 1)
                rel = (now - timedelta(days=n)).replace(second=0, microsecond=0)

    # "cả ngày": chỉ là dấu hiệu việc không có giờ, không thuộc tên việc
    take(r"\bca\s+ngay\b")

    # 5) ngày
    d: Optional[date] = None
    m = take(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?\b") or \
        take(r"\b(?:(?:ngay|mung|mong)\s+)?(\d{1,2})\s+thang\s+(\d{1,2})(?:\s+nam\s+(\d{4}))?\b")
    if m:
        dd, mm = int(m.group(1)), int(m.group(2))
        yy = int(m.group(3)) if m.group(3) else now.year
        has_year = bool(m.group(3))
        if not has_year:   # "20/11 năm sau", "5/3 năm ngoái"
            my = take(r"\bnam\s+(sau|toi|ngoai|truoc|roi|nay)\b")
            if my:
                yy, has_year = now.year + {"sau": 1, "toi": 1, "nay": 0}.get(my.group(1), -1), True
        if r.repeat is None and not has_year and _ANNIV.search(f0_core):
            r.repeat = "yearly"   # sinh nhật, kỷ niệm có ngày mà không nói năm: năm nào cũng có
            r.warnings.append("sinh nhật, ngày kỷ niệm: đã đặt lặp hằng năm, bấm Sửa nếu chỉ một lần")
        if r.repeat == "yearly":
            d = _next_anniversary(dd, mm, now.date(), yy if has_year else None)
            if d is None:
                r.warnings.append("ngày không hợp lệ")
            elif d.month == 2 and d.day == 29:
                r.warnings.append("29/2 chỉ có ở năm nhuận, năm khác sẽ nhắc vào 28/2")
        else:
            d = _valid_date(yy, mm, dd)
            if d is None:
                r.warnings.append("ngày không hợp lệ")
            elif not has_year and d < now.date():
                d = _valid_date(yy + 1, mm, dd)
    elif (m := take(r"\b(?:ngay|mung|mong)\s+(\d{1,2})\s+thang\s+(sau|toi|nay)\b")):
        # "ngày 5 tháng tới", "mùng 10 tháng này"
        base = _shift_months(now.replace(day=1), 0 if m.group(2) == "nay" else 1)
        d = _valid_date(base.year, base.month, int(m.group(1)))
        if d is None:
            r.warnings.append("ngày không hợp lệ")
    if d is None and not r.warnings and r.repeat == "monthly":
        m = take(r"\b(?:ngay|mung|mong)\s+(\d{1,2})\b")
        if m and 1 <= int(m.group(1)) <= 31:
            dom, today = int(m.group(1)), now.date()
            y, mo = today.year, today.month
            for _ in range(13):   # tháng nào có ngày này thì lấy; ngày đã qua trong tháng này thì sang tháng sau
                if not (y == today.year and mo == today.month and dom < today.day):
                    d = _valid_date(y, mo, dom)
                    if d:
                        break
                mo += 1
                if mo > 12:
                    y, mo = y + 1, 1
            if d is None:
                r.warnings.append("không tìm được tháng có ngày %d" % dom)
    if d is None and not r.warnings:
        m = re.search(r"\b(?:sang|trua|chieu|toi|dem|khuya)\s+(nay)\b", f)
        if take(r"\b(?:bua\s+)?(?:hom|bua)\s+nay\b"):
            d = now.date()
        elif m:
            spans.append((m.start(1), m.end(1)))
            f = f[:m.start(1)] + " " * 3 + f[m.end(1):]
            d = now.date()
        elif take(r"\bngay\s+mai\b|\bmai\b"):
            d = now.date() + timedelta(days=1)
        elif take(r"\bngay\s+kia\b"):
            d = now.date() + timedelta(days=2)
        elif take(r"\b(?:bua\s+)?(?:hom|bua)\s+qua\b"):
            d = now.date() - timedelta(days=1)   # service sẽ cảnh báo "đã qua" khi lưu
        elif take(r"\bhom\s+kia\b"):
            d = now.date() - timedelta(days=2)
        elif (m := take(r"\bbua\s+hom\b(?!\s+(?:nay|kia|sau))|\bhom\s+bua\b")):
            # "bữa hổm", "hôm bữa" = mấy hôm trước, không rõ ngày: tạm đặt 3 ngày trước để người dùng chỉnh
            d = now.date() - timedelta(days=3)
            r.warnings.append("\"%s\" không rõ là ngày nào, tạm đặt 3 ngày trước, bạn chỉnh lại nếu khác"
                              % text[m.start():m.end()].lower())
    if d is None and not r.warnings:
        # cụm mơ hồ: "cuối tuần (này/sau)", "đầu tuần sau", "cuối tháng", "đầu tháng sau"
        unit = "tuan"
        m = take(r"\b(cuoi|dau)\s+tuan(?:\s+(nay|sau|toi|truoc)\b)?")
        if not m:
            unit = "thang"  # "đầu tháng 11" là ngày cụ thể, để luật khác xử lý
            m = take(r"\b(cuoi|dau)\s+thang(?:\s+(nay|sau|toi|truoc)\b|(?!\s*\d))")
        if m:
            edge, q = m.group(1), m.group(2)
            today = now.date()
            if unit == "tuan":
                shift = {"sau": 7, "toi": 7, "truoc": -7}.get(q, 0)
                monday = today - timedelta(days=today.weekday()) + timedelta(days=shift)
                d = monday + timedelta(days=5 if edge == "cuoi" else 0)
                if d < today and q != "truoc":  # cuối tuần đang diễn ra thì lấy hôm nay, đầu tuần đã qua thì lấy tuần sau
                    d = today if edge == "cuoi" else d + timedelta(days=7)
                if edge == "cuoi":
                    r.warnings.append("\"cuối tuần\" tạm đặt thứ Bảy, bạn chỉnh nếu khác")
            else:
                first = today.replace(day=1)
                nxt = (first + timedelta(days=32)).replace(day=1)
                prev = (first - timedelta(days=1)).replace(day=1)
                base = nxt if q in ("sau", "toi") else prev if q == "truoc" else first
                if edge == "dau":
                    d = base if q else nxt
                else:
                    d = (base + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            # ngày đã qua nhưng không rõ ngày: "tháng trước", "năm ngoái" -> tạm cùng ngày tháng/năm trước, có cảnh báo
            m = take(r"\bthang\s+truoc\b") or take(r"\bnam\s+(?:ngoai|truoc|roi)\b")
            if m:
                d = _shift_months(now, -12 if m.group().startswith("nam") else -1).date()
                r.warnings.append("\"%s\" không rõ là ngày nào, tạm đặt %s, bạn chỉnh lại nếu khác"
                                  % (text[m.start():m.end()].lower(), d.strftime("%d/%m/%Y")))
    if d is None and not r.warnings:
        m = take(r"\b(?:thu\s+(hai|bay|ba|tu|nam|sau|[2-7])|(chu\s+nhat))\s*(tuan\s+(?:sau|toi|nay|truoc)|nay\b)?")
        if m or day is not None:
            wd = day if m is None else WEEKDAYS["cn" if m.group(2) else m.group(1)]
            q = (m.group(3) or "") if m else ""
            monday = now.date() - timedelta(days=now.weekday())
            if "sau" in q or "toi" in q:
                d = monday + timedelta(days=7 + wd)
            elif "truoc" in q:
                d = monday + timedelta(days=wd - 7)
            elif q == "nay":   # "thứ bảy này": lần tới gần nhất, kể cả hôm nay
                d = now.date() + timedelta(days=(wd - now.weekday()) % 7)
            elif "nay" in q:
                d = monday + timedelta(days=wd)
            else:
                d = now.date() + timedelta(days=(wd - now.weekday() - 1) % 7 + 1)
        else:
            if take(r"\btuan\s+(?:sau|toi)\b"):
                d = now.date() + timedelta(days=7)
            elif take(r"\btuan\s+truoc\b"):
                d = now.date() - timedelta(days=7)

    # 6) giờ
    hh = mi = None
    tspan = None
    kem = 0
    rng = None
    # khoảng giờ: "từ 2h đến 4h chiều", "9h-11h", "từ 8 tới 10h" -> giờ bắt đầu + thời lượng
    m = take(r"(?<!thu )\btu\s+(\d{1,2})\s*(?:h|gio|:)?\s*(\d{2})?\s*(?:-|den|toi)\s*(\d{1,2})\s*(?:h(?![a-z])|gio|:)\s*(\d{2})?\b(?:\s*phut)?") or \
        take(r"\b(\d{1,2})\s*(?:h|gio|:)\s*(\d{2})?\s*(?:-|den)\s*(\d{1,2})\s*(?:h(?![a-z])|gio|:)\s*(\d{2})?\b(?:\s*phut)?")
    if m:
        hh, mi = int(m.group(1)), int(m.group(2) or 0)
        rng = (int(m.group(3)), int(m.group(4) or 0), hh)
        tspan = (m.start(), m.end())
    # "3 giờ kém 15" = 2:45; "ba giờ kém mười lăm"
    m = None if rng else take(r"\b(?:(\d{1,2})\s*(?:h(?![a-z])|gio)|(mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?:\s+(?:mot|hai))?)\s+gio)\s+kem\s+(\d{1,2}|hai\s+muoi\s+lam|hai\s+muoi|muoi\s+lam|muoi|nam)\b(?:\s*phut)?")
    if m:
        hh = int(m.group(1)) if m.group(1) else NUMW[m.group(2).replace("  ", " ")]
        w = re.sub(r"\s+", " ", m.group(3))
        kem = int(w) if w.isdigit() else {"nam": 5, "muoi": 10, "muoi lam": 15, "hai muoi": 20, "hai muoi lam": 25}[w]
        mi = 0
        tspan = (m.start(), m.end())
    elif not rng:
        # "9 rưỡi sáng" (bỏ chữ giờ) cũng là giờ
        m = take(r"\b(?:(\d{1,2})\s*(?:h(?![a-z])|gio|:|(?=\s+ruoi\b))|(mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?:\s+(?:mot|hai))?)\s+gio)\s*(?:(\d{2})\b|(?<=h)(\d)\b|(ruoi)\b)?(?:\s*phut)?")
        if m:
            hh = int(m.group(1)) if m.group(1) else NUMW[m.group(2).replace("  ", " ")]
            mi = 30 if m.group(5) else int(m.group(3) or m.group(4) or 0)
            tspan = (m.start(), m.end())
    period = None
    midnight12 = False
    early = False
    if take(r"\bnua\s+dem\b"):   # "nửa đêm (nay)" = 0 giờ kết thúc ngày đó
        if hh is None:
            hh, mi, midnight12 = 0, 0, True
    ms_som = re.search(r"\bsang\s+(som)\b", f)
    if ms_som:   # "sáng sớm": sớm hơn buổi sáng thường, chỉ dùng khi không nói giờ
        early = True
        spans.append(ms_som.span(1))
        f = f[:ms_som.start(1)] + "   " + f[ms_som.end(1):]
    ms = list(re.finditer(r"\b(sang|trua|chieu|toi|dem|khuya)\b", f))
    # "tôi" là đại từ sau các động từ này ("gọi tôi 8h"), không phải buổi tối
    _PRON_BEFORE = {"goi", "nhac", "bao", "cho", "hoi", "voi", "keu", "gap", "nho", "dan", "cung"}
    ms = [x for x in ms if not (x.group(1) == "toi" and (f[:x.start()].split() or [""])[-1] in _PRON_BEFORE)]
    # câu gõ có dấu: "hộ chiếu", "chiếu phim", "tới" không phải buổi
    if f0_core != text.lower():
        ms = [x for x in ms if text[x.start():x.end()].lower() == _PERIOD_VI[x.group(1)]]
    # "tuần tới", "tháng tới", "năm tới": "tới" chứ không phải buổi tối
    ms = [x for x in ms if not (x.group(1) == "toi" and (f0_core[:x.start()].split() or [""])[-1] in _NEXT_UNITS)]

    def is_meal(x):
        w = (f0_core[:x.start()].split() or [""])[-1]
        if w not in _MEAL_BEFORE:
            return False
        if f0_core != text.lower():   # câu có dấu: đúng chữ "ăn/bữa/ca/cơm/tiệc" ("cà", "an" thì không)
            return (text[:x.start()].split() or [""])[-1].lower() == _MEAL_BEFORE[w]
        return True
    meal = [x for x in ms if is_meal(x)]
    meal_pos = {x.start() for x in meal}
    ms = [x for x in ms if x.start() not in meal_pos]
    if tspan:  # chỉ lấy từ chỉ buổi sát cạnh giờ ("3h chiều", "tối 7h")
        # chỉ cách nhau bởi khoảng trắng (từ ngày như "chủ nhật", "mai" đã bị che): "tối chủ nhật 8h"
        def gap(x):
            g = f[tspan[1]:x.start()] if x.start() >= tspan[1] else f[x.end():tspan[0]] if x.end() <= tspan[0] else "x"
            return len(g) if not g.strip() else None
        ms = sorted((x for x in ms if gap(x) is not None), key=gap)
        if not ms:  # "tối nay 8h", "tối mai 8h": buổi đứng cạnh từ ngày thì vẫn áp cho giờ
            ms = [x for x in re.finditer(r"\b(sang|trua|chieu|toi|dem|khuya)\s+(?:nay|mai|kia)\b", fold(text))
                  if x.start() not in meal_pos][-1:]  # "nay" đã bị che ở bước ngày
    else:
        ms = ms[-1:]
    for m in ms[:1]:
        period = "dem" if m.group(1) == "khuya" else m.group(1)
        spans.append((m.start(), m.end()))
        f = _mask(f, m)
    if period is None and meal:   # "ăn tối 7h" = 19h, "ăn tối mai" = 19h mai; chữ vẫn ở lại trong tên
        period = "dem" if meal[0].group(1) == "khuya" else meal[0].group(1)
    raw_hh = hh
    if hh is not None:
        if hh > 24 or mi > 59:
            r.warnings.append("giờ không hợp lệ")
            hh = None
        elif period == "toi" and hh == 12:   # "12h tối nay" = nửa đêm, không phải 12h trưa
            hh = 0
            midnight12 = True
        elif period in ("chieu", "toi") and hh < 12:
            hh += 12
        elif period == "trua" and 1 <= hh < 6:
            hh += 12
        elif period == "dem" and hh == 12:
            hh = 0
            midnight12 = True
        elif period == "dem" and 6 <= hh < 12:   # "10h đêm", "11 giờ khuya" = 22h, 23h
            hh += 12
        if hh == 24:
            hh = 0
        # giờ nói ngược thói quen của buổi ("3 giờ tối", "15h sáng", "9h chiều"): vẫn đặt theo luật nhưng nhắc kiểm tra
        odd = raw_hh is not None and hh is not None and not rng and not kem and (
            (period == "toi" and 1 <= raw_hh <= 4) or (period == "sang" and raw_hh >= 13)
            or (period == "chieu" and 9 <= raw_hh <= 11) or (period == "trua" and 6 <= raw_hh <= 10))
        if odd:
            r.warnings.append("giờ %d ít khi đi với buổi %s, tạm đặt %02d:%02d, bạn kiểm tra lại"
                              % (raw_hh, _PERIOD_VI[period], hh, mi))
        if kem and hh is not None:   # "3 giờ kém 15": trừ sau khi đã áp buổi (chiều → 15 → 14:45)
            hh, mi = hh - 1, 60 - kem
            if hh < 0:
                hh = 23
        if rng and hh is not None:
            eh, em, raw = rng
            if eh > 24 or em > 59:
                r.warnings.append("giờ kết thúc không hợp lệ")
            else:
                e = (eh + 12 if period in ("chieu", "toi") and eh < 12 else
                     eh + 12 if period == "trua" and 1 <= eh < 6 else
                     eh + 12 if period == "dem" and 6 <= eh < 12 else eh) * 60 + em
                if hh * 60 + mi > e:   # "từ 11h đến 1h chiều": buổi chỉ áp cho giờ kết thúc
                    hh = raw
                st = hh * 60 + mi
                if e <= st:
                    e += 720 if eh < 12 and e + 720 > st else 1440   # "từ 10h đến 2h" = 14h; "22h-2h" qua đêm
                if r.duration_min is None:
                    r.duration_min = e - st

    # 7) ghép ngày giờ
    if "ngày không hợp lệ" in r.warnings:   # "31/4": không đoán ngày, để thiếu ngày và hỏi lại
        r.start, r.all_day = None, False
    elif rel is not None:
        if rel_days and hh is not None:   # "sau 3 ngày lúc 9h": ngày theo N, giờ theo người nói
            r.start = datetime.combine(rel.date(), time(hh, mi))
        elif rel_days:
            r.start = datetime.combine(rel.date(), time(0, 0))
            r.all_day = True
        else:
            r.start = rel
    elif hh is not None:
        if midnight12 and d is not None:   # "12h đêm nay" = nửa đêm kết thúc ngày đó
            d = d + timedelta(days=1)
        if d is None:
            cand = now.replace(hour=hh, minute=mi, second=0, microsecond=0)
            d = cand.date() if cand > now else cand.date() + timedelta(days=1)
        r.start = datetime.combine(d, time(hh, mi))
    elif d is not None and period is not None:   # "sáng mai", "tối nay": có buổi thì không được bỏ
        h = {"sang": 6 if early else 8, "trua": 12, "chieu": 15, "toi": 19, "dem": 22}[period]
        r.start = datetime.combine(d, time(h, 0))
        r.warnings.append("chỉ nói buổi, tạm đặt %02d:00" % h)
    elif d is not None:
        r.start = datetime.combine(d, time(0, 0))
        r.all_day = True
    elif period is not None:
        h = {"sang": 6 if early else 8, "trua": 12, "chieu": 15, "toi": 19, "dem": 22}[period]
        cand = now.replace(hour=h, minute=0, second=0, microsecond=0)
        r.start = cand if cand > now else cand + timedelta(days=1)
        r.warnings.append("chỉ nói buổi, tạm đặt %02d:00" % h)

    # 8) tiêu đề: văn bản gốc trừ phần đã dùng (kể cả từ nối đứng ngay trước), bỏ từ đệm hai đầu
    f0 = fold(text)
    keep = [True] * len(text)
    for a, b in spans:
        mm = re.search(r"(?:\b(?:vao\s+luc|vao\s+ngay|vao|luc|ngay|khoang|den|truoc|sau)\s*)+$", f0[:a])
        if mm:
            a = mm.start()
        for i in range(a, b):
            keep[i] = False
    rest = "".join(c if k else " " for c, k in zip(text, keep))
    rest = re.sub(r"\s+", " ", rest).strip(" ,.;:-!?")
    ff = fold(rest)
    for m in re.finditer("nhạc|nhà", rest.lower()):  # "nhạc", "nhà" không phải "nhắc", "nha" (từ đệm)
        ff = ff[:m.start() + 2] + "x" + ff[m.start() + 3:]
    lead = r"(?:(?:nho\s+nhac|nhac\s+nho|nho|nhac)(?:\s+(?:em|anh|chi))?(?:\s+(?:cai\s+vu|cai|vu|viec))?|dat\s+lich|tao\s+lich|them\s+lich|lich|vao\s+luc|vao|luc|ngay|giup\s+toi|giup|hen|va\s+luc)"
    trail = r"(?:vao\s+luc|vao|luc|ngay|nhac|va|nhe|nha|nhen|nhi|a|di|voi|giup|nhoe|nghe)"
    for _ in range(8):
        m1 = re.match(r"^" + lead + r"\b\s*", ff)
        m2 = re.search(r"\s*\b" + trail + r"$", ff)
        if m1 and m1.end() < len(ff):
            rest, ff = rest[m1.end():], ff[m1.end():]
        elif m2:
            rest, ff = rest[:m2.start()], ff[:m2.start()]
        else:
            break
    if re.search(r"\b(?:ngay\s+mot|mung\s*\d|dau\s+thang|cuoi\s+thang|cuoi\s+tuan|thang\s+(?:sau|toi|\d+)|tuan\s+(?:sau|toi|nay)|nam\s+(?:sau|toi)|hom\s+qua)\b", ff):
        r.unsure = True
        r.warnings.append("có thể chưa hiểu cụm ngày trong câu, bạn kiểm tra lại")
    r.title = rest.strip(" ,.;:-!?")
    if r.title:
        r.title = r.title[0].upper() + r.title[1:]
    return r


# ---------------------------------------------------------------- âm lịch
_DATE_PATTERNS = (
    r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?\b",
    r"\b(?:(?:ngay|mung|mong)\s+)?(\d{1,2})\s+thang\s+(\d{1,2})(?:\s+nam\s+(\d{4}))?\b",
)


def _blank(text: str, span) -> str:
    return text[:span[0]] + " " * (span[1] - span[0]) + text[span[1]:]


def _find_lunar(text: str, f: str):
    """Tìm ngày âm lịch trong câu. Trả về (ngày, tháng, năm|None, span_ngày, span_dấu_âm|None)
    hoặc None nếu câu không nói theo âm lịch.

    Coi là âm lịch khi: có "âm lịch", hoặc chữ "âm" đứng sát ngày ("15/08 âm", "âm 15/8"),
    hoặc là đám giỗ (giỗ luôn tính theo âm lịch). Có chữ "dương" thì luôn là dương lịch.
    "học âm nhạc 5/11" không bị nhầm vì chữ "âm" không đứng sát ngày.
    """
    dm = None
    for p in _DATE_PATTERNS:
        dm = re.search(p, f)
        if dm:
            break
    if not dm:
        return None
    day, month = int(dm.group(1)), int(dm.group(2))
    year = int(dm.group(3)) if dm.group(3) else None
    if not (1 <= day <= 30 and 1 <= month <= 12):
        return None
    a, b = dm.span()
    for mk in re.finditer(r"\bam\s+lich\b|\bam\b", f):
        if "lich" in mk.group():
            return day, month, year, (a, b), mk.span()
        gap = f[mk.end():a] if mk.end() <= a else f[b:mk.start()] if mk.start() >= b else None
        if gap is not None and gap.strip() in ("", "ngay"):
            return day, month, year, (a, b), mk.span()
    if re.search(r"\bgiỗ\b", text.lower()):
        return day, month, year, (a, b), None
    return None


_MONTHLY = r"\b(?:moi|hang)\s+thang\b"


def _find_lunar_monthly(text: str, f: str):
    """"Cúng rằm mỗi tháng", "mùng 1 hàng tháng", "ngày 15 âm lịch mỗi tháng".
    Trả về (ngày âm, [span cần xóa khỏi câu]) hoặc ("nhieu", []) nếu nói nhiều ngày; None nếu không phải kiểu này."""
    mon = re.search(_MONTHLY, f)
    if not mon:
        return None
    low = text.lower()
    days, blank = [], [mon.span()]
    # cả câu gõ không dấu ("cung ram moi thang"): "ram" là rằm; câu có dấu thì phải đúng chữ "rằm"
    no_marks = f == low
    for m in re.finditer(r"\bram\b" if no_marks else r"\brằm\b", f if no_marks else low):
        days.append(15)
    for m in re.finditer(r"\b(?:mùng|mồng)\s*(\d{1,2}|một)\b", low):
        days.append(1 if m.group(1) == "một" else int(m.group(1)))
    for m in re.finditer(r"\bngay\s+(\d{1,2})\s+am(?:\s+lich)?\b", f):
        days.append(int(m.group(1)))
        blank.append(m.span())
    for m in re.finditer(r"\bam\s+lich\b", f):
        blank.append(m.span())
    days = sorted(set(days))
    if not days:
        return None
    if len(days) > 1:
        return "nhieu", []
    if not 1 <= days[0] <= 30:
        return None
    return days[0], blank


_W1 = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "lam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9}
_NUMRX = (r"(?:(?:hai|ba|bon|nam|sau|bay|tam|chin)\s+muoi(?:\s+(?:mot|hai|ba|bon|tu|lam|nam|sau|bay|tam|chin))?"
          r"|muoi(?:\s+(?:mot|hai|ba|bon|lam|nam|sau|bay|tam|chin))?|mot|hai|ba|bon|nam|sau|bay|tam|chin)")
_RELUNIT = r"(?:phut|gio|tieng|ngay|hom|tuan|thang|nam)"
# Số viết bằng chữ chỉ đổi khi chắc là số lượng: trước "đơn vị + nữa/trước/tới", sau "sau/trong/kéo dài/mất/nhắc trước".
_REL_WORD_PATTERNS = (
    r"(?<![a-z])(" + _NUMRX + r")(?=\s+" + _RELUNIT + r"(?:\s+ruoi)?\s+(?:nua|truoc|toi)\b)",
    r"\b(?:sau|trong|keo\s+dai|mat|truoc)\s+(" + _NUMRX + r")(?=\s+" + _RELUNIT + r"\b)",
    r"\b(?:ngay|mung|mong)\s+(" + _NUMRX + r")(?=\s+(?:thang\s+(?:sau|toi|nay)|(?:hang|moi)\s+thang)\b)",   # "mùng hai tháng tới", "mùng hai hàng tháng"
)


def _num_value(words: str) -> int:
    w = words.split()
    if w[0] == "muoi":
        return 10 + (_W1[w[1]] if len(w) > 1 else 0)
    if len(w) > 1 and w[1] == "muoi":
        return _W1[w[0]] * 10 + (_W1[w[2]] if len(w) > 2 else 0)
    return _W1[w[0]]


def _rel_words_to_digits(text: str) -> str:
    """Câu gõ tay: "hai ngày nữa" -> "2 ngày nữa", "ba hôm trước", "sau mười lăm phút", "nửa tiếng" -> "30 phút".
    "thứ hai tuần trước", "mùng hai tháng tới", "ngày mốt" giữ nguyên."""
    text = re.sub(r"(?i)\bnửa\s+(?:tiếng|giờ)\b", "30 phút", text)
    f = fold(text)
    hits = []
    for k, p in enumerate(_REL_WORD_PATTERNS):
        for m in re.finditer(p, f):
            a, b = m.span(1)
            prev = f[:a].split()[-1:] or [""]
            if (k == 0 and prev[0] in ("thu", "mung", "mong", "ngay", "bua")) or text[a:b].lower() == "mốt":
                continue
            hits.append((a, b, _num_value(re.sub(r"\s+", " ", m.group(1)))))
    for a, b, v in sorted(set(hits), reverse=True):
        text = text[:a] + str(v) + text[b:]
    # "1 tiếng rưỡi nữa", "trong 2 tiếng rưỡi" -> phút; "3 giờ rưỡi chiều" là giờ nên giữ nguyên
    half = lambda m: "%s%d phút" % (m.group(1) or "", int(m.group(2)) * 60 + 30)
    text = re.sub(r"(?i)()\b(\d{1,2})\s*(?:tiếng|giờ)\s+rưỡi\b(?=\s+(?:nữa|trước)\b)", half, text)
    return re.sub(r"(?i)(\b(?:sau|trong|kéo\s+dài|mất)\s+)(\d{1,2})\s*(?:tiếng|giờ)\s+rưỡi\b", half, text)


_RAM_NOTE = "đã hiểu \"ram\" là rằm (ngày 15 âm lịch), bấm Sửa nếu không phải"


def _fix_ram(text: str):
    """"ram" gõ thiếu dấu trước "tháng N"/"mỗi tháng" là rằm. Trả về (câu đã sửa, có cần nhắc không).
    Cả câu không dấu: "cung ram thang 7" -> "15 thang 7 am lich" (giữ câu không dấu để các luật khác vẫn chạy).
    Câu có dấu: "cúng ram mỗi tháng", "đi chùa ram tháng giêng" -> "rằm" kèm lời nhắc."""
    if fold(text) == text.lower():
        months = {"gieng": "1", "chap": "12"}
        return re.sub(r"(?i)\bram\s+thang\s+(\d{1,2}|gieng|chap)(?:\s+am(?:\s+lich)?)?\b(?!\s*duong)",
                      lambda m: "15 thang %s am lich" % months.get(m.group(1).lower(), m.group(1)), text), False
    new = re.sub(r"\b[Rr]am(?=\s+(?:(?:mỗi|hằng|hàng)\s+tháng|tháng\s+(?:\d{1,2}|giêng|chạp))\b)", "rằm", text)
    return new, new != text


def parse_vi(text: str, now: datetime) -> ParseResult:
    text, ram_typo = _fix_ram(unicodedata.normalize("NFC", text))
    r = _parse_vi(text, now)
    if ram_typo and r.lunar:
        r.warnings.append(_RAM_NOTE)
    return r


def _parse_vi(text: str, now: datetime) -> ParseResult:
    text = _rel_words_to_digits(text)
    # "9g sáng", "7g30" (gõ tắt giờ kiểu Nam Bộ) = 9h; "gói 4g", "sim 5g", "mạng 4g" là mạng điện thoại nên giữ nguyên
    text = re.sub(r"(?i)(?<!gói )(?<!goi )(?<!sim )(?<!mạng )(?<!mang )(?<!sóng )(?<!song )\b(\d{1,2})g(\d{2})?\b",
                  lambda m: m.group(1) + "h" + (m.group(2) or "") if int(m.group(1)) <= 24 else m.group(0), text)
    # "ngày mốt", "bữa mốt" (Nam Bộ) = ngày kia; "ngày một" (mùng 1) giữ nguyên vì có dấu khác
    text = re.sub(r"(?i)\b(?:ngày|bữa)\s+mốt\b", "ngày kia", text)
    # "tháng giêng", "tháng chạp" là tên tháng âm lịch
    text = re.sub(r"(?i)\btháng\s+giêng\b(?!\s*(?:âm|dương))", "tháng 1 âm lịch", text)
    text = re.sub(r"(?i)\btháng\s+chạp\b(?!\s*(?:âm|dương))", "tháng 12 âm lịch", text)
    text = re.sub(r"(?i)\btháng\s+(giêng|chạp)\b", lambda m: "tháng " + ("1" if m.group(1).lower() == "giêng" else "12"), text)
    text = re.sub(r"(?i)\brằm\s+tháng\s+(\d{1,2})(?:\s+âm(?:\s+lịch)?)?\b(?!\s*dương)", r"15 tháng \1 âm lịch", text)
    f = fold(text)
    if re.search(r"\bduong\b", f):  # nói rõ dương lịch: bỏ chữ đó khỏi tên việc, dùng luật thường
        for m in re.finditer(r"\bduong\s+lich\b", f):
            text = _blank(text, m.span())
        return _parse_core(text, now)

    mfound = _find_lunar_monthly(text, f)
    if mfound is not None:
        if mfound[0] == "nhieu":   # "mùng 1 và rằm hằng tháng": chưa hỗ trợ nhiều ngày trong một câu
            r = _parse_core(_blank(text, re.search(_MONTHLY, f).span()), now)
            r.start, r.all_day = None, False
            r.warnings.append("câu có nhiều ngày âm lịch, hãy tạo từng việc riêng (ví dụ một việc cho mùng 1, một việc cho rằm)")
            return r
        day, blank = mfound
        cleaned = text
        for sp in blank:
            cleaned = _blank(cleaned, sp)
        r = _parse_core(cleaned, now)
        r.repeat, r.lunar = "lunar_monthly", (day, None)
        r.unsure = False
        r.warnings = [w for w in r.warnings if w not in ("ngày không hợp lệ", "có thể chưa hiểu cụm ngày trong câu, bạn kiểm tra lại")]
        s, used29 = next_lunar_monthly(day, now.date())
        has_time = r.start is not None and not r.all_day
        r.start = datetime.combine(s, r.start.time() if has_time else time(0, 0)) if s else None
        r.all_day = not has_time and s is not None
        if used29:
            r.warnings.append("tháng âm này không có ngày 30, dùng ngày 29")
        return r

    found = _find_lunar(text, f)
    if found is None:
        return _parse_core(text, now)

    day, month, year, dspan, mspan = found
    cleaned = _blank(text, dspan)
    if mspan:
        cleaned = _blank(cleaned, mspan)
    r = _parse_core(cleaned, now)
    r.lunar = (day, month)
    if r.repeat == "yearly" or (year is None and r.repeat is None):
        r.repeat = "lunar_yearly"  # giỗ, sinh nhật âm: không ghi năm nghĩa là năm nào cũng có
    r.warnings = [w for w in r.warnings if w != "ngày không hợp lệ"]

    used29 = False
    if year:
        s = lunar_to_solar(day, month, year)
    else:
        s, used29 = next_solar(day, month, now.date())
    if s is None:
        r.start, r.all_day = None, False
        r.warnings.append("ngày âm lịch này không tồn tại, bạn kiểm tra lại")
        return r
    has_time = r.start is not None and not r.all_day
    t = r.start.time() if has_time else time(0, 0)
    r.start = datetime.combine(s, t)
    r.all_day = not has_time
    if used29:
        r.warnings.append("tháng âm này không có ngày 30, dùng ngày 29")
    return r
