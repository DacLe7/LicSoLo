import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request as U
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lichviet.api import make_handler
from lichviet.service import Service
from lichviet.stt import STTClient


class Fake(BaseHTTPRequestHandler):
    def _j(self, o):
        b = json.dumps(o).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._j({"ready": True, "model": "fake"})

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self._j({"text": "họp với anh Nam ba giờ chiều mai"})

    def log_message(self, *a):
        pass


class STTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.fake.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d" % cls.fake.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.fake.shutdown(); cls.fake.server_close()

    def _api(self, stt):
        svc = Service(tempfile.mktemp(suffix=".db"), stt=stt)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(svc))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return "http://127.0.0.1:%d" % srv.server_address[1]

    def test_tat_thi_bao_503(self):
        base = self._api(STTClient(""))
        self.assertFalse(json.load(U.urlopen(base + "/stt/status"))["enabled"])
        with self.assertRaises(urllib.error.HTTPError) as c:
            U.urlopen(U.Request(base + "/stt", b"x" * 10, method="POST"))
        self.assertEqual(c.exception.code, 503)

    def test_bat_thi_tra_chu(self):
        base = self._api(STTClient(self.url))
        st = json.load(U.urlopen(base + "/stt/status"))
        self.assertTrue(st["enabled"] and st["ready"])
        r = json.load(U.urlopen(U.Request(base + "/stt", b"RIFF" + b"0" * 100, method="POST")))
        self.assertIn("họp", r["text"])
        r2 = json.load(U.urlopen(U.Request(base + "/v1/stt", b"RIFF" + b"0" * 100, method="POST")))
        self.assertEqual(r, r2)

    def test_am_thanh_rong(self):
        base = self._api(STTClient(self.url))
        with self.assertRaises(urllib.error.HTTPError) as c:
            U.urlopen(U.Request(base + "/stt", b"", method="POST"))
        self.assertEqual(c.exception.code, 400)

    def test_chi_bat_khi_che_do_voice(self):
        import os
        old = dict(os.environ)
        try:
            os.environ["LICHVIET_STT_URL"] = self.url
            os.environ["LICHVIET_AI"] = "ai"
            self.assertFalse(STTClient().enabled)
            os.environ["LICHVIET_AI"] = "both"
            self.assertTrue(STTClient().enabled)
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
