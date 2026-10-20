"""Lần 14: "ram" gõ thiếu dấu là rằm (B24, B26), giờ nói ngược thói quen của buổi (B19), "12h tối" là nửa đêm.
Giờ giả lập: Thứ Tư 21/10/2026 10:00."""
import os
import sys
import unittest
from datetime import datetime as D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi

NOW = D(2026, 10, 21, 10, 0)
RAM = "đã hiểu \"ram\" là rằm"


def p(s):
    return parse_vi(s, NOW)


class RamTest(unittest.TestCase):
    def test_no_marks_ram_thang(self):
        for s, title, month, start in [
            ("cung ram thang 7", "Cung", 7, D(2027, 8, 16)),
            ("le chua ram thang 7 am", "Le chua", 7, D(2027, 8, 16)),
            ("cung ram thang gieng", "Cung", 1, D(2027, 2, 20)),
        ]:
            r = p(s)
            self.assertEqual((r.title, r.lunar, r.repeat, r.start, r.all_day),
                             (title, (15, month), "lunar_yearly", start, True), s)
            self.assertFalse(r.warnings, s)   # cả câu không dấu thì "ram" chắc là rằm, không cần nhắc

    def test_no_marks_keeps_period_rules(self):
        r = p("cung ram thang gieng luc 7h toi")
        self.assertEqual((r.start, r.all_day), (D(2027, 2, 20, 19, 0), False))

    def test_accented_ram_typo_warns(self):
        r = p("cúng ram hàng tháng")
        self.assertEqual((r.repeat, r.lunar, r.start), ("lunar_monthly", (15, None), D(2026, 10, 24)))
        self.assertTrue(any(RAM in w for w in r.warnings))
        r = p("đi chùa ram tháng chạp")
        self.assertEqual((r.title, r.lunar, r.repeat), ("Đi chùa", (15, 12), "lunar_yearly"))
        self.assertTrue(any(RAM in w for w in r.warnings))

    def test_ram_as_memory_untouched(self):
        r = p("nâng cấp ram máy tính thứ 7")
        self.assertEqual((r.title, r.lunar), ("Nâng cấp ram máy tính", None))
        r = p("mua ram tháng sau")
        self.assertIsNone(r.lunar)
        self.assertIn("ram", r.title)
        self.assertFalse(any(RAM in w for w in r.warnings))

    def test_real_ram_no_warning(self):
        r = p("cúng rằm mỗi tháng")
        self.assertEqual(r.repeat, "lunar_monthly")
        self.assertFalse(any(RAM in w for w in r.warnings))


class OddPeriodTest(unittest.TestCase):
    def test_odd_hours_warn(self):
        for s, start in [
            ("họp 3 giờ tối mai", D(2026, 10, 22, 15, 0)),
            ("đón con 15h sáng mai", D(2026, 10, 22, 15, 0)),
            ("học 9h chiều", D(2026, 10, 21, 21, 0)),
            ("ăn 8h trưa mai", D(2026, 10, 22, 8, 0)),
        ]:
            r = p(s)
            self.assertEqual(r.start, start, s)
            self.assertTrue(any("ít khi đi với buổi" in w for w in r.warnings), (s, r.warnings))

    def test_usual_hours_quiet(self):
        for s in ["họp 5 giờ tối", "xem phim 10 giờ tối", "đón con 7h sáng", "họp 2h chiều", "ăn 12h trưa",
                  "ngủ 11h đêm", "đi chợ 8h chiều", "họp từ 9h đến 11h sáng", "về 3 giờ kém 15 chiều"]:
            r = p(s)
            self.assertFalse(any("ít khi đi với buổi" in w for w in r.warnings), (s, r.warnings))

    def test_12h_toi_is_midnight(self):
        r = p("đi ngủ 12h tối nay")
        self.assertEqual(r.start, D(2026, 10, 22, 0, 0))
        r = p("12 giờ tối mai gọi điện")
        self.assertEqual(r.start, D(2026, 10, 23, 0, 0))


if __name__ == "__main__":
    unittest.main()
