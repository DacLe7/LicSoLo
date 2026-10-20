"""Lần 15: "tháng giêng/chạp" gõ không dấu (B30), chỉ đổi tên tháng khi có ngày đứng trước,
năm âm lịch sau chữ "âm lịch", ngày 30 tháng thiếu khi đã ghi năm. Giờ giả lập: Thứ Tư 21/10/2026 10:00."""
import os
import sys
import unittest
from datetime import datetime as D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi

NOW = D(2026, 10, 21, 10, 0)


def p(s):
    return parse_vi(s, NOW)


class MonthNameTest(unittest.TestCase):
    def test_no_marks_month_names(self):
        for s, title, lunar, start in [
            ("di chua mung 1 thang gieng", "Di chua", (1, 1), D(2027, 2, 6)),
            ("gio ong noi mung 8 thang chap", "Gio ong noi", (8, 12), D(2027, 1, 15)),
            ("cung ong tao 23 thang chap", "Cung ong tao", (23, 12), D(2027, 1, 30)),
            ("mung 1 thang gieng am", "", (1, 1), D(2027, 2, 6)),
            ("di chua ram thang gieng", "Di chua", (15, 1), D(2027, 2, 20)),
        ]:
            r = p(s)
            self.assertEqual((r.title, r.lunar, r.repeat, r.start, r.all_day),
                             (title, lunar, "lunar_yearly", start, True), s)
            self.assertFalse(r.warnings, s)

    def test_marked_month_names_still_work(self):
        r = p("đi chùa mùng 1 tháng giêng")
        self.assertEqual((r.title, r.lunar, r.start), ("Đi chùa", (1, 1), D(2027, 2, 6)))
        r = p("cúng ông táo 23 tháng chạp 7h tối")
        self.assertEqual((r.title, r.lunar, r.start, r.all_day), ("Cúng ông táo", (23, 12), D(2027, 1, 30, 19, 0), False))

    def test_month_name_without_day_stays_in_title(self):
        # trước đây thành "Họp tổng kết tháng 12 âm lịch" và bị coi là chưa hiểu
        for s, title in [("họp tổng kết tháng chạp", "Họp tổng kết tháng chạp"),
                         ("mua dao thang gieng", "Mua dao thang gieng")]:
            r = p(s)
            self.assertEqual((r.title, r.lunar, r.start), (title, None, None), s)
            self.assertFalse(r.unsure, s)

    def test_month_name_needs_marks_in_marked_sentence(self):
        # câu có dấu mà gõ "thang chap" thì không đoán (có thể là chữ khác)
        r = p("họp 5 thang chap")
        self.assertIsNone(r.lunar)

    def test_lunar_year_after_am_lich(self):
        r = p("giỗ ông 8/12 âm lịch 2026")
        self.assertEqual((r.title, r.lunar, r.repeat, r.start), ("Giỗ ông", (8, 12), None, D(2027, 1, 15)))
        r = p("giỗ ông 8/12 âm lịch năm 2025")
        self.assertEqual((r.title, r.start), ("Giỗ ông", D(2026, 1, 26)))
        r = p("gio ong 8/12 am lich 2026 luc 9h")
        self.assertEqual((r.title, r.start, r.all_day), ("Gio ong", D(2027, 1, 15, 9, 0), False))

    def test_day_30_of_short_month_with_year(self):
        # tháng chạp năm âm 2026 chỉ có 29 ngày: lấy ngày 29, có cảnh báo, không báo "không tồn tại"
        for s in ("tết 30 tháng chạp 2026", "tet 30 thang chap 2026"):
            r = p(s)
            self.assertEqual((r.title.lower(), r.start, r.repeat), ("tết" if "ế" in s else "tet", D(2027, 2, 5), None), s)
            self.assertIn("tháng âm này không có ngày 30, dùng ngày 29", r.warnings, s)


if __name__ == "__main__":
    unittest.main()
