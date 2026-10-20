"""Hộp xác nhận xóa trong trang (E13) và ô chọn nhanh "Nhắc trước" trong form Sửa (C11)."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.ui import PAGE


def script():
    return "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))


class TestAskDialog(unittest.TestCase):
    def test_hop_xac_nhan_trong_trang(self):
        self.assertRegex(PAGE, r'<dialog class="ask" id="ask" aria-labelledby="ask_t" aria-describedby="ask_d">')
        self.assertIn('<form method="dialog">', PAGE)
        self.assertIn('id="ask_no">Hủy</button>', PAGE)
        js = script()
        self.assertIn("showModal", js)
        self.assertIn("$('ask_no').focus()", js)       # mặc định chọn Hủy cho an toàn
        # confirm() chỉ còn làm dự phòng trong ask() cho trình duyệt cũ
        self.assertEqual(len(re.findall(r"\bconfirm\(", js)), 1)
        self.assertIn("await ask(", js)

    def test_cau_xoa_viec_lap(self):
        self.assertIn("xóa là xóa cả chuỗi", script())


class TestRemindSelect(unittest.TestCase):
    def test_form_sua_dung_o_chon(self):
        js = script()
        self.assertIn("<select id=\"e_m\">'+remOpts(d.remind_before_min)", js)
        self.assertNotIn('id="e_m" type="number"', js)

    @unittest.skipUnless(shutil.which("node"), "không có node để chạy JavaScript")
    def test_remopts(self):
        m = re.search(r"const mins=.*?;\n", PAGE).group(0)
        r_ = re.search(r"const REMOPT=.*?;\n", PAGE).group(0)
        f = re.search(r"function remOpts\(v\)\{.*?\n\}\n", PAGE, re.S).group(0)
        js = m + r_ + f + """
const pick=h=>[...h.matchAll(/<option value="(\\d*)"( selected)?>([^<]*)</g)].map(x=>[x[1],!!x[2],x[3]]);
console.log(JSON.stringify([null,0,15,45,10080].map(v=>pick(remOpts(v)))));"""
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        sel = [[o for o in opts if o[1]] for opts in out]
        self.assertEqual(sel[0], [["", True, "Không, nhắc đúng giờ"]])
        self.assertEqual(sel[1], [["", True, "Không, nhắc đúng giờ"]])
        self.assertEqual(sel[2], [["15", True, "15 phút"]])
        self.assertEqual(sel[3], [["45", True, "45 phút"]])      # giá trị lạ vẫn giữ
        self.assertEqual(sel[4], [["10080", True, "1 tuần"]])
        vals = [int(o[0]) for o in out[3] if o[0]]
        self.assertEqual(vals, sorted(vals))
        self.assertEqual(len(out[3]), len(out[2]) + 1)
        self.assertIn(["1440", False, "1 ngày"], out[2])
        self.assertIn(["2880", False, "2 ngày"], out[2])

    def test_cai_dat_dung_chung_danh_sach(self):
        """C13: ô "Nhắc trước mặc định" trong Cài đặt cá nhân dựng từ remOpts như form Sửa (có 2 ngày, 1 tuần);
        lựa chọn "không" có giá trị rỗng, gửi lên thành 0."""
        js = script()
        self.assertIn("$('me_rm').innerHTML=remOpts(", js)
        self.assertIn("default_remind_min:+$('me_rm').value", js)
        self.assertIsNone(re.search(r'<select id="me_rm">.*?value="1440"', PAGE, re.S))


if __name__ == "__main__":
    unittest.main()
