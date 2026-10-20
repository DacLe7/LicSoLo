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
    # lần 10 (B11): "ăn tối", "ca sáng"... là tên việc, buổi vẫn dùng để đoán giờ khi không nói buổi khác
    "bữa ăn, ca làm trong tên việc": [
        ("ăn tối hôm bữa", "Ăn tối", D(2026, 10, 18, 19, 0), False),
        ("ăn tối với sếp 7h mai", "Ăn tối với sếp", D(2026, 10, 22, 19, 0), False),
        ("ăn trưa 12h thứ 6", "Ăn trưa", D(2026, 10, 23, 12, 0), False),
        ("ăn trưa 1h", "Ăn trưa", D(2026, 10, 21, 13, 0), False),
        ("đi ăn tối mai", "Đi ăn tối", D(2026, 10, 22, 19, 0), False),
        ("ăn tối lúc 8h", "Ăn tối", D(2026, 10, 21, 20, 0), False),
        ("ăn sáng 7h mai", "Ăn sáng", D(2026, 10, 22, 7, 0), False),
        ("ca sáng 6h mai", "Ca sáng", D(2026, 10, 22, 6, 0), False),
        ("ca chiều 2h thứ hai", "Ca chiều", D(2026, 10, 26, 14, 0), False),
        ("ca đêm 10h thứ bảy", "Ca đêm", D(2026, 10, 24, 22, 0), False),
        ("cơm tối nhà ngoại 6h chủ nhật", "Cơm tối nhà ngoại", D(2026, 10, 25, 18, 0), False),
        ("bữa sáng với nhóm 7h30 thứ năm", "Bữa sáng với nhóm", D(2026, 10, 22, 7, 30), False),
        ("tiệc tối 7h thứ sáu", "Tiệc tối", D(2026, 10, 23, 19, 0), False),
        ("đi tiệc tối thứ bảy", "Đi tiệc tối", D(2026, 10, 24, 19, 0), False),
        ("ăn tối 7h sáng mai", "Ăn tối", D(2026, 10, 22, 7, 0), False),   # buổi nói rõ thắng buổi trong tên
        ("ăn tối tối mai", "Ăn tối", D(2026, 10, 22, 19, 0), False),
        ("an toi 7h mai", "An toi", D(2026, 10, 22, 19, 0), False),   # gõ không dấu
        ("cà chua tối mai", "Cà chua", D(2026, 10, 22, 19, 0), False),   # "cà" không phải "ca"
    ],
    "giờ đêm, khuya": [
        ("trực 10h đêm mai", "Trực", D(2026, 10, 22, 22, 0), False),
        ("đi ngủ 11h đêm nay", "Đi ngủ", D(2026, 10, 21, 23, 0), False),
        ("9h đêm nay xem phim", "Xem phim", D(2026, 10, 21, 21, 0), False),
        ("xem bóng đá 2h sáng mai", "Xem bóng đá", D(2026, 10, 22, 2, 0), False),
        ("bay 2h đêm mai", "Bay", D(2026, 10, 22, 2, 0), False),
    ],
    "thứ trong tuần": [
        ("đi bơi thứ bảy này", "Đi bơi", D(2026, 10, 24), True),
        ("đi bơi thứ 7 này", "Đi bơi", D(2026, 10, 24), True),
        ("đi bơi chủ nhật này", "Đi bơi", D(2026, 10, 25), True),
        ("họp thứ tư này", "Họp", D(2026, 10, 21), True),
        ("họp thứ hai tuần này", "Họp", D(2026, 10, 19), True),
        ("họp thứ 2 tuần sau 8h", "Họp", D(2026, 10, 26, 8, 0), False),
        ("đón con 4h30 chiều thứ sáu", "Đón con", D(2026, 10, 23, 16, 30), False),
        ("chạy bộ 5h sáng thứ hai", "Chạy bộ", D(2026, 10, 26, 5, 0), False),
    ],
    "câu thường ngày": [
        ("họp 9h sáng mai", "Họp", D(2026, 10, 22, 9, 0), False),
        ("họp lúc 9 giờ sáng mai", "Họp", D(2026, 10, 22, 9, 0), False),
        ("gọi mẹ 8 giờ tối nay", "Gọi mẹ", D(2026, 10, 21, 20, 0), False),
        ("đi siêu thị chiều nay", "Đi siêu thị", D(2026, 10, 21, 15, 0), False),
        ("họp 14h ngày 25/10", "Họp", D(2026, 10, 25, 14, 0), False),
        ("khám răng 9h ngày 3/11", "Khám răng", D(2026, 11, 3, 9, 0), False),
        ("nộp báo cáo 30/10", "Nộp báo cáo", D(2026, 10, 30), True),
        ("đi đám cưới ngày 15 tháng 11", "Đi đám cưới", D(2026, 11, 15), True),
        ("đi chợ hôm nay", "Đi chợ", D(2026, 10, 21), True),
        ("đi chợ bữa nay", "Đi chợ", D(2026, 10, 21), True),
        ("đi chợ ngày mai", "Đi chợ", D(2026, 10, 22), True),
        ("họp ngày kia 10h", "Họp", D(2026, 10, 23, 10, 0), False),
        ("họp lúc 15:30 mai", "Họp", D(2026, 10, 22, 15, 30), False),
        ("họp ba giờ chiều mai", "Họp", D(2026, 10, 22, 15, 0), False),
        ("đi khám 7 giờ kém 15 sáng mai", "Đi khám", D(2026, 10, 22, 6, 45), False),
        ("dọn nhà cuối tuần này", "Dọn nhà", D(2026, 10, 24), True),
        ("họp đầu tháng sau", "Họp", D(2026, 11, 1), True),
        ("nộp hồ sơ trước ngày 30/10", "Nộp hồ sơ", D(2026, 10, 30), True),
        ("đón con sau 2 giờ chiều", "Đón con", D(2026, 10, 21, 14, 0), False),
        ("đi xem phim tối thứ sáu tuần sau", "Đi xem phim", D(2026, 10, 30, 19, 0), False),
        ("họp 8h30 sáng thứ ba tuần tới", "Họp", D(2026, 10, 27, 8, 30), False),
        ("họp trưa mai", "Họp", D(2026, 10, 22, 12, 0), False),
        ("gặp khách 10 giờ 15 mai", "Gặp khách", D(2026, 10, 22, 10, 15), False),
        ("nấu cơm 5 giờ chiều", "Nấu cơm", D(2026, 10, 21, 17, 0), False),
        ("đi học 6h45 sáng mai", "Đi học", D(2026, 10, 22, 6, 45), False),
        ("mua quà 25/12", "Mua quà", D(2026, 12, 25), True),
        ("họp lớp 1/1/2027", "Họp lớp", D(2027, 1, 1), True),
    ],
}

# (câu, tên việc, bắt đầu, kiểu lặp, nhắc trước phút)
REPEAT_REMIND_CASES = [
    ("uống thuốc 8h sáng mỗi ngày", "Uống thuốc", D(2026, 10, 22, 8, 0), "daily", None),
    ("tưới cây 7h sáng hằng ngày", "Tưới cây", D(2026, 10, 22, 7, 0), "daily", None),
    ("tập gym 6h tối thứ 2 hàng tuần", "Tập gym", D(2026, 10, 26, 18, 0), "weekly", None),
    ("họp giao ban 8h thứ hai mỗi tuần", "Họp giao ban", D(2026, 10, 26, 8, 0), "weekly", None),
    ("đi chợ phiên 8h sáng chủ nhật hàng tuần", "Đi chợ phiên", D(2026, 10, 25, 8, 0), "weekly", None),
    ("cúng rằm mỗi tháng", "Cúng rằm", D(2026, 10, 24), "lunar_monthly", None),
    ("đóng tiền điện ngày 10 hàng tháng", "Đóng tiền điện", D(2026, 11, 10), "monthly", None),
    ("sinh nhật mẹ 20/11", "Sinh nhật mẹ", D(2026, 11, 20), "yearly", None),
    ("kỷ niệm ngày cưới 14/2", "Kỷ niệm ngày cưới", D(2027, 2, 14), "yearly", None),
    ("sinh nhật con 5/3 hằng năm", "Sinh nhật con", D(2027, 3, 5), "yearly", None),
    ("nhắc tôi trước 30 phút họp 3h chiều mai", "Họp", D(2026, 10, 22, 15, 0), None, 30),
    ("họp 3h chiều mai nhắc trước 1 tiếng", "Họp", D(2026, 10, 22, 15, 0), None, 60),
    ("khám thai 9h thứ năm báo trước 2 tiếng", "Khám thai", D(2026, 10, 22, 9, 0), None, 120),
]

# (câu, tên việc, ngày âm, tháng âm, kiểu lặp, ngày dương lần tới)
LUNAR_CASES = [
    ("rằm tháng giêng đi chùa", "Đi chùa", 15, 1, "lunar_yearly", D(2027, 2, 20)),
    ("đi chùa rằm tháng 1 âm", "Đi chùa", 15, 1, "lunar_yearly", D(2027, 2, 20)),
    ("giỗ bà mùng 8 tháng chạp", "Giỗ bà", 8, 12, "lunar_yearly", D(2027, 1, 15)),
    ("giỗ ông 10/3 âm lịch", "Giỗ ông", 10, 3, "lunar_yearly", D(2027, 4, 16)),
]

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

    def test_lunar_cases(self):
        for text, title, ld, lm, rep, start in LUNAR_CASES:
            with self.subTest(text=text):
                r = parse_vi(text, NOW)
                self.assertEqual((r.title, r.lunar, r.repeat, r.start), (title, (ld, lm), rep, start), r.warnings)

    def test_night_range(self):
        r = parse_vi("trực từ 10h đến 11h đêm", NOW)
        self.assertEqual((r.start, r.duration_min), (D(2026, 10, 21, 22, 0), 60))

    def test_repeat_remind_cases(self):
        for text, title, start, rep, remind in REPEAT_REMIND_CASES:
            with self.subTest(text=text):
                r = parse_vi(text, NOW)
                self.assertEqual((r.title, r.start, r.repeat, r.remind_before_min), (title, start, rep, remind), r.warnings)

    def test_table_size(self):
        n = sum(map(len, CASES.values())) + len(LUNAR_CASES) + len(REPEAT_REMIND_CASES)
        self.assertGreaterEqual(n, 110)

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
