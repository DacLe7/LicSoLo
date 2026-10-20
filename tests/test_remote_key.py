"""D3 (lần 10): mở app từ máy khác trong mạng (Host thêm qua LICHVIET_ALLOWED_HOSTS) thì giao diện không còn được tin
theo same-origin, phải gửi khóa như mọi client khác. Trên chính máy này (127.0.0.1, localhost qua adb reverse) giữ nguyên."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import api, pwa
from lichviet.ui import PAGE
from test_ecosystem import Srv, svc, KEY

LAN = {"LICHVIET_ALLOWED_HOSTS": "192.168.1.5, may.tail1234.ts.net"}
UI = {"Sec-Fetch-Site": "same-origin"}


class TestHostIsLocal(unittest.TestCase):
    def test_local_names(self):
        with mock.patch.dict(os.environ, LAN):
            for h in ("127.0.0.1:18763", "localhost", "[::1]:8765", "app:8765"):
                self.assertTrue(api.host_is_local(h), h)
            for h in ("192.168.1.5:18763", "may.tail1234.ts.net", "", None):
                self.assertFalse(api.host_is_local(h), h)

    def test_extra_name_without_dot_is_remote(self):
        with mock.patch.dict(os.environ, {"LICHVIET_ALLOWED_HOSTS": "dienthoai"}):
            self.assertFalse(api.host_is_local("dienthoai:18763"))
            self.assertTrue(api.host_ok("dienthoai:18763"))


class TestRemoteNeedsKey(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {**LAN, "LICHVIET_API_KEY": KEY})
        self.env.start()
        self.s = Srv(svc(), {"LICHVIET_API_KEY": KEY})

    def tearDown(self):
        self.s.close()
        self.env.stop()

    def test_local_ui_still_trusted(self):
        self.assertEqual(self.s.call("GET", "/v1/info", headers=UI)[0], 200)
        self.assertEqual(self.s.call("GET", "/v1/info", headers={**UI, "Host": "localhost:18763"})[0], 200)

    def test_remote_ui_needs_key(self):
        for host in ("192.168.1.5:18763", "may.tail1234.ts.net"):
            with self.subTest(host=host):
                h = {**UI, "Host": host}
                self.assertEqual(self.s.call("GET", "/v1/events", headers=h)[0], 401)
                h2 = {"Host": host, "Origin": "http://" + host}
                self.assertEqual(self.s.call("GET", "/v1/info", headers=h2)[0], 401)
                self.assertEqual(self.s.call("GET", "/v1/info", headers={**h, "X-Lacviet-Key": KEY})[0], 200)

    def test_remote_page_and_health_open(self):
        h = {**UI, "Host": "192.168.1.5:18763"}
        self.assertEqual(self.s.call("GET", "/", headers=h)[0], 200)        # trang tải được để nhập khóa
        self.assertEqual(self.s.call("GET", "/sw.js", headers=h)[0], 200)
        self.assertEqual(self.s.call("GET", "/health", headers=h)[0], 200)


class TestRemoteWithoutKey(unittest.TestCase):
    def test_open_as_before_and_warns_at_start(self):
        with mock.patch.dict(os.environ, {**LAN, "LICHVIET_API_KEY": ""}):
            s = Srv(svc(), {"LICHVIET_API_KEY": ""})
            try:
                self.assertEqual(s.call("GET", "/v1/info", headers={**UI, "Host": "192.168.1.5"})[0], 200)
            finally:
                s.close()
            with mock.patch.object(api, "Server") as Server, self.assertLogs("lichviet.api", "WARNING") as cm:
                Server.return_value.serve_forever.side_effect = KeyboardInterrupt
                with self.assertRaises(KeyboardInterrupt):
                    api.serve(":memory:")
            self.assertTrue(any("LICHVIET_API_KEY" in m and "192.168.1.5" in m for m in cm.output), cm.output)


class TestPageSendsKey(unittest.TestCase):
    def test_page_has_key_box_and_header(self):
        for must in ('id="keybar"', 'id="keyin"', "'X-Lacviet-Key'", "KEY.ask()", "lv_key", "a[download]"):
            self.assertIn(must, PAGE, must)
        self.assertIn('type="password"', PAGE)

    def test_all_raw_fetches_send_key(self):
        """Mọi fetch gọi thẳng (ngoài j()) tới API phải gửi khóa qua KEY.h."""
        import re
        for m in re.finditer(r"fetch\('(/[^']*)',\{([^}]*)", PAGE):
            with self.subTest(url=m.group(1)):
                self.assertIn("KEY.h(", m.group(2))

    def test_sw_hands_ack_back_to_page(self):
        sw = pwa.FILES["/sw.js"][0]().decode("utf-8")
        self.assertIn("ack:{event_id", sw)
        self.assertIn("e.data.ack", PAGE)


if __name__ == "__main__":
    unittest.main()
