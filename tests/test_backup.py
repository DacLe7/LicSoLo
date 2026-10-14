import sys, os, json, threading, unittest, urllib.request
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer
from urllib.parse import quote
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.api import make_handler
from lichviet.store import fmt

NOW = datetime(2026, 10, 13, 10, 0)


def svc():
    return Service(":memory:", clock=lambda: NOW, llm=LLMClient(""))


class TestBackup(unittest.TestCase):
    def test_import_twice_adds_nothing_second_time(self):
        a = svc()
        a.create("Họp nhóm", NOW + timedelta(hours=2))
        a.create("Khám răng", NOW + timedelta(days=1))
        data = json.loads(json.dumps(a.export_all()))
        b = svc()
        self.assertEqual(b.import_all(data)["added"], 2)
        r2 = b.import_all(data)
        self.assertEqual(r2["added"], 0)
        self.assertEqual(r2["skipped"], 2)
        self.assertEqual(len(b.list_range(NOW - timedelta(days=1), NOW + timedelta(days=5))), 2)

    def test_bad_format_raises_value_error(self):
        b = svc()
        with self.assertRaises(ValueError):
            b.import_all({"format": "khac", "events": []})
        with self.assertRaises(ValueError):
            b.import_all([1, 2])
        with self.assertRaises(ValueError):
            b.import_all({"format": "lichviet-backup", "events": [{"title": "x", "start": "ngày mai"}]})
        self.assertEqual(b.list_range(NOW - timedelta(days=1), NOW + timedelta(days=5)), [])

    def test_fired_reminder_not_repeated_after_import(self):
        a = svc()
        ev_id = a.create("Uống thuốc", NOW - timedelta(minutes=30))
        due = a.due_reminders()
        self.assertEqual(len(due), 1)
        a.mark_fired(due[0]["event_id"], due[0]["key"])
        self.assertEqual(a.due_reminders(), [])
        data = json.loads(json.dumps(a.export_all()))
        b = svc()
        b.import_all(data)
        self.assertEqual(b.due_reminders(), [])

    def test_phrase_import_and_delete(self):
        b = svc()
        r = b.import_all({"format": "lichviet-backup", "events": [],
                          "phrases": [{"src": "hop nhom", "dst": "họp nhóm", "hits": 3}]})
        self.assertEqual(r["phrases"], 1)
        self.assertTrue(b.forget_phrase("hop nhom"))
        self.assertFalse(b.forget_phrase("hop nhom"))


class TestHttpV1(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.s))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_port

    def tearDown(self):
        self.srv.shutdown()

    def get(self, path):
        return json.loads(urllib.request.urlopen(self.base + path).read())

    def test_v1_same_as_plain(self):
        for p in ["/today", "/info", "/phrases", "/events?from=2026-10-13T00:00:00&to=2026-10-20T00:00:00"]:
            self.assertEqual(self.get("/v1" + p), self.get(p), p)

    def test_delete_phrase(self):
        self.s.import_all({"format": "lichviet-backup", "events": [],
                           "phrases": [{"src": "di cho", "dst": "đi chợ"}]})
        url = self.base + "/phrases/" + quote("di cho")
        d = urllib.request.Request(url, method="DELETE")
        self.assertTrue(json.loads(urllib.request.urlopen(d).read())["deleted"])
        d = urllib.request.Request(url, method="DELETE")
        self.assertFalse(json.loads(urllib.request.urlopen(d).read())["deleted"])
        self.assertEqual(self.get("/phrases"), [])


if __name__ == "__main__":
    unittest.main()
