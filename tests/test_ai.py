import sys, os, json, unittest, threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient

NOW = datetime(2026, 10, 13, 10, 0)
REPLY = {"v": '{"title": "Khám răng", "when": "ngày 23/10 lúc 14:30"}'}
CALLS = []


class Fake(BaseHTTPRequestHandler):
    def do_POST(self):
        CALLS.append(1)
        self.rfile.read(int(self.headers["Content-Length"]))
        b = json.dumps({"choices": [{"message": {"content": REPLY["v"]}}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a): pass


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def svc(self, url):
        return Service(":memory:", clock=lambda: NOW, llm=LLMClient(url, timeout=3))

    def test_ai_off_by_default(self):
        s = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        self.assertEqual(s.from_text("mua sữa")["status"], "need_info")

    def test_ai_not_called_when_rules_suffice(self):
        CALLS.clear()
        r = self.svc(self.url).from_text("họp 3h chiều mai")
        self.assertEqual((r["status"], len(CALLS)), ("draft", 0))

    def test_ai_used_when_rules_fail(self):
        CALLS.clear()
        r = self.svc(self.url).from_text("nhờ nhắc em cái vụ nha sĩ nhé")  # luật không hiểu
        self.assertEqual(r["status"], "draft")
        self.assertTrue(r["draft"]["used_ai"])
        self.assertEqual(r["draft"]["start"], "2026-10-23T14:30:00")  # ngày do luật tính, không do AI

    def test_ai_normalizes_odd_date(self):
        REPLY["v"] = '{"title": "Khám răng", "when": "ngày kia 9 giờ sáng"}'
        try:
            r = self.svc(self.url).from_text("đi khám răng ngày mốt lúc 9 giờ sáng")
            self.assertTrue(r["draft"]["used_ai"])
            self.assertEqual(r["draft"]["start"], "2026-10-15T09:00:00")
            self.assertEqual(r["draft"]["title"], "Khám răng")
        finally:
            REPLY["v"] = '{"title": "Khám răng", "when": "ngày 23/10 lúc 14:30"}'

    def test_odd_date_without_ai_keeps_warning(self):
        s = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        r = s.from_text("đi khám răng ngày mốt lúc 9 giờ sáng")
        self.assertFalse(r["draft"]["used_ai"])
        self.assertTrue(r["draft"]["warnings"])

    def test_bad_ai_output_falls_back(self):
        REPLY["v"] = "xin lỗi tôi không hiểu"
        try:
            self.assertEqual(self.svc(self.url).from_text("mua sữa")["status"], "need_info")
        finally:
            REPLY["v"] = '{"title": "Khám răng", "when": "ngày 23/10 lúc 14:30"}'

    def test_dead_server_and_circuit_breaker(self):
        c = LLMClient("http://127.0.0.1:1", timeout=1, max_fail=2, cooldown=60)
        s = Service(":memory:", clock=lambda: NOW, llm=c)
        for _ in range(3):
            self.assertEqual(s.from_text("mua sữa")["status"], "need_info")
        self.assertFalse(c.enabled)   # đã ngắt mạch


if __name__ == "__main__":
    unittest.main()


class TestEnv(unittest.TestCase):
    def test_env_switch(self):
        os.environ["LICHVIET_LLM_URL"] = "http://llm:8080"
        try:
            os.environ["LICHVIET_AI"] = "off"
            self.assertFalse(LLMClient().enabled)
            os.environ["LICHVIET_AI"] = "on"
            self.assertTrue(LLMClient().enabled)
        finally:
            os.environ.pop("LICHVIET_LLM_URL"); os.environ.pop("LICHVIET_AI")


class TestStatus(unittest.TestCase):
    def test_status_reported(self):
        s = Service(":memory:", clock=lambda: NOW, llm=LLMClient("http://127.0.0.1:1", timeout=1))
        d = s.from_text("đi khám ngày mốt lúc 9 giờ sáng")["draft"]
        self.assertEqual(d["ai"]["status"], "error")
        s2 = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        self.assertEqual(s2.from_text("đi khám ngày mốt lúc 9 giờ sáng")["draft"]["ai"]["status"], "off")
        self.assertIsNone(s2.from_text("họp 3h chiều mai")["draft"]["ai"])
