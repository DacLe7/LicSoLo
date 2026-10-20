"""Trang giao diện: JavaScript không lỗi cú pháp, có các phần báo lỗi thân thiện và tiến độ giọng nói."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.ui import PAGE


def script():
    return "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))


class TestPage(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "không có node để kiểm tra cú pháp JavaScript")
    def test_js_syntax(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(script())
        self.addCleanup(os.unlink, f.name)
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_friendly_errors(self):
        js = script()
        self.assertIn("Không nối được với app", js)
        self.assertIn("AbortController", js)        # có hạn chờ, nút không treo mãi
        self.assertIn('id="net"', PAGE)              # thanh báo mất kết nối
        # mọi lời gọi API đi qua j(); chỉ còn fetch trong j() và gửi âm thanh /stt, lưu từ form, học cụm từ, nhập tệp
        self.assertLessEqual(len(re.findall(r"\bfetch\(", js)), 5)

    def test_voice_progress(self):
        self.assertIn('id="vstat"', PAGE)
        self.assertIn("VStat.poll()", script())

    def test_live_regions(self):
        self.assertRegex(PAGE, r'id="toast"[^>]*aria-live="polite"')


if __name__ == "__main__":
    unittest.main()
