"""Đổi âm lịch <-> dương lịch theo múi giờ Việt Nam (UTC+7).

Dùng thuật toán thiên văn của Hồ Ngọc Đức. Không cần thư viện ngoài.
Không dùng thư viện lịch Trung Quốc (UTC+8) vì có năm lệch 1 ngày so với lịch Việt.
"""
from datetime import date
from math import pi, sin
from typing import Optional

TZ = 7.0
_SYN = 29.530588853
_EPOCH = 2415021.076998695


def _jd_from_date(dd: int, mm: int, yy: int) -> int:
    a = (14 - mm) // 12
    y = yy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if jd < 2299161:
        jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083
    return jd


def _jd_to_date(jd: int):
    if jd > 2299160:
        a = jd + 32044
        b = (4 * a + 3) // 146097
        c = a - (b * 146097) // 4
    else:
        b = 0
        c = jd + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = b * 100 + d - 4800 + m // 10
    return day, month, year


def _new_moon(k: int) -> float:
    T = k / 1236.85
    T2, T3 = T * T, T * T * T
    dr = pi / 180
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    jd1 += 0.00033 * sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    c1 = (0.1734 - 0.000393 * T) * sin(M * dr) + 0.0021 * sin(2 * dr * M)
    c1 -= 0.4068 * sin(Mpr * dr) - 0.0161 * sin(dr * 2 * Mpr)
    c1 -= 0.0004 * sin(dr * 3 * Mpr)
    c1 += 0.0104 * sin(dr * 2 * F) - 0.0051 * sin(dr * (M + Mpr))
    c1 -= 0.0074 * sin(dr * (M - Mpr)) - 0.0004 * sin(dr * (2 * F + M))
    c1 -= 0.0004 * sin(dr * (2 * F - M)) + 0.0006 * sin(dr * (2 * F + Mpr))
    c1 += 0.0010 * sin(dr * (2 * F - Mpr)) + 0.0005 * sin(dr * (2 * Mpr + M))
    if T < -11:
        dt = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        dt = -0.000278 + 0.000265 * T + 0.000262 * T2
    return jd1 + c1 - dt


def _sun_longitude_idx(jdn: float) -> int:
    T = (jdn - 2451545.0 - 0.5 - TZ / 24.0) / 36525
    T2 = T * T
    dr = pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    dl = (1.914600 - 0.004817 * T - 0.000014 * T2) * sin(dr * M)
    dl += (0.019993 - 0.000101 * T) * sin(dr * 2 * M) + 0.000290 * sin(dr * 3 * M)
    L = (L0 + dl) * dr
    L -= pi * 2 * int(L / (pi * 2))
    return int(L / pi * 6)


def _new_moon_day(k: int) -> int:
    return int(_new_moon(k) + 0.5 + TZ / 24.0)


def _month11(yy: int) -> int:
    off = _jd_from_date(31, 12, yy) - 2415021
    k = int(off / _SYN)
    nm = _new_moon_day(k)
    if _sun_longitude_idx(nm) >= 9:
        nm = _new_moon_day(k - 1)
    return nm


def _leap_offset(a11: int) -> int:
    k = int((a11 - _EPOCH) / _SYN + 0.5)
    i = 1
    arc = _sun_longitude_idx(_new_moon_day(k + i))
    while True:
        last = arc
        i += 1
        arc = _sun_longitude_idx(_new_moon_day(k + i))
        if not (arc != last and i < 14):
            break
    return i - 1


def solar_to_lunar(d: date):
    """Trả về (ngày, tháng, năm, nhuận) âm lịch; nhuận = 1 nếu là tháng nhuận."""
    dd, mm, yy = d.day, d.month, d.year
    jdn = _jd_from_date(dd, mm, yy)
    k = int((jdn - _EPOCH) / _SYN)
    start = _new_moon_day(k + 1)
    if start > jdn:
        start = _new_moon_day(k)
    a11 = _month11(yy)
    b11 = a11
    if a11 >= start:
        ly = yy
        a11 = _month11(yy - 1)
    else:
        ly = yy + 1
        b11 = _month11(yy + 1)
    lday = jdn - start + 1
    diff = int((start - a11) / 29)
    leap = 0
    lmonth = diff + 11
    if b11 - a11 > 365:
        loff = _leap_offset(a11)
        if diff >= loff:
            lmonth = diff + 10
            if diff == loff:
                leap = 1
    if lmonth > 12:
        lmonth -= 12
    if lmonth >= 11 and diff < 4:
        ly -= 1
    return lday, lmonth, ly, leap


def lunar_to_solar(lday: int, lmonth: int, lyear: int, leap: int = 0) -> Optional[date]:
    """Đổi âm lịch sang dương lịch; trả về None nếu ngày âm đó không tồn tại."""
    if lmonth < 11:
        a11 = _month11(lyear - 1)
        b11 = _month11(lyear)
    else:
        a11 = _month11(lyear)
        b11 = _month11(lyear + 1)
    k = int(0.5 + (a11 - _EPOCH) / _SYN)
    off = lmonth - 11
    if off < 0:
        off += 12
    if b11 - a11 > 365:
        loff = _leap_offset(a11)
        lm = loff - 2
        if lm < 0:
            lm += 12
        if leap != 0 and lmonth != lm:
            return None
        if leap != 0 or off >= loff:
            off += 1
    start = _new_moon_day(k + off)
    dd, mm, yy = _jd_to_date(start + lday - 1)
    try:
        out = date(yy, mm, dd)
    except ValueError:
        return None
    # kiểm tra ngược để loại ngày không có (ví dụ 30 của tháng thiếu)
    back = solar_to_lunar(out)
    if (back[0], back[1], back[3]) != (lday, lmonth, leap):
        return None
    return out


def next_solar(lday: int, lmonth: int, today: date):
    """Ngày dương gần nhất (từ hôm nay trở đi) ứng với ngày âm lịch lday/lmonth.

    Trả về (ngày dương, có_phải_dùng_29_thay_30). Tháng thiếu không có ngày 30
    thì lùi về ngày 29, theo cách người Việt vẫn cúng giỗ.
    """
    for use_day in ([lday, 29] if lday == 30 else [lday]):
        best = None
        for ly in range(today.year - 1, today.year + 3):
            s = lunar_to_solar(use_day, lmonth, ly)
            if s and s >= today and (best is None or s < best):
                best = s
        if best:
            return best, use_day != lday
    return None, False
