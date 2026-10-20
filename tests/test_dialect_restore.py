"""Luật sửa lỗi nghe theo vùng miền (B6), nút khôi phục ở màn hình chào (A12), lý do lỗi /health trong thanh mất kết nối (A13)."""
import os
import re
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.parser import parse_vi
from lichviet.speech import digits_from_words as d
from lichviet.ui import PAGE

NOW = datetime(2026, 10, 21, 9, 0)   # thứ tư


class DialectFix(unittest.TestCase):
    def test_sua_khi_ngu_canh_chac_chan(self):
        cases = {
            "họp ba dờ triều mai": "họp 3 giờ chiều mai",
            "mười dzờ sáng mai": "10 giờ sáng mai",
            "hẹn bác sĩ 9 giừ sáng": "hẹn bác sĩ 9 giờ sáng",
            "ăn cơm 12 giờ chưa": "ăn cơm 12 giờ trưa",
            "họp 11h chưa mai": "họp 11h trưa mai",
            "đi tập 6 giờ xáng mai": "đi tập 6 giờ sáng mai",
            "họp triều mai": "họp chiều mai",
            "đón con 4 giờ rưởi chiều nay": "đón con 4 giờ rưỡi chiều nay",
            "gọi mẹ 30 phút nửa": "gọi mẹ 30 phút nữa",
            "trả sách 2 ngày lữa": "trả sách 2 ngày nữa",
            "khám bệnh tuần xau": "khám bệnh tuần sau",
            "uống thuốc 7 giờ tối mõi ngày": "uống thuốc 7 giờ tối mỗi ngày",
            "đi chợ bửa nay": "đi chợ bữa nay",
            "đi lễ chủ nhựt": "đi lễ chủ nhật",
            "giổ ông nội ngày mười lăm tháng tám âm lịch": "giỗ ông nội ngày 15 tháng 8 âm lịch",
            "họp tối nai": "họp tối nay",
            "đi khám hôm lay": "đi khám hôm nay",
            "lăm sau đi du lịch": "năm sau đi du lịch",
            "gọi mẹ 7 giờ tói nay": "gọi mẹ 7 giờ tối nay",
        }
        for src, want in cases.items():
            self.assertEqual(d(src), want, src)

    def test_giu_nguyen_tu_that(self):
        for s in ["xoài chín chưa", "dỗ em ngủ", "ngủ 12 giờ nửa đêm", "ăn nửa cái bánh", "triều đình nhà Nguyễn",
                  "mối tình đầu", "con nai vàng", "màu xanh lam", "ba chưa về", "đã làm chưa", "nửa tháng nữa",
                  "đọc sách nửa tiếng", "chưa ăn sáng"]:
            self.assertEqual(d(s), s, s)

    def test_giu_dau_cau(self):
        self.assertEqual(d("họp 3 giờ triều mai,"), "họp 3 giờ chiều mai,")
        self.assertEqual(d("ăn 12 giờ chưa."), "ăn 12 giờ trưa.")

    def test_di_het_duong_phan_tich(self):
        r = parse_vi(d("họp nhóm ba dờ triều mai"), NOW)
        self.assertEqual(r.start, datetime(2026, 10, 22, 15, 0))
        self.assertEqual(r.title, "Họp nhóm")
        r = parse_vi(d("ăn cơm với khách mười hai dờ chưa thứ sáu"), NOW)
        self.assertEqual(r.start, datetime(2026, 10, 23, 12, 0))
        r = parse_vi(d("uống thuốc tám dờ tối mõi ngày"), NOW)
        self.assertEqual(r.repeat, "daily")
        self.assertEqual((r.start.hour, r.start.minute), (20, 0))
        r = parse_vi(d("gọi lại cho khách ba mươi phút nửa"), NOW)
        self.assertEqual(r.start, datetime(2026, 10, 21, 9, 30))
        r = parse_vi(d("đi nhà thờ chín dờ xáng chủ nhựt"), NOW)
        self.assertEqual(r.start, datetime(2026, 10, 25, 9, 0))


class WelcomeRestoreAndHealthBanner(unittest.TestCase):
    def test_welcome_has_restore_link(self):
        welcome = re.search(r'<section class="welcome".*?</section>', PAGE, re.S).group(0)
        self.assertIn('id="wrs"', welcome)
        self.assertIn("Khôi phục từ tệp", welcome)
        js = PAGE.split("<script>", 1)[1]
        # mở mục Sao lưu và mở hộp chọn tệp của nút Khôi phục
        self.assertRegex(js, r"\$\('wrs'\)\.onclick=.*\$\('more'\).*m\.open=true.*\$\('rs'\)\.click\(\)")

    def test_net_banner_uses_health_reason(self):
        self.assertIn('id="nettxt"', PAGE)
        js = PAGE.split("<script>", 1)[1]
        self.assertIn("j('/health'", js)
        self.assertIn("App đang gặp sự cố", js)
        # trở lại bình thường thì trả câu mặc định
        self.assertIn("$('nettxt').textContent=NETMSG", js)


if __name__ == "__main__":
    unittest.main()
