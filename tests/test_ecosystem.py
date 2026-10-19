"""Hợp đồng cho hệ sinh thái: khóa API, payload nhắc có ref, đồng bộ tăng dần, thiết bị, .ics."""
import sys, os, json, threading, unittest, urllib.request, urllib.error
from datetime import datetime, timedelta
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.api import make_handler, Server
from lichviet.service import CursorTooOld

NOW = datetime(2026, 10, 19, 9, 0)
KEY = "k" * 20


def svc(clock=lambda: NOW):
    return Service(":memory:", clock=clock, llm=LLMClient(""))


class Srv:
    """Máy chủ thử với biến môi trường tùy ý (khóa được đọc lúc tạo handler)."""
    def __init__(self, service, env):
        with mock.patch.dict(os.environ, env):
            self.srv = Server(("127.0.0.1", 0), make_handler(service))
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def call(self, method, path, body=None, headers=None):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                   method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                raw = x.read()
                return x.status, (json.loads(raw) if "json" in x.headers.get("Content-Type", "") else raw.decode()), x.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read()), e.headers

    def close(self):
        self.srv.shutdown(); self.srv.server_close()


class TestAuth(unittest.TestCase):
    def test_short_key_refused(self):
        with self.assertRaises(ValueError):
            Srv(svc(), {"LICHVIET_API_KEY": "ngan"})

    def test_new_endpoints_fail_closed_without_key(self):
        s = Srv(svc(), {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        for p in ("/v1/events/changes", "/v1/reminders/upcoming", "/v1/devices", "/v1/calendar.ics"):
            self.assertEqual(s.call("GET", p)[0], 503, p)
        s.close()

    def test_key_required_when_set(self):
        s = Srv(svc(), {"LICHVIET_API_KEY": KEY})
        self.assertEqual(s.call("GET", "/v1/events/changes")[0], 401)
        self.assertEqual(s.call("GET", "/v1/events/changes", headers={"X-Lacviet-Key": "sai" * 8})[0], 401)
        self.assertEqual(s.call("GET", "/v1/events/changes", headers={"X-Lacviet-Key": KEY})[0], 200)
        self.assertEqual(s.call("GET", "/v1/events/changes", headers={"Authorization": "Bearer " + KEY})[0], 200)
        self.assertEqual(s.call("GET", "/v1/reminders/due")[0], 401)                      # endpoint cũ cũng được khóa
        self.assertEqual(s.call("GET", "/v1/reminders/due?channel=ui")[0], 200)           # banner giao diện thì không
        self.assertEqual(s.call("POST", "/v1/reminders/fired", {"event_id": 1, "occurrence": "x"})[0], 401)
        s.close()

    def test_legacy_endpoints_open_without_key(self):
        s = Srv(svc(), {"LICHVIET_API_KEY": ""})
        self.assertEqual(s.call("GET", "/v1/reminders/due")[0], 200)
        s.close()


class TestReminderPayload(unittest.TestCase):
    def test_ref_and_fields_stable(self):
        clk = [NOW - timedelta(days=1)]; a = svc(lambda: clk[0])
        ev = a.create("Họp", datetime(2026, 10, 19, 8, 0), notes="mang laptop", remind_before_min=10)
        clk[0] = NOW
        d = a.due_reminders()[0]
        self.assertEqual(d["ref"], "lv-%d-202610190800" % ev["id"]); self.assertEqual(d["event_ref"], "lv-%d" % ev["id"])
        self.assertEqual(d["fire_at"], "2026-10-19T07:50:00"); self.assertEqual(d["notes"], "mang laptop")
        self.assertEqual(d["ref"], a.due_reminders()[0]["ref"])

    def test_upcoming_gives_every_stage_with_unique_refs(self):
        a = svc(); a.create("Giỗ ông", datetime(2026, 10, 24, 0, 0), all_day=True, repeat="lunar_yearly", lunar=(15, 9))
        a.create("Họp", datetime(2026, 10, 20, 9, 0), remind_before_min=15)
        up = a.upcoming_reminders(14)
        # mốc 7 ngày của giỗ (17/10) đã qua nên không có; còn: họp 20/10 08:45, giỗ nhắc trước 1 ngày, giỗ đúng ngày
        self.assertEqual([(u["title"], u["kind"]) for u in up],
                         [("Họp", "on_time"), ("Giỗ ông", "prepare_1d"), ("Giỗ ông", "on_time")])
        refs = [u["ref"] for u in up]; self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(up[0]["title"], "Họp"); self.assertEqual(up[0]["fire_at"], "2026-10-20T08:45:00")
        self.assertEqual(sorted(u["fire_at"] for u in up), [u["fire_at"] for u in up])   # đã sắp theo giờ nhắc


class TestDevices(unittest.TestCase):
    def test_register_validate_and_limit(self):
        a = svc()
        self.assertEqual(a.register_device("ip-1", "ios", " iPhone Hậu ")["label"], "iPhone Hậu")
        with self.assertRaises(ValueError): a.register_device("x y", "ios")
        with self.assertRaises(ValueError): a.register_device("a", "windows")
        for i in range(19): a.register_device("d%d" % i, "android")
        with self.assertRaises(ValueError): a.register_device("tran", "other")
        self.assertTrue(a.remove_device("ip-1"))

    def test_delivered_is_per_device_and_independent_of_fired(self):
        clk = [NOW - timedelta(days=1)]; a = svc(lambda: clk[0])
        a.register_device("p1", "ios"); a.register_device("p2", "android")
        a.create("Họp", datetime(2026, 10, 19, 8, 0)); clk[0] = NOW
        d = a.due_reminders()[0]
        a.mark_delivered("p1", d["event_id"], d["key"])
        self.assertEqual(a.due_reminders(device_id="p1"), [])
        self.assertEqual(len(a.due_reminders(device_id="p2")), 1)
        self.assertEqual(len(a.due_reminders()), 1)          # notifier chưa gửi
        with self.assertRaises(ValueError): a.due_reminders(device_id="la")
        a.update(d["event_id"], title="Họp mới")             # sửa việc: nhắc lại được
        self.assertEqual(len(a.due_reminders(device_id="p1")), 1)


class TestChanges(unittest.TestCase):
    def test_full_then_incremental(self):
        a = svc(); e1 = a.create("A", datetime(2026, 11, 1, 9, 0)); e2 = a.create("B", datetime(2026, 11, 2, 9, 0))
        full = a.changes_since(0)
        self.assertEqual([c["op"] for c in full["changes"]], ["upsert", "upsert"])
        cur = int(full["cursor"])
        self.assertEqual(a.changes_since(cur)["changes"], [])
        a.update(e1["id"], title="A2"); a.update(e1["id"], title="A3"); a.delete(e2["id"])
        inc = a.changes_since(cur)
        self.assertEqual([(c["op"], c.get("event", {}).get("title") or c.get("event_id")) for c in inc["changes"]],
                         [("upsert", "A3"), ("delete", e2["id"])])      # mỗi việc một lần, trạng thái mới nhất

    def test_paging(self):
        a = svc()
        for i in range(5): a.create("V%d" % i, datetime(2026, 11, 1 + i, 9, 0))
        seen, cur = [], 0
        while True:
            r = a.changes_since(cur, limit=2); seen += [c["event"]["title"] for c in r["changes"]]; cur = int(r["cursor"])
            if not r["has_more"]: break
        self.assertEqual(seen, ["V0", "V1", "V2", "V3", "V4"])

    def test_import_and_upgrade_are_visible(self):
        a = svc(); a.create("A", datetime(2026, 11, 1, 9, 0)); data = a.export_all()
        b = svc(); b.import_all(data)
        self.assertEqual(len(b.changes_since(0)["changes"]), 1)

    def test_old_cursor_after_tombstone_purge(self):
        clk = [NOW]; a = svc(lambda: clk[0])
        e = a.create("A", datetime(2026, 11, 1, 9, 0)); cur = int(a.changes_since(0)["cursor"])
        a.delete(e["id"]); clk[0] = NOW + timedelta(days=100)
        a.create("B", datetime(2026, 12, 1, 9, 0))
        with self.assertRaises(CursorTooOld): a.changes_since(cur)
        self.assertEqual([c["event"]["title"] for c in a.changes_since(0)["changes"]], ["B"])   # đồng bộ lại vẫn được

    def test_http_410_and_bad_cursor(self):
        s = Srv(svc(), {"LICHVIET_API_KEY": KEY}); h = {"X-Lacviet-Key": KEY}
        self.assertEqual(s.call("GET", "/v1/events/changes?since=-1", headers=h)[0], 400)
        self.assertEqual(s.call("GET", "/v1/events/changes?since=abc", headers=h)[0], 400)
        c, body, _ = s.call("GET", "/v1/events/changes", headers=h)
        self.assertEqual((c, body["user_id"], body["has_more"]), (200, "default", False)); s.close()


class TestIcs(unittest.TestCase):
    def _ics(self, a, env=None, path="/v1/calendar.ics"):
        s = Srv(a, {"LICHVIET_API_KEY": KEY, **(env or {})})
        try:
            return s.call("GET", path, headers={"X-Lacviet-Key": KEY})
        finally:
            s.close()

    def test_structure_timezone_alarms_and_escape(self):
        a = svc()
        a.create("Họp, nhóm; A", datetime(2026, 10, 20, 9, 0), duration_min=60, notes="dòng 1\ndòng 2", remind_before_min=10)
        a.create("Giỗ ông", datetime(2026, 10, 24, 0, 0), all_day=True, repeat="lunar_yearly", lunar=(15, 9))
        code, text, hdr = self._ics(a)
        self.assertEqual(code, 200); self.assertTrue(hdr["Content-Type"].startswith("text/calendar"))
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("\n", text.replace("\r\n", ""))
        flat = text.replace("\r\n ", "")
        self.assertIn("DTSTART:20261020T020000Z", flat)               # 09:00 +07:00 = 02:00Z
        self.assertIn("DTEND:20261020T030000Z", flat)
        self.assertIn("SUMMARY:Họp\\, nhóm\\; A", flat)
        self.assertIn("DESCRIPTION:dòng 1\\ndòng 2", flat)
        self.assertIn("DTSTART;VALUE=DATE:20261024", flat)
        self.assertIn("Âm lịch: 15/9 hằng năm", flat)
        # họp 1; giỗ 24/10/2026 còn 2 (mốc 7 ngày = 17/10 đã quá 1 ngày nên bỏ); giỗ năm 2027 trong 365 ngày có đủ 3
        self.assertEqual(flat.count("BEGIN:VALARM"), 6)
        self.assertIn("TRIGGER;VALUE=DATE-TIME:20261020T015000Z", flat)   # 08:50 +07:00 (nhắc trước 10 phút)
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_range_validation_and_ics_key(self):
        a = svc(); a.create("A", datetime(2026, 11, 1, 9, 0))
        s = Srv(a, {"LICHVIET_API_KEY": KEY, "LICHVIET_ICS_KEY": "i" * 20})
        self.assertEqual(s.call("GET", "/v1/calendar.ics?from=2026-12-01&to=2026-11-01", headers={"X-Lacviet-Key": KEY})[0], 400)
        self.assertEqual(s.call("GET", "/v1/calendar.ics?key=" + "i" * 20)[0], 200)      # đăng ký lịch qua URL
        self.assertEqual(s.call("GET", "/v1/calendar.ics?key=" + "x" * 20)[0], 401)
        self.assertEqual(s.call("GET", "/v1/events/changes?key=" + "i" * 20)[0], 401)    # khóa ics không mở endpoint khác
        s.close()


if __name__ == "__main__":
    unittest.main()
