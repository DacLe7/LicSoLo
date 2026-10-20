"""Bảng câu thử bộ hiểu câu, chia nhóm theo hiện tượng (lần 7):
số viết bằng chữ trong cụm tương đối, tháng/năm tương đối, ngày đã qua mơ hồ, khoảng giờ, sáng sớm, nửa đêm.
Giờ giả lập: Thứ Tư 21/10/2026 10:00."""
import os
import sys
import unittest
from datetime import datetime as D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi, _shift_months

NOW = D(2026, 10, 21, 10, 0)

# (câu, tên việc, bắt đầu, cả ngày)
CASES = {
    "số bằng chữ trong cụm tương đối": [
        ("hai ngày nữa nộp bài", "Nộp bài", D(2026, 10, 23), True),
        ("khám răng ba hôm trước", "Khám răng", D(2026, 10, 18), True),
        ("tắt bếp mười lăm phút nữa", "Tắt bếp", D(2026, 10, 21, 10, 15), False),
        ("gọi mẹ sau hai tiếng", "Gọi mẹ", D(2026, 10, 21, 12, 0), False),
        ("uống thuốc hai mươi phút nữa", "Uống thuốc", D(2026, 10, 21, 10, 20), False),
        ("họp nửa tiếng nữa", "Họp", D(2026, 10, 21, 10, 30), False),
        ("xem phim một tiếng rưỡi nữa", "Xem phim", D(2026, 10, 21, 11, 30), False),
        ("nộp hồ sơ một tuần nữa", "Nộp hồ sơ", D(2026, 10, 28), True),
        ("gặp bác sĩ hai tuần tới", "Gặp bác sĩ", D(2026, 11, 4), True),
        ("đi Đà Lạt sau ba ngày", "Đi Đà Lạt", D(2026, 10, 24), True),
    ],
    "tháng, năm tương đối": [
        ("nộp thuế 3 tháng nữa", "Nộp thuế", D(2027, 1, 21), True),
        ("gia hạn hộ chiếu sau sáu tháng", "Gia hạn hộ chiếu", D(2027, 4, 21), True),
        ("tái khám hai tháng nữa 9h sáng", "Tái khám", D(2026, 12, 21, 9, 0), False),
        ("đổi bằng lái một năm nữa", "Đổi bằng lái", D(2027, 10, 21), True),
        ("họp 20/11 năm sau", "Họp", D(2027, 11, 20), True),
        ("họp ngày 5 tháng tới", "Họp", D(2026, 11, 5), True),
        ("mùng hai tháng tới đi chùa", "Đi chùa", D(2026, 11, 2), True),
        ("họp tuần tới 8h tối", "Họp", D(2026, 10, 28, 20, 0), False),
    ],
    "ngày đã qua": [
        ("họp đầu tuần trước", "Họp", D(2026, 10, 12), True),
        ("đi chơi cuối tuần trước", "Đi chơi", D(2026, 10, 17), True),
        ("họp đầu tháng trước", "Họp", D(2026, 9, 1), True),
        ("chốt sổ cuối tháng trước", "Chốt sổ", D(2026, 9, 30), True),
        ("mua xe 2 tháng trước", "Mua xe", D(2026, 8, 21), True),
        ("thứ hai tuần trước họp", "Họp", D(2026, 10, 12), True),
    ],
    "khoảng giờ": [
        ("họp từ 2h đến 4h chiều", "Họp", D(2026, 10, 21, 14, 0), False),
        ("họp từ 11h đến 1h chiều", "Họp", D(2026, 10, 21, 11, 0), False),
        ("học 9h-11h30 mai", "Học", D(2026, 10, 22, 9, 0), False),
        ("trực 22h-2h", "Trực", D(2026, 10, 21, 22, 0), False),
        ("dạy thêm từ 7 tới 9h tối thứ sáu", "Dạy thêm", D(2026, 10, 23, 19, 0), False),
    ],
    "buổi đặc biệt": [
        ("sáng sớm mai chạy bộ", "Chạy bộ", D(2026, 10, 22, 6, 0), False),
        ("chạy bộ sáng sớm", "Chạy bộ", D(2026, 10, 22, 6, 0), False),
        ("tập thể dục 5h sáng sớm", "Tập thể dục", D(2026, 10, 22, 5, 0), False),
        ("nửa đêm nay xem bóng", "Xem bóng", D(2026, 10, 22, 0, 0), False),
        ("xem bóng nửa đêm mai", "Xem bóng", D(2026, 10, 23, 0, 0), False),
        ("gọi điện tối chủ nhật 8h", "Gọi điện", D(2026, 10, 25, 20, 0), False),
        ("khám bệnh sáng thứ hai 7h", "Khám bệnh", D(2026, 10, 26, 7, 0), False),
    ],
}

DURATIONS = {
    "họp từ 2h đến 4h chiều": 120,
    "họp từ 11h đến 1h chiều": 120,
    "học 9h-11h30 mai": 150,
    "trực 22h-2h": 240,
    "dạy thêm từ 7 tới 9h tối thứ sáu": 120,
}


class TestPhraseTable(unittest.TestCase):
    def test_cases(self):
        for group, rows in CASES.items():
            for text, title, start, all_day in rows:
                with self.subTest(group=group, text=text):
                    r = parse_vi(text, NOW)
                    self.assertEqual((r.title, r.start, r.all_day), (title, start, all_day), r.warnings)

    def test_durations(self):
        for text, dur in DURATIONS.items():
            with self.subTest(text=text):
                self.assertEqual(parse_vi(text, NOW).duration_min, dur)

    def test_explicit_duration_wins_over_range(self):
        self.assertEqual(parse_vi("họp từ 2h đến 4h chiều kéo dài 30 phút", NOW).duration_min, 30)


class TestKeptAsIs(unittest.TestCase):
    """Những chỗ không được đổi: số đếm không phải khoảng thời gian, "tới" không phải "tối"."""

    def test_weekday_words_unchanged(self):
        r = parse_vi("ăn cưới thứ năm tuần trước", NOW)
        self.assertEqual((r.title, r.start), ("Ăn cưới", D(2026, 10, 15)))
        r = parse_vi("họp thứ hai tuần tới", NOW)
        self.assertEqual(r.start, D(2026, 10, 26))

    def test_toi_after_unit_is_not_evening(self):
        r = parse_vi("họp tuần tới", NOW)
        self.assertEqual((r.start, r.all_day), (D(2026, 10, 28), True))
        self.assertFalse(any("19:00" in w for w in parse_vi("họp tháng tới", NOW).warnings))

    def test_clock_after_sau_is_not_relative(self):
        r = parse_vi("đón con sau 2 giờ chiều", NOW)
        self.assertEqual(r.start, D(2026, 10, 21, 14, 0))

    def test_half_hour_clock_kept(self):
        self.assertEqual(parse_vi("ba giờ rưỡi chiều họp", NOW).start, D(2026, 10, 21, 15, 30))
        self.assertEqual(parse_vi("họp 3 giờ rưỡi chiều mai", NOW).start, D(2026, 10, 22, 15, 30))

    def test_accented_words_not_periods(self):
        """Câu gõ có dấu: "hộ chiếu", "chiếu phim" không phải buổi chiều."""
        r = parse_vi("đi chiếu phim 8h tối mai", NOW)
        self.assertEqual((r.title, r.start), ("Đi chiếu phim", D(2026, 10, 22, 20, 0)))
        r = parse_vi("làm hộ chiếu chiều mai", NOW)
        self.assertEqual((r.title, r.start), ("Làm hộ chiếu", D(2026, 10, 22, 15, 0)))
        self.assertEqual(parse_vi("hop 3h chieu mai", NOW).start, D(2026, 10, 22, 15, 0))   # không dấu vẫn hiểu

    def test_mot_is_not_one(self):
        self.assertEqual(parse_vi("họp ngày mốt", NOW).start, D(2026, 10, 23))

    def test_thu_tu_not_range(self):
        r = parse_vi("họp thứ tư 2h đến 4h chiều", NOW)
        self.assertEqual((r.start, r.duration_min), (D(2026, 10, 28, 14, 0), 120))


class TestVaguePast(unittest.TestCase):
    def test_thang_truoc_nam_ngoai_warn(self):
        for text, start, cum in (("trả tiền điện tháng trước", D(2026, 9, 21), "tháng trước"),
                                 ("du lịch năm ngoái", D(2025, 10, 21), "năm ngoái"),
                                 ("đi Huế năm rồi", D(2025, 10, 21), "năm rồi")):
            with self.subTest(text=text):
                r = parse_vi(text, NOW)
                self.assertEqual((r.start, r.all_day), (start, True))
                self.assertNotIn(cum, r.title.lower())
                self.assertTrue(any(cum in w and "không rõ" in w for w in r.warnings), r.warnings)

    def test_date_last_year(self):
        r = parse_vi("đám cưới bạn 5/3 năm ngoái", NOW)
        self.assertEqual((r.title, r.start, r.repeat), ("Đám cưới bạn", D(2025, 3, 5), None))

    def test_birthday_next_year_not_auto_yearly(self):
        r = parse_vi("tiệc sinh nhật 20/11 năm sau", NOW)
        self.assertEqual((r.start, r.repeat), (D(2027, 11, 20), None))


class TestShiftMonths(unittest.TestCase):
    def test_clamp_end_of_month(self):
        self.assertEqual(_shift_months(D(2026, 3, 31, 9), -1), D(2026, 2, 28, 9))
        self.assertEqual(_shift_months(D(2028, 3, 31), -1), D(2028, 2, 29))
        self.assertEqual(_shift_months(D(2026, 12, 15), 1), D(2027, 1, 15))
        self.assertEqual(_shift_months(D(2026, 1, 15), -13), D(2024, 12, 15))


if __name__ == "__main__":
    unittest.main()
