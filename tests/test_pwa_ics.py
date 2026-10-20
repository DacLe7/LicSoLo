"""Cài app lên máy (manifest, biểu tượng, service worker), thông báo hệ thống trong trang, tải .ics từng việc.
Giờ giả lập: Thứ Hai 19/10/2026 09:00 (NOW của test_ecosystem)."""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import zlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import ics, pwa
from lichviet.tz import get_tz
from lichviet.ui import PAGE
from test_ecosystem import KEY, NOW, Srv, svc


def png_info(b):
    """(rộng, cao, loại màu) và kiểm tra CRC từng khối."""
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    i, out = 8, None
    while i < len(b):
        n, tag = struct.unpack(">I4s", b[i:i + 8])
        data = b[i + 8:i + 8 + n]
        assert struct.unpack(">I", b[i + 8 + n:i + 12 + n])[0] == zlib.crc32(tag + data) & 0xffffffff
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", data[:10])
            out = (w, h, ct)
        i += 12 + n
    return out


class TestPwaFiles(unittest.TestCase):
    def test_manifest(self):
        m = json.loads(pwa.MANIFEST)
        self.assertEqual((m["lang"], m["display"], m["start_url"]), ("vi", "standalone", "/"))
        sizes = {i["sizes"] for i in m["icons"] if i["type"] == "image/png"}
        self.assertTrue({"192x192", "512x512"} <= sizes)
        self.assertTrue(any(i.get("purpose") == "maskable" for i in m["icons"]))
        for i in m["icons"]:
            self.assertIn(i["src"], pwa.FILES)

    def test_icons_are_valid_png(self):
        self.assertEqual(png_info(pwa.icon_png(192)), (192, 192, 6))
        self.assertEqual(png_info(pwa.icon_png(48, True)), (48, 48, 6))

    @unittest.skipUnless(shutil.which("node"), "không có node để kiểm tra cú pháp JavaScript")
    def test_sw_syntax(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(pwa.SW)
        self.addCleanup(os.unlink, f.name)
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_sw_khong_luu_du_lieu(self):
        self.assertNotIn("caches.open", pwa.SW)          # không lưu đệm dữ liệu người dùng
        self.assertIn("notificationclick", pwa.SW)
        self.assertIn("/reminders/ack", pwa.SW)

    def test_page_links(self):
        self.assertIn('rel="manifest" href="/manifest.webmanifest"', PAGE)
        self.assertIn("serviceWorker.register('/sw.js')", PAGE)
        # chỉ xin quyền khi người dùng bấm nút, không tự hỏi lúc tải trang
        self.assertEqual(PAGE.count("Notification.requestPermission"), 1)
        self.assertIn("async ask()", PAGE)

    def test_served_without_key(self):
        s = Srv(svc(), {"LICHVIET_API_KEY": KEY})
        self.addCleanup(s.close)
        for path, ctype in (("/manifest.webmanifest", "manifest"), ("/sw.js", "javascript"),
                            ("/icon.svg", "svg")):
            code, _, h = s.call("GET", path)
            self.assertEqual(code, 200, path)
            self.assertIn(ctype, h["Content-Type"], path)
        self.assertEqual(s.call("GET", "/sw.js")[2]["Cache-Control"], "no-cache")
        with urllib.request.urlopen(s.base + "/icon-512.png", timeout=5) as x:
            self.assertEqual(x.headers["Content-Type"], "image/png")
            self.assertEqual(png_info(x.read())[:2], (512, 512))
        # API dữ liệu vẫn cần khóa
        self.assertEqual(s.call("GET", "/v1/events/1.ics")[0], 401)


class TestEventIcs(unittest.TestCase):
    def setUp(self):
        self.s = svc()

    def ics(self, eid):
        return ics.render_event(self.s.event_calendar(eid), NOW, get_tz())

    def test_mot_lan(self):
        e = self.s.create("Họp, nhóm", datetime(2026, 10, 20, 14, 0), duration_min=60, remind_before_min=15)
        t = self.ics(e["id"])
        self.assertEqual(t.count("BEGIN:VEVENT"), 1)
        self.assertIn("SUMMARY:Họp\\, nhóm", t)
        self.assertIn("DTEND:", t)
        self.assertNotIn("RRULE", t)
        self.assertNotIn("REFRESH-INTERVAL", t)          # tệp tải một lần, không phải đăng ký
        self.assertIn("TRIGGER;VALUE=DATE-TIME:", t)
        self.assertTrue(t.endswith("\r\n"))

    def test_lap_chuan_dung_rrule(self):
        e = self.s.create("Tập thể dục", datetime(2026, 10, 20, 6, 0), repeat="daily", remind_before_min=10)
        t = self.ics(e["id"])
        self.assertEqual(t.count("BEGIN:VEVENT"), 1)
        self.assertIn("RRULE:FREQ=DAILY", t)
        self.assertIn("TRIGGER:-PT10M", t)

    def test_sinh_nhat_ca_ngay(self):
        e = self.s.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        t = self.ics(e["id"])
        self.assertIn("RRULE:FREQ=YEARLY", t)
        self.assertIn("DTSTART;VALUE=DATE:20261120", t)
        self.assertIn("TRIGGER:PT480M", t)               # cả ngày: app nhắc lúc 8h sáng

    def test_khong_co_rrule_chuan_liet_ke_tung_lan(self):
        e = self.s.create("Trả tiền nhà", datetime(2026, 10, 31, 9, 0), repeat="monthly")
        t = self.ics(e["id"])
        self.assertNotIn("RRULE", t)
        self.assertEqual(t.count("BEGIN:VEVENT"), 24)
        self.assertIn("DTSTART:20261130", t)             # tháng 11 không có 31: lùi về 30 như app
        g = self.s.create("Giỗ ông", datetime(2026, 12, 1), all_day=True, repeat="lunar_yearly", lunar=(12, 10))
        t = self.ics(g["id"])
        self.assertNotIn("RRULE", t)
        self.assertEqual(t.count("BEGIN:VEVENT"), 10)
        self.assertIn("Âm lịch: 12/10 hằng năm", t)

    def test_api(self):
        e = self.s.create("Khám răng", datetime(2026, 10, 22, 8, 30))
        srv = Srv(self.s, {"LICHVIET_API_KEY": ""})
        self.addCleanup(srv.close)
        code, body, h = srv.call("GET", "/v1/events/%d.ics" % e["id"])
        self.assertEqual(code, 200)
        self.assertIn("text/calendar", h["Content-Type"])
        self.assertIn("lichviet-%d.ics" % e["id"], h["Content-Disposition"])
        self.assertIn("SUMMARY:Khám răng", body)
        self.assertEqual(srv.call("GET", "/events/9999.ics")[0], 404)
        self.assertEqual(srv.call("GET", "/events/abc.ics")[0], 404)


if __name__ == "__main__":
    unittest.main()
