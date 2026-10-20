"""Ngày tương đối: đã qua (hôm kia, bữa hổm, N ngày trước, tuần trước) và sắp tới (N ngày nữa).
Giờ giả lập: Thứ Tư 21/10/2026 10:00."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi

NOW = datetime(2026, 10, 21, 10, 0)


def at(text):
    r = parse_vi(text, NOW)
    return r.start, r.all_day, r.title, r.remind_before_min, r.warnings


class TestPastDates(unittest.TestCase):
    def test_hom_kia(self):
        self.assertEqual(at("họp hôm kia")[:3], (datetime(2026, 10, 19), True, "Họp"))
        self.assertEqual(at("hom kia di kham 9h")[:3], (datetime(2026, 10, 19, 9, 0), False, "Di kham"))

    def test_ngay_kia_van_la_tuong_lai(self):
        self.assertEqual(at("họp ngày kia")[0], datetime(2026, 10, 23))
        self.assertEqual(at("họp ngày mốt")[0], datetime(2026, 10, 23))

    def test_bua_hom_qua_va_bua_nay(self):
        self.assertEqual(at("đi chơi bữa hôm qua")[:3], (datetime(2026, 10, 20), True, "Đi chơi"))
        self.assertEqual(at("đi chơi bữa qua")[0], datetime(2026, 10, 20))
        self.assertEqual(at("đi chợ bữa nay 5h chiều")[:3], (datetime(2026, 10, 21, 17, 0), False, "Đi chợ"))
        self.assertEqual(at("bữa hôm nay đi chợ")[2], "Đi chợ")

    def test_bua_hom_khong_ro_ngay_co_canh_bao(self):
        for s, cum in (("gặp bạn bữa hổm", "bữa hổm"), ("gặp bạn hôm bữa", "hôm bữa"), ("gặp bạn bữa hôm", "bữa hôm")):
            start, all_day, title, _, warns = at(s)
            self.assertEqual((start, all_day, title), (datetime(2026, 10, 18), True, "Gặp bạn"), s)
            self.assertTrue(any(cum in w and "3 ngày trước" in w for w in warns), (s, warns))

    def test_n_ngay_truoc(self):
        self.assertEqual(at("khám răng 3 ngày trước")[:3], (datetime(2026, 10, 18), True, "Khám răng"))
        self.assertEqual(at("khám răng 2 hôm trước")[0], datetime(2026, 10, 19))
        self.assertEqual(at("họp 1 tuần trước lúc 9h")[:2], (datetime(2026, 10, 14, 9, 0), False))

    def test_tuan_truoc(self):
        self.assertEqual(at("họp tuần trước")[:3], (datetime(2026, 10, 14), True, "Họp"))
        self.assertEqual(at("ăn cưới thứ ba tuần trước")[:3], (datetime(2026, 10, 13), True, "Ăn cưới"))
        self.assertEqual(at("họp chủ nhật tuần trước 8h")[0], datetime(2026, 10, 18, 8, 0))


class TestFutureRelative(unittest.TestCase):
    def test_n_ngay_nua(self):
        self.assertEqual(at("nộp bài 3 ngày nữa")[:3], (datetime(2026, 10, 24), True, "Nộp bài"))
        self.assertEqual(at("nộp bài 2 tuần nữa")[0], datetime(2026, 11, 4))
        self.assertEqual(at("sinh nhật bé 9h sáng 3 ngày nữa")[:2], (datetime(2026, 10, 24, 9, 0), False))

    def test_n_tieng_phut_nua(self):
        self.assertEqual(at("gọi mẹ 2 tiếng nữa")[:3], (datetime(2026, 10, 21, 12, 0), False, "Gọi mẹ"))
        self.assertEqual(at("tắt bếp 15 phút nữa")[0], datetime(2026, 10, 21, 10, 15))

    def test_sau_n_tuan(self):
        self.assertEqual(at("tái khám sau 2 tuần")[:2], (datetime(2026, 11, 4), True))


class TestRemindBeforeForms(unittest.TestCase):
    def test_nhac_toi_truoc(self):
        # trước đây "nhắc tôi trước 2 ngày" mất phần nhắc và lọt "trước 2" vào tên việc
        self.assertEqual(at("họp 15/11 nhắc tôi trước 2 ngày")[2:4], ("Họp", 2880))

    def test_nhac_n_ngay_truoc_khong_phai_ngay_da_qua(self):
        start, _, title, before, _ = at("họp 15/11 nhắc tôi 2 ngày trước")
        self.assertEqual((start, title, before), (datetime(2026, 11, 15), "Họp", 2880))
        self.assertEqual(at("họp 15/11 nhắc 30 phút trước")[3], 30)

    def test_bao_truoc(self):
        self.assertEqual(at("báo trước 30 phút họp 3h chiều mai")[:4],
                         (datetime(2026, 10, 22, 15, 0), False, "Họp", 30))


if __name__ == "__main__":
    unittest.main()
