"""Xuất lịch iCalendar (RFC 5545) để iOS/Android/Google Calendar nhập hoặc đăng ký.

Mỗi lần xảy ra là một VEVENT riêng (không dùng RRULE) vì lặp theo âm lịch không có chuẩn.
Giờ xuất dạng UTC (Z) để không cần VTIMEZONE; việc cả ngày dùng VALUE=DATE.
Nhắc dùng TRIGGER tuyệt đối (giờ UTC) nên giỗ có đủ mốc 7 ngày, 1 ngày và đúng giờ.
"""
from datetime import datetime, timedelta, timezone

PRODID = "-//Lac Viet//LicSoLo//VI"


def esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))


def fold(line: str) -> str:
    """Gập dòng tối đa 75 byte UTF-8, không cắt giữa một ký tự."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur, size, limit = [], "", 0, 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > limit:
            parts.append(cur)
            cur, size, limit = "", 0, 74   # dòng tiếp bắt đầu bằng một khoảng trắng
        cur += ch
        size += n
    parts.append(cur)
    return "\r\n ".join(parts)


def _utc(dt: datetime, tz) -> str:
    return dt.replace(tzinfo=tz).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _vevent(e: dict, o: datetime, tz, stamp: str, calname: str, uid: str, rrule=None, remind=None) -> list:
    """Một VEVENT. rrule: lặp theo chuẩn (khi đó remind = các mốc nhắc tính bằng phút trước giờ);
    không có rrule thì nhắc theo e["alarms"] (giờ tuyệt đối)."""
    L = ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp, "SUMMARY:" + esc(e["title"])]
    if e["all_day"]:
        d = o.date()
        L += ["DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
              "DTEND;VALUE=DATE:" + (d + timedelta(days=1)).strftime("%Y%m%d"), "TRANSP:TRANSPARENT"]
    else:
        L.append("DTSTART:" + _utc(o, tz))
        if e.get("duration_min"):
            L.append("DTEND:" + _utc(o + timedelta(minutes=e["duration_min"]), tz))
        L.append("TRANSP:OPAQUE")
    if rrule:
        L.append("RRULE:" + rrule)
    desc = []
    if (e.get("notes") or "").strip():
        desc.append(e["notes"].strip())
    if e.get("repeat") == "lunar_yearly" and e.get("lunar_day") and e.get("lunar_month"):
        desc.append("Âm lịch: %d/%d hằng năm" % (e["lunar_day"], e["lunar_month"]))
    elif e.get("repeat") == "lunar_monthly" and e.get("lunar_day"):
        desc.append("Âm lịch: ngày %d hằng tháng" % e["lunar_day"])
    elif e.get("repeat") == "yearly":
        desc.append("Lặp hằng năm")
    if desc:
        L.append("DESCRIPTION:" + esc("\n".join(desc)))
    if e.get("updated"):
        L.append("LAST-MODIFIED:" + _utc(datetime.fromisoformat(e["updated"]), tz))
    L.append("CATEGORIES:" + esc(calname))
    triggers = ["TRIGGER;VALUE=DATE-TIME:" + _utc(fa, tz) for fa in e.get("alarms", [])] if rrule is None else \
        ["TRIGGER:" + _rel(m) for m in (remind or [])]   # việc cả ngày: remind đã tính giờ nhắc (mặc định 8h sáng)
    for t in triggers:
        L += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(e["title"]), t, "END:VALARM"]
    L.append("END:VEVENT")
    return L


def _rel(before_min: int) -> str:
    """Mốc nhắc tương đối so với giờ bắt đầu: dương = trước giờ ("-PT10M"), âm = sau giờ ("PT480M")."""
    return ("-PT%dM" % before_min) if before_min > 0 else ("PT%dM" % -before_min)


def _wrap(body: list, calname: str, tz, feed: bool) -> str:
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:" + PRODID, "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:" + esc(calname), "X-WR-TIMEZONE:" + str(tz)]
    if feed:
        L += ["REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    L += body + ["END:VCALENDAR"]
    return "\r\n".join(fold(x) for x in L) + "\r\n"


def render(items: list, now: datetime, tz, calname: str = "Lạc Việt") -> str:
    """items: kết quả Service.calendar_items(); now: giờ địa phương hiện tại (naive); tz: múi giờ của app."""
    stamp, body = _utc(now, tz), []
    for e in items:
        o = datetime.fromisoformat(e["occurrence"])
        body += _vevent(e, o, tz, stamp, calname, "lv-%d-%s@lichviet" % (e["id"], o.strftime("%Y%m%d%H%M")))
    return _wrap(body, calname, tz, feed=True)


def render_event(ev: dict, now: datetime, tz, calname: str = "Lạc Việt") -> str:
    """Một việc (kết quả Service.event_calendar) thành tệp .ics để tải về: lặp chuẩn dùng RRULE, còn lại liệt kê từng lần."""
    stamp = _utc(now, tz)
    if ev.get("rrule"):
        body = _vevent(ev, datetime.fromisoformat(ev["start"]), tz, stamp, calname, "lv-%d@lichviet" % ev["id"],
                       rrule=ev["rrule"], remind=ev["remind"])
    else:
        body = []
        for e in ev["items"]:
            o = datetime.fromisoformat(e["occurrence"])
            body += _vevent(e, o, tz, stamp, calname, "lv-%d-%s@lichviet" % (e["id"], o.strftime("%Y%m%d%H%M")))
    return _wrap(body, calname, tz, feed=False)
