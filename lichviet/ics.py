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


def render(items: list, now: datetime, tz, calname: str = "Lạc Việt") -> str:
    """items: kết quả Service.calendar_items(); now: giờ địa phương hiện tại (naive); tz: múi giờ của app."""
    stamp = _utc(now, tz)
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:" + PRODID, "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:" + esc(calname), "X-WR-TIMEZONE:" + str(tz),
         "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    for e in items:
        o = datetime.fromisoformat(e["occurrence"])
        uid = "lv-%d-%s@lichviet" % (e["id"], o.strftime("%Y%m%d%H%M"))
        L += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp,
              "SUMMARY:" + esc(e["title"])]
        if e["all_day"]:
            d = o.date()
            L += ["DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
                  "DTEND;VALUE=DATE:" + (d + timedelta(days=1)).strftime("%Y%m%d"), "TRANSP:TRANSPARENT"]
        else:
            L.append("DTSTART:" + _utc(o, tz))
            if e.get("duration_min"):
                L.append("DTEND:" + _utc(o + timedelta(minutes=e["duration_min"]), tz))
            L.append("TRANSP:OPAQUE")
        desc = []
        if (e.get("notes") or "").strip():
            desc.append(e["notes"].strip())
        if e.get("repeat") == "lunar_yearly" and e.get("lunar_day") and e.get("lunar_month"):
            desc.append("Âm lịch: %d/%d hằng năm" % (e["lunar_day"], e["lunar_month"]))
        elif e.get("repeat") == "lunar_monthly" and e.get("lunar_day"):
            desc.append("Âm lịch: ngày %d hằng tháng" % e["lunar_day"])
        if desc:
            L.append("DESCRIPTION:" + esc("\n".join(desc)))
        if e.get("updated"):
            L.append("LAST-MODIFIED:" + _utc(datetime.fromisoformat(e["updated"]), tz))
        L.append("CATEGORIES:" + esc(calname))
        for fa in e.get("alarms", []):
            L += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(e["title"]),
                  "TRIGGER;VALUE=DATE-TIME:" + _utc(fa, tz), "END:VALARM"]
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in L) + "\r\n"
