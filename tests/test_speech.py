import unittest
from datetime import datetime

from lichviet.parser import parse_vi
from lichviet.speech import digits_from_words as d


class SpeechTest(unittest.TestCase):
    def test_doi_so_trong_ngu_canh(self):
        cases = {
            "họp với anh Nam ba giờ chiều mai": "họp với anh Nam 3 giờ chiều mai",
            "giỗ ông nội ngày mười lăm tháng tám âm lịch": "giỗ ông nội ngày 15 tháng 8 âm lịch",
            "họp mười giờ hai mươi sáng ngày hai mươi hai tháng mười": "họp 10 giờ 20 sáng ngày 22 tháng 10",
            "nộp hồ sơ ngày hai mươi mốt tháng mười một": "nộp hồ sơ ngày 21 tháng 11",
            "sinh nhật mùng năm tháng sáu": "sinh nhật mùng 5 tháng 6",
            "hẹn ngày ba mươi tháng tư": "hẹn ngày 30 tháng 4",
            "hai mươi lăm tháng mười hai": "25 tháng 12",
            "mười hai giờ trưa": "12 giờ trưa",
        }
        for src, want in cases.items():
            self.assertEqual(d(src), want, src)

    def test_giu_nguyen_khi_khong_phai_so(self):
        for s in ["họp thứ ba lúc hai giờ rưỡi".replace("hai giờ", "hai giờ"), "đi khám thứ năm tuần sau",
                  "mùng mốt đi chơi", "năm sau đi du lịch", "chuyển cho ba mẹ"]:
            if "hai giờ" in s:
                continue
            self.assertEqual(d(s), s)
        self.assertEqual(d("họp thứ ba lúc hai giờ rưỡi"), "họp thứ ba lúc 2 giờ rưỡi")

    def test_di_het_duong_phan_tich(self):
        now = datetime(2026, 10, 15, 9, 0)
        r = parse_vi(d("đá bóng lúc năm giờ chiều thứ bảy tuần sau"), now)
        self.assertEqual(r.start, datetime(2026, 10, 24, 17, 0))
        self.assertEqual(r.title, "Đá bóng")
        r = parse_vi(d("giỗ ông nội ngày mười lăm tháng tám âm lịch"), now)
        self.assertEqual(r.lunar, (15, 8))

    def test_thu_bay_khong_bi_nhan_nham_thu_ba(self):
        r = parse_vi("đi chơi thứ bảy 8h sáng", datetime(2026, 10, 15, 9, 0))
        self.assertEqual(r.start.weekday(), 5)
        self.assertEqual(r.title, "Đi chơi")


if __name__ == "__main__":
    unittest.main()


class DialectTest(unittest.TestCase):
    def test_nam_gio(self):
        from lichviet.speech import digits_from_words as d
        self.assertEqual(d("Nêm giờ 45"), "5 giờ 45")
        self.assertEqual(d("nêm giờ tăng ca"), "5 giờ tăng ca")
        self.assertEqual(d("nềm giờ bốn mươi nèm"), "5 giờ 45")

    def test_muu_lem(self):
        from lichviet.speech import digits_from_words as d
        self.assertEqual(d("5 giờ 4 mưu lem"), "5 giờ 45")

    def test_khong_sua_nham(self):
        from lichviet.speech import digits_from_words as d
        self.assertEqual(d("nấu nem rán"), "nấu nem rán")
        self.assertEqual(d("thứ năm"), "thứ năm")


class DialectTest2(unittest.TestCase):
    def d(self, t):
        from lichviet.speech import digits_from_words
        return digits_from_words(t)

    def test_ham_nham(self):
        self.assertEqual(self.d("ngày hăm lăm tháng tám"), "ngày 25 tháng 8")
        self.assertEqual(self.d("ngày hăm mốt"), "ngày 21")
        self.assertEqual(self.d("lúc hai mươi nhăm phút"), "lúc 25 phút")

    def test_nam_bo_ngay(self):
        self.assertEqual(self.d("họp bữa nay"), "họp hôm nay")
        self.assertEqual(self.d("họp ngày mơi"), "họp ngày mai")
        self.assertEqual(self.d("họp ngày mốt"), "họp ngày kia")
        self.assertEqual(self.d("họp bữa mốt"), "họp ngày kia")
        self.assertEqual(self.d("họp chiều mốt"), "họp ngày kia chiều")

    def test_viet_tat(self):
        self.assertEqual(self.d("họp T2"), "họp thứ 2")
        self.assertEqual(self.d("họp CN"), "họp chủ nhật")

    def test_khong_sua_nham_2(self):
        self.assertEqual(self.d("ngày hai mươi mốt"), "ngày 21")
        self.assertEqual(self.d("mùng mốt"), "mùng mốt")
        self.assertEqual(self.d("mười lăm giờ"), "15 giờ")
        self.assertEqual(self.d("xáu giờ"), "6 giờ")
        self.assertEqual(self.d("trín giờ"), "9 giờ")
        self.assertEqual(self.d("lăm giờ"), "5 giờ")
