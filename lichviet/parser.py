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
    repeat: Optional[str] = None          # daily | weekly | monthly | lunar_yearly
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
    return n * {"phut": 1, "gio": 60, "tieng": 60, "ngay": 1440}[unit]


def _valid_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _parse_core(text: str, now: datetime) -> ParseResult:
    f = fold(text)
    spans = []  # (start, end) đã dùng, để cắt khỏi tiêu đề
    r = ParseResult()

    def take(pattern, flags=0):
        nonlocal f
        m = re.search(pattern, f, flags)
        if m:
            spans.append((m.start(), m.end()))
            f = _mask(f, m)
        return m

    take(r"\b(?:nhac|giup)\s+toi\b")  # "tôi" ở đây là đại từ, không phải buổi tối
    # 1) nhắc trước
    m = take(r"\bnhac\s+(?:toi\s+)?truoc\s+(\d+)\s*(phut|gio|tieng|ngay)\b")
    if m:
        r.remind_before_min = _unit_min(int(m.group(1)), m.group(2))

    # 2) thời lượng
    m = take(r"\b(?:keo\s+dai|trong|mat)\s+(\d+)\s*(phut|gio|tieng)\b")
    if m:
        r.duration_min = _unit_min(int(m.group(1)), m.group(2))

    # 3) lặp lại
    day = None
    m = take(r"\b(?:moi|hang)\s+ngay\b")
    if m:
        r.repeat = "daily"
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

    # 4) sau N phút/giờ/ngày  (tương đối so với bây giờ)
    rel = None
    rel_days = False
    m = take(r"\bsau\s+(\d+)\s*(phut|gio|tieng|ngay)\b")
    if m:
        rel_days = m.group(2) == "ngay"
        rel = now + timedelta(minutes=_unit_min(int(m.group(1)), m.group(2)))
        if m.group(2) == "ngay":
            rel = rel.replace(second=0, microsecond=0)

    # "cả ngày": chỉ là dấu hiệu việc không có giờ, không thuộc tên việc
    take(r"\bca\s+ngay\b")

    # 5) ngày
    d: Optional[date] = None
    m = take(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?\b") or \
        take(r"\b(?:(?:ngay|mung|mong)\s+)?(\d{1,2})\s+thang\s+(\d{1,2})(?:\s+nam\s+(\d{4}))?\b")
    if m:
        dd, mm = int(m.group(1)), int(m.group(2))
        yy = int(m.group(3)) if m.group(3) else now.year
        d = _valid_date(yy, mm, dd)
        if d is None:
            r.warnings.append("ngày không hợp lệ")
        elif not m.group(3) and d < now.date():
            d = _valid_date(yy + 1, mm, dd)
    if d is None and not r.warnings:
        m = re.search(r"\b(?:sang|trua|chieu|toi|dem|khuya)\s+(nay)\b", f)
        if take(r"\bhom\s+nay\b"):
            d = now.date()
        elif m:
            spans.append((m.start(1), m.end(1)))
            f = f[:m.start(1)] + " " * 3 + f[m.end(1):]
            d = now.date()
        elif take(r"\bngay\s+mai\b|\bmai\b"):
            d = now.date() + timedelta(days=1)
        elif take(r"\bngay\s+kia\b"):
            d = now.date() + timedelta(days=2)
    if d is None and not r.warnings:
        # cụm mơ hồ: "cuối tuần (này/sau)", "đầu tuần sau", "cuối tháng", "đầu tháng sau"
        unit = "tuan"
        m = take(r"\b(cuoi|dau)\s+tuan(?:\s+(nay|sau|toi)\b)?")
        if not m:
            unit = "thang"  # "đầu tháng 11" là ngày cụ thể, để luật khác xử lý
            m = take(r"\b(cuoi|dau)\s+thang(?:\s+(nay|sau|toi)\b|(?!\s*\d))")
        if m:
            edge, q = m.group(1), m.group(2)
            today = now.date()
            if unit == "tuan":
                monday = today - timedelta(days=today.weekday()) + timedelta(days=7 if q in ("sau", "toi") else 0)
                d = monday + timedelta(days=5 if edge == "cuoi" else 0)
                if d < today:  # cuối tuần đang diễn ra thì lấy hôm nay, đầu tuần đã qua thì lấy tuần sau
                    d = today if edge == "cuoi" else d + timedelta(days=7)
                if edge == "cuoi":
                    r.warnings.append("\"cuối tuần\" tạm đặt thứ Bảy, bạn chỉnh nếu khác")
            else:
                first = today.replace(day=1)
                nxt = (first + timedelta(days=32)).replace(day=1)
                base = nxt if q in ("sau", "toi") else first
                if edge == "dau":
                    d = base if q else nxt
                else:
                    d = (base + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    if d is None and not r.warnings:
        m = take(r"\b(?:thu\s+(hai|bay|ba|tu|nam|sau|[2-7])|(chu\s+nhat))\s*(tuan\s+(?:sau|toi|nay))?")
        if m or day is not None:
            wd = day if m is None else WEEKDAYS["cn" if m.group(2) else m.group(1)]
            q = (m.group(3) or "") if m else ""
            monday = now.date() - timedelta(days=now.weekday())
            if "sau" in q or "toi" in q:
                d = monday + timedelta(days=7 + wd)
            elif "nay" in q:
                d = monday + timedelta(days=wd)
            else:
                d = now.date() + timedelta(days=(wd - now.weekday() - 1) % 7 + 1)
        else:
            if take(r"\btuan\s+(?:sau|toi)\b"):
                d = now.date() + timedelta(days=7)

    # 6) giờ
    hh = mi = None
    tspan = None
    kem = 0
    # "3 giờ kém 15" = 2:45; "ba giờ kém mười lăm"
    m = take(r"\b(?:(\d{1,2})\s*(?:h(?![a-z])|gio)|(mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?:\s+(?:mot|hai))?)\s+gio)\s+kem\s+(\d{1,2}|hai\s+muoi\s+lam|hai\s+muoi|muoi\s+lam|muoi|nam)\b(?:\s*phut)?")
    if m:
        hh = int(m.group(1)) if m.group(1) else NUMW[m.group(2).replace("  ", " ")]
        w = re.sub(r"\s+", " ", m.group(3))
        kem = int(w) if w.isdigit() else {"nam": 5, "muoi": 10, "muoi lam": 15, "hai muoi": 20, "hai muoi lam": 25}[w]
        mi = 0
        tspan = (m.start(), m.end())
    else:
        m = take(r"\b(?:(\d{1,2})\s*(?:h(?![a-z])|gio|:)|(mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?:\s+(?:mot|hai))?)\s+gio)\s*(?:(\d{2})\b|(?<=h)(\d)\b|(ruoi)\b)?(?:\s*phut)?")
        if m:
            hh = int(m.group(1)) if m.group(1) else NUMW[m.group(2).replace("  ", " ")]
            mi = 30 if m.group(5) else int(m.group(3) or m.group(4) or 0)
            tspan = (m.start(), m.end())
    period = None
    midnight12 = False
    ms = list(re.finditer(r"\b(sang|trua|chieu|toi|dem|khuya)\b", f))
    if tspan:  # chỉ lấy từ chỉ buổi sát cạnh giờ ("3h chiều", "tối 7h")
        ms = [x for x in ms if 0 <= x.start() - tspan[1] <= 3 or 0 <= tspan[0] - x.end() <= 3]
    else:
        ms = ms[-1:]
    for m in ms[:1]:
        period = "dem" if m.group(1) == "khuya" else m.group(1)
        spans.append((m.start(), m.end()))
        f = _mask(f, m)
    if hh is not None:
        if hh > 24 or mi > 59:
            r.warnings.append("giờ không hợp lệ")
            hh = None
        elif period in ("chieu", "toi") and hh < 12:
            hh += 12
        elif period == "trua" and 1 <= hh < 6:
            hh += 12
        elif period == "dem" and hh == 12:
            hh = 0
            midnight12 = True
        if hh == 24:
            hh = 0
        if kem and hh is not None:   # "3 giờ kém 15": trừ sau khi đã áp buổi (chiều → 15 → 14:45)
            hh, mi = hh - 1, 60 - kem
            if hh < 0:
                hh = 23

    # 7) ghép ngày giờ
    if rel is not None:
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
        h = {"sang": 8, "trua": 12, "chieu": 15, "toi": 19, "dem": 22}[period]
        r.start = datetime.combine(d, time(h, 0))
        r.warnings.append("chỉ nói buổi, tạm đặt %02d:00" % h)
    elif d is not None:
        r.start = datetime.combine(d, time(0, 0))
        r.all_day = True
    elif period is not None:
        h = {"sang": 8, "trua": 12, "chieu": 15, "toi": 19, "dem": 22}[period]
        cand = now.replace(hour=h, minute=0, second=0, microsecond=0)
        r.start = cand if cand > now else cand + timedelta(days=1)
        r.warnings.append("chỉ nói buổi, tạm đặt %02d:00" % h)

    # 8) tiêu đề: văn bản gốc trừ phần đã dùng (kể cả từ nối đứng ngay trước), bỏ từ đệm hai đầu
    f0 = fold(text)
    keep = [True] * len(text)
    for a, b in spans:
        mm = re.search(r"(?:\b(?:vao\s+luc|vao\s+ngay|vao|luc|ngay|khoang|den)\s*)+$", f0[:a])
        if mm:
            a = mm.start()
        for i in range(a, b):
            keep[i] = False
    rest = "".join(c if k else " " for c, k in zip(text, keep))
    rest = re.sub(r"\s+", " ", rest).strip(" ,.;:-")
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
    r.title = rest.strip(" ,.;:-")
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
    for m in re.finditer(r"\brằm\b", low):
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


def parse_vi(text: str, now: datetime) -> ParseResult:
    text = unicodedata.normalize("NFC", text)
    # "ngày mốt", "bữa mốt" (Nam Bộ) = ngày kia; "ngày một" (mùng 1) giữ nguyên vì có dấu khác
    text = re.sub(r"(?i)\b(?:ngày|bữa)\s+mốt\b", "ngày kia", text)
    text = re.sub(r"(?i)\brằm\s+tháng\s+(\d{1,2})\b(?!\s*(?:âm|dương))", r"15 tháng \1 âm lịch", text)
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
    if year is None and r.repeat is None:
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
