"""Hồi quy cho các lỗi đã sửa sau đợt khảo sát (toàn vẹn dữ liệu, parser, API, lặp âm lịch hằng tháng)."""
import sys, os, json, threading, unittest, urllib.request, urllib.error
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.api import make_handler, Server, host_ok, origin_ok
from lichviet.parser import parse_vi

NOW = datetime(2026, 10, 19, 16, 0)   # Thứ Hai
def svc(clock=lambda: NOW):
    return Service(":memory:", clock=clock, llm=LLMClient(""))
def P(t):
    return parse_vi(t, NOW)


class TestParserFixes(unittest.TestCase):
    def test_period_with_date_is_kept(self):
        self.assertEqual(P("sáng mai họp").start, datetime(2026, 10, 20, 8, 0))
        self.assertEqual(P("tối mai gọi mẹ").start, datetime(2026, 10, 20, 19, 0))
        self.assertFalse(P("sáng mai họp").all_day)

    def test_kem_and_short_minutes(self):
        self.assertEqual(P("họp 3 giờ kém 15 chiều mai").start, datetime(2026, 10, 20, 14, 45))
        self.assertEqual(P("ba giờ kém mười lăm chiều mai họp").start, datetime(2026, 10, 20, 14, 45))
        self.assertEqual(P("họp 3h5 chiều mai").start, datetime(2026, 10, 20, 15, 5))

    def test_relative_days_keep_time(self):
        self.assertEqual(P("sau 3 ngày lúc 9h họp").start, datetime(2026, 10, 22, 9, 0))
        self.assertTrue(P("sau 3 ngày họp").all_day)

    def test_midnight_and_ngay_mot(self):
        self.assertEqual(P("họp 12h khuya").start, datetime(2026, 10, 20, 0, 0))
        self.assertEqual(P("họp 12h đêm nay").start, datetime(2026, 10, 20, 0, 0))
        self.assertEqual(P("khám ngày mốt 8h30 sáng").start, datetime(2026, 10, 21, 8, 30))


class TestLunarMonthly(unittest.TestCase):
    def test_ram_monthly(self):
        d = svc().from_text("cúng rằm mỗi tháng")["draft"]
        self.assertEqual((d["repeat"], d["lunar"], d["start"]), ("lunar_monthly", [15, None], "2026-10-24T00:00:00"))

    def test_expands_every_month(self):
        s = svc(); s.from_text("cúng rằm mỗi tháng", save=True)
        days = [e["occurrence"][:10] for e in s.list_range(datetime(2026, 10, 19), datetime(2027, 1, 1))]
        self.assertEqual(days, ["2026-10-24", "2026-11-23", "2026-12-23"])

    def test_two_days_not_silently_wrong(self):
        r = svc().from_text("ăn chay mùng 1 và rằm hằng tháng")
        self.assertEqual(r["status"], "need_info")
        self.assertTrue(any("nhiều ngày" in w for w in r["draft"]["warnings"]))


class TestIntegrity(unittest.TestCase):
    def test_past_warns_and_does_not_fire(self):
        s = svc(); r = s.from_text("hôm nay 8h sáng họp", save=True)
        self.assertTrue(any("đã qua" in w for w in r["draft"]["warnings"]))
        self.assertEqual(s.due_reminders(), [])

    def test_catch_up_after_downtime(self):
        clk = [datetime(2026, 10, 17, 7, 0)]; s = svc(lambda: clk[0])
        s.create("Họp", datetime(2026, 10, 17, 8, 0)); clk[0] = datetime(2026, 10, 19, 9, 0)
        self.assertEqual([d["title"] for d in s.due_reminders()], ["Họp"])

    def test_bad_import_rolls_back_everything(self):
        s = svc()
        bad = {"format": "lichviet-backup", "events": [{"id": 1, "title": "A", "start": "2026-11-01T09:00:00"},
                                                       {"id": 2, "title": "B", "start": "HỎNG"}]}
        with self.assertRaises(ValueError):
            s.import_all(bad)
        s.create("C", datetime(2026, 12, 1, 9, 0))   # một lần ghi khác không được "kéo theo" A
        self.assertEqual([r["title"] for r in s.con.execute("select title from events")], ["C"])

    def test_ui_ack_does_not_hide_from_notifier(self):
        clk = [datetime(2026, 10, 19, 7, 0)]; s = svc(lambda: clk[0])
        e = s.create("Uống thuốc", datetime(2026, 10, 19, 8, 0)); clk[0] = datetime(2026, 10, 19, 8, 5)
        d = s.due_reminders()[0]; s.ack(d["event_id"], d["key"])
        self.assertEqual(s.due_reminders("ui"), [])
        self.assertEqual(len(s.due_reminders()), 1)          # notifier vẫn phải gửi
        s.mark_fired(d["event_id"], d["key"])
        self.assertEqual(s.due_reminders(), [])


class TestApiGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svc = svc(); cls.srv = Server(("127.0.0.1", 0), make_handler(cls.svc))
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def call(self, m, p, body=None, h=None):
        r = urllib.request.Request(self.base + p, data=body, method=m, headers=h or {})
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_hosts_and_origins(self):
        self.assertTrue(host_ok("127.0.0.1:18763") and host_ok("app:8080") and host_ok("[::1]:8080"))
        self.assertFalse(host_ok("evil.example:18763"))
        self.assertTrue(origin_ok("", "127.0.0.1:1") and origin_ok("http://127.0.0.1:1", "127.0.0.1:1"))
        self.assertFalse(origin_ok("http://evil.example", "127.0.0.1:1"))

    def test_cross_origin_write_rejected(self):
        c, _ = self.call("POST", "/parse", json.dumps({"text": "họp 5/11 9h", "save": True}).encode(), {"Origin": "http://evil.example"})
        self.assertEqual(c, 403)
        self.assertEqual(self.svc.con.execute("select count(*) from events").fetchone()[0], 0)

    def test_errors_are_json_400(self):
        self.assertEqual(self.call("POST", "/events", json.dumps({"title": "x", "start": "2026-11-01T09:00:00", "bogus": 1}).encode())[0], 400)
        self.assertEqual(self.call("POST", "/events", json.dumps({"title": "x"}).encode())[0], 400)
        self.assertEqual(self.call("POST", "/import", json.dumps({"format": "lichviet-backup", "events": [1]}).encode())[0], 400)

    def test_contract_fields(self):
        c, info = self.call("GET", "/v1/info")
        self.assertEqual(info["user_id"], "default"); self.assertTrue(info["now_iso"].endswith("+07:00"))


if __name__ == "__main__":
    unittest.main()
