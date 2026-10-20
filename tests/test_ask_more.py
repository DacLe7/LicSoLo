"""E16: hộp hỏi trong trang dùng cho cả "Quên cụm từ" và "Nhập bản sao lưu"; lời giải thích khớp hành vi thật."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.ui import PAGE

NOW = datetime(2026, 10, 21, 10, 0)


def script():
    return "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))


class TestAskMore(unittest.TestCase):
    def test_quen_cum_tu_hoi_truoc(self):
        js = script()
        block = re.search(r"#phl \.del'\)\.forEach\(b=>b\.onclick=async\(\)=>\{(.*?)phr\(\);\}\);", js, re.S).group(1)
        self.assertLess(block.index("await ask("), block.index("method:'DELETE'"))
        self.assertIn("if(!await ask(", block)

    def test_nhap_sao_luu_hoi_truoc(self):
        js = script()
        block = re.search(r"\$\('rs'\)\.onchange=async e=>\{(.*?)\n  e\.target\.value='';\};", js, re.S).group(1)
        self.assertLess(block.index("await ask("), block.index("fetch('/import'"))
        self.assertIn("e.target.value='';return;", block)   # Hủy thì chọn lại được cùng tệp

    def test_loi_giai_thich_khop_hanh_vi(self):
        """RESTORE_NOTE nói "không xóa việc nào, giữ cài đặt đã đặt": kiểm tra đúng như vậy trong Service."""
        note = re.search(r"const RESTORE_NOTE='([^']*)'", PAGE).group(1)
        self.assertIn("không việc nào bị xóa", note)
        self.assertIn("giữ nguyên", note)
        a = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        a.create("Họp nhóm", NOW + timedelta(hours=2))
        a.update_settings(name="An")
        data = json.loads(json.dumps(a.export_all()))
        b = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        b.create("Khám răng", NOW + timedelta(days=1))
        b.update_settings(name="Bình")
        b.import_all(data)
        titles = sorted(e["title"] for e in b.list_range(NOW, NOW + timedelta(days=3)))
        self.assertEqual(titles, ["Họp nhóm", "Khám răng"])
        self.assertEqual(b.settings()["name"], "Bình")

    @unittest.skipUnless(shutil.which("node"), "không có node để chạy JavaScript")
    def test_forget_text(self):
        f = re.search(r"const forgetText=.*?;\n", PAGE).group(0)
        r = subprocess.run(["node", "-e", f + "console.log(forgetText({src:'chìu',dst:'chiều'}))"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "App sẽ thôi tự hiểu “chìu” là “chiều”. Lần sau gặp cụm này, app hỏi AI lại như lần đầu.")


if __name__ == "__main__":
    unittest.main()
