"""Đường tạo việc bằng các trường rõ ràng (POST /events), dùng cho form "Sửa" của thẻ "Trợ lý hiểu là"."""
import sys, os, json, threading, unittest, urllib.request, urllib.error
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.api import make_handler, Server

NOW = datetime(2026, 10, 19, 16, 0)


class TestManualCreate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svc = Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))
        cls.srv = Server(("127.0.0.1", 0), make_handler(cls.svc))
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def post(self, body):
        r = urllib.request.Request(self.base + "/events", data=json.dumps(body).encode(), method="POST")
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            finally:
                e.close()

    def count(self):
        return self.svc.con.execute("select count(*) from events").fetchone()[0]

    def test_valid_fields_saved(self):
        c, ev = self.post({"title": "Họp nhóm", "start": "2026-11-02T14:30:00", "all_day": False,
                           "repeat": "weekly", "remind_before_min": 10, "duration_min": None, "lunar": None})
        self.assertEqual(c, 200)
        self.assertEqual(ev["title"], "Họp nhóm")
        self.assertEqual(ev["start"], "2026-11-02T14:30:00")
        self.assertEqual(ev["repeat"], "weekly")
        self.assertEqual(ev["remind_before_min"], 10)
        self.assertFalse(ev.get("duplicate"))

    def test_all_day_at_midnight(self):
        c, ev = self.post({"title": "Đi du lịch", "start": "2026-11-03T00:00:00", "all_day": True})
        self.assertEqual(c, 200)
        self.assertEqual(ev["all_day"], 1)

    def test_empty_title_rejected(self):
        for t in ("", "   "):
            before = self.count()
            c, body = self.post({"title": t, "start": "2026-11-04T09:00:00"})
            self.assertEqual(c, 400)
            self.assertIn("error", body)
            self.assertEqual(self.count(), before)

    def test_bad_datetime_rejected(self):
        for start in ("2026-02-30T09:00:00", "2026-11-04T25:00:00", "ngày mai"):
            before = self.count()
            c, body = self.post({"title": "Việc thử", "start": start})
            self.assertEqual(c, 400, start)
            self.assertIn("error", body)
            self.assertEqual(self.count(), before)

    def test_bad_repeat_rejected(self):
        c, body = self.post({"title": "Việc thử", "start": "2026-11-05T09:00:00", "repeat": "yearly"})
        self.assertEqual(c, 400)
        self.assertIn("error", body)

    def test_lunar_repeat_needs_lunar_date(self):
        c, _ = self.post({"title": "Giỗ", "start": "2026-11-06T09:00:00", "repeat": "lunar_yearly"})
        self.assertEqual(c, 400)
        c, ev = self.post({"title": "Giỗ", "start": "2026-11-06T09:00:00", "repeat": "lunar_yearly", "lunar": [15, 8]})
        self.assertEqual(c, 200)
        self.assertEqual(ev["lunar_day"], 15)
        self.assertEqual(ev["lunar_month"], 8)

    def test_duplicate_returns_existing(self):
        body = {"title": "Uống thuốc", "start": "2026-11-07T19:00:00", "repeat": "daily"}
        c1, first = self.post(body)
        before = self.count()
        c2, second = self.post(body)
        self.assertEqual((c1, c2), (200, 200))
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(self.count(), before)


if __name__ == "__main__":
    unittest.main()
