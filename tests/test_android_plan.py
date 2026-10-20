"""Mặc định chỉ mở trên máy này (127.0.0.1); tài liệu Android có đủ các cách và nói rõ đánh đổi riêng tư."""
import inspect
import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from lichviet import api, __main__ as cli


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class TestDefaultBinding(unittest.TestCase):
    def test_compose_chi_mo_127(self):
        ports = re.findall(r'^\s*-\s*"([^"]*:\d+)"\s*$', read("solohost", "docker-compose.yml"), re.M)
        self.assertTrue(ports)
        for p in ports:
            self.assertTrue(p.startswith("127.0.0.1:"), p)

    def test_serve_mac_dinh_127(self):
        self.assertEqual(inspect.signature(api.serve).parameters["host"].default, "127.0.0.1")
        self.assertIn('os.environ.get("LICHVIET_HOST", "127.0.0.1")', inspect.getsource(cli))

    def test_host_la_bi_chan(self):
        self.assertTrue(api.host_ok("localhost:18763"))
        self.assertFalse(api.host_ok("192.168.1.10:18763"))   # IP mạng nội bộ phải thêm vào LICHVIET_ALLOWED_HOSTS
        self.assertFalse(api.host_ok("may.tail1234.ts.net"))


class TestAndroidPlan(unittest.TestCase):
    def test_noi_dung(self):
        t = read("docs", "ANDROID_PLAN.md")
        for must in ("adb reverse", "Tailscale", "LICHVIET_ALLOWED_HOSTS", "trang an toàn", "Riêng tư",
                     "Khuyến nghị", "whisper", "127.0.0.1"):
            self.assertIn(must.lower(), t.lower(), must)
        self.assertIn("ANDROID_PLAN.md", read("docs", "HUONG_DAN.md"))

    def test_huong_dan_adb_tung_buoc(self):
        t = read("docs", "HUONG_DAN.md")
        m = re.search(r"^## (\d+)\. Dùng thử trên điện thoại Android qua cáp USB$(.*?)^## ", t, re.M | re.S)
        self.assertTrue(m)
        sec = m.group(2)
        for must in ("Gỡ lỗi USB", "Platform-Tools", "adb devices", "unauthorized",
                     "adb reverse tcp:18763 tcp:18763", "http://localhost:18763", "adb reverse --remove-all"):
            self.assertIn(must, sec, must)
        # cổng trong lệnh khớp cổng mặc định của compose
        self.assertIn("PANEL_PORT:-18763", read("solohost", "docker-compose.yml"))
        self.assertIn("theo mục %s ở trên" % m.group(1), t)


if __name__ == "__main__":
    unittest.main()
