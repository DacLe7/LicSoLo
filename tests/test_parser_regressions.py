"""Các câu test thực tế (giờ giả lập: Thứ Ba 20/10/2026 09:30). Mỗi dòng là một lỗi đã từng sai."""
import sys, os, unittest
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi

NOW = datetime(2026, 10, 20, 9, 30)


def at(text):
    r = parse_vi(text, NOW)
    return r.start, r.all_day, r.repeat, r.title, r.warnings


class TestRegressions(unittest.TestCase):
    def test_period_with_relative_day_and_hour(self):
        self.assertEqual(at("họp tối nay 8h")[0], datetime(2026, 10, 20, 20, 0))
        self.assertEqual(at("họp tối mai 8h")[0], datetime(2026, 10, 21, 20, 0))
        self.assertEqual(at("họp sáng nay 8h")[0], datetime(2026, 10, 20, 8, 0))
        self.assertEqual(at("họp chiều nay 3h")[0], datetime(2026, 10, 20, 15, 0))
        self.assertEqual(at("tối nay họp 8h")[0], datetime(2026, 10, 20, 20, 0))

    def test_toi_pronoun_is_not_evening(self):
        # không có buổi: 8h đã qua hôm nay nên lấy 8h sáng mai (không được hiểu thành 20h)
        self.assertEqual(at("gọi tôi 8h")[0], datetime(2026, 10, 21, 8, 0))
        self.assertEqual(at("gọi tôi 8h")[3], "Gọi tôi")

    def test_hom_qua(self):
        start, _, _, title, _ = at("họp hôm qua 8h")
        self.assertEqual((start, title), (datetime(2026, 10, 19, 8, 0), "Họp"))

    def test_monthly_day_of_month(self):
        start, all_day, rep, title, _ = at("đóng tiền điện ngày 25 hằng tháng")
        self.assertEqual((start.date().isoformat(), rep, title), ("2026-10-25", "monthly", "Đóng tiền điện"))
        self.assertTrue(all_day)
        self.assertEqual(at("đóng tiền ngày 31 hằng tháng")[0].date().isoformat(), "2026-10-31")
        # ngày 5 hằng tháng khi hôm nay là 20: đã qua trong tháng này -> tháng sau
        self.assertEqual(at("trả nợ ngày 5 hằng tháng")[0].date().isoformat(), "2026-11-05")

    def test_invalid_date_is_not_guessed(self):
        start, _, _, _, warnings = at("họp 31/4 lúc 9h")
        self.assertIsNone(start)
        self.assertIn("ngày không hợp lệ", warnings)

    def test_unchanged_good_cases(self):
        self.assertEqual(at("họp 3 giờ kém 15 chiều mai")[0], datetime(2026, 10, 21, 14, 45))
        self.assertEqual(at("họp 3h5 chiều thứ sáu")[0], datetime(2026, 10, 23, 15, 5))
        self.assertEqual(at("sau 3 ngày lúc 9h họp")[0], datetime(2026, 10, 23, 9, 0))
        self.assertEqual(at("đi khám ngày mốt 8h30 sáng")[0], datetime(2026, 10, 22, 8, 30))
        self.assertEqual(at("gọi mẹ 10 giờ 30 phút tối")[0], datetime(2026, 10, 20, 22, 30))
        self.assertEqual(at("sinh nhật bạn 5/11")[0].date().isoformat(), "2026-11-05")
        self.assertEqual(at("họp 9 giờ 30 phút sáng mai")[0], datetime(2026, 10, 21, 9, 30))
        self.assertEqual(at("giỗ ông nội 15/8 âm lịch")[0].date().isoformat(), "2027-09-15")


if __name__ == "__main__":
    unittest.main()
