import tempfile
import unittest
from datetime import datetime

from lichviet.service import Service


class HeardTest(unittest.TestCase):
    def setUp(self):
        self.s = Service(tempfile.mktemp(), clock=lambda: datetime(2026, 10, 15, 9, 0))

    def test_hoc_sau_hai_lan(self):
        for _ in range(2):
            self.assertEqual(self.s.learn_heard("họp tạng ca chiều nay", "họp tăng ca chiều nay"), 1)
        self.assertEqual(self.s._apply_heard("nay tạng ca nhé"), "nay tăng ca nhé")

    def test_chua_du_so_lan_thi_chua_sua(self):
        self.s.learn_heard("họp tạng ca", "họp tăng ca")
        self.assertEqual(self.s._apply_heard("tạng ca"), "tạng ca")

    def test_doi_noi_dung_khong_hoc(self):
        self.assertEqual(self.s.learn_heard("họp 3 giờ chiều", "họp 4 giờ chiều"), 0)
        self.assertEqual(self.s.learn_heard("họp với anh Nam", "đi chợ với chị Lan"), 0)

    def test_hoc_cho_thanh_so(self):
        for _ in range(2):
            self.s.learn_heard("hăm bảy giờ", "27 giờ")
        self.assertIn("27", self.s._apply_heard("hăm bảy giờ"))

    def test_sao_luu_co_heard(self):
        self.s.learn_heard("họp tạng ca", "họp tăng ca")
        self.assertEqual(len(self.s.export_all()["heard"]), 1)

if __name__ == "__main__":
    unittest.main()
