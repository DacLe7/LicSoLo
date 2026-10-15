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
                  "ngày mốt đi chơi", "năm sau đi du lịch", "chuyển cho ba mẹ"]:
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
