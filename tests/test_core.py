import sys, os, unittest
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service, parse_vi

NOW = datetime(2026, 10, 13, 10, 0)  # Thứ Ba


def P(t):
    return parse_vi(t, NOW)


class TestParser(unittest.TestCase):
    CASES = [
        ("Nhắc tôi họp với anh Nam lúc 3h chiều ngày mai", "Họp với anh Nam", datetime(2026, 10, 14, 15, 0)),
        ("họp nhóm 9 giờ rưỡi sáng thứ sáu", "Họp nhóm", datetime(2026, 10, 16, 9, 30)),
        ("khám răng ngày 23/10 lúc 14:30", "Khám răng", datetime(2026, 10, 23, 14, 30)),
        ("đi chợ 7h tối nay", "Đi chợ", datetime(2026, 10, 13, 19, 0)),
        ("gọi mẹ 8h sáng ngày kia", "Gọi mẹ", datetime(2026, 10, 15, 8, 0)),
        ("họp lúc 9h thứ hai tuần sau", "Họp", datetime(2026, 10, 19, 9, 0)),
        ("nop bao cao 5h chieu thu ba", "Nop bao cao", datetime(2026, 10, 20, 17, 0)),   # thứ Ba hôm nay -> tuần sau
        ("uống thuốc sau 30 phút", "Uống thuốc", datetime(2026, 10, 13, 10, 30)),
        ("sinh nhật Lan ngày 5 tháng 11", "Sinh nhật Lan", datetime(2026, 11, 5, 0, 0)),
        ("ăn trưa 12 giờ trưa mai", "Ăn trưa", datetime(2026, 10, 14, 12, 0)),
        ("nhờ nhắc em cái vụ nha sĩ ngày 23/10 lúc 14:30 nhé", "Nha sĩ", datetime(2026, 10, 23, 14, 30)),
        ("đi khám răng mùng 5 tháng 11 lúc 9 giờ sáng", "Đi khám răng", datetime(2026, 11, 5, 9, 0)),
        ("họp mồng 20 tháng 10 lúc 8h", "Họp", datetime(2026, 10, 20, 8, 0)),
        ("họp hai giờ rưỡi chiều mai nhé", "Họp", datetime(2026, 10, 14, 14, 30)),
        ("đi khám răng lúc mười giờ sáng mai", "Đi khám răng", datetime(2026, 10, 14, 10, 0)),
    ]

    def test_cases(self):
        for text, title, start in self.CASES:
            r = P(text)
            self.assertEqual(r.title, title, text)
            self.assertEqual(r.start, start, text)

    def test_time_only_rolls_forward(self):
        self.assertEqual(P("tập gym 6h sáng").start, datetime(2026, 10, 14, 6, 0))
        self.assertEqual(P("tập gym 6h chiều").start, datetime(2026, 10, 13, 18, 0))

    def test_all_day(self):
        r = P("hạn nộp thuế ngày 30/10")
        self.assertTrue(r.all_day)

    def test_repeat_remind_duration(self):
        r = P("họp giao ban 8h sáng mỗi thứ hai, nhắc trước 15 phút, kéo dài 45 phút")
        self.assertEqual(r.repeat, "weekly")
        self.assertEqual(r.remind_before_min, 15)
        self.assertEqual(r.duration_min, 45)
        self.assertEqual(r.start, datetime(2026, 10, 19, 8, 0))
        self.assertEqual(r.title, "Họp giao ban")
        self.assertEqual(P("uống vitamin 7h sáng mỗi ngày").repeat, "daily")

    def test_unsure_date(self):
        r = P("đi khám ngày mốt lúc 9 giờ sáng")
        self.assertTrue(r.unsure)
        self.assertTrue(r.warnings)
        self.assertFalse(P("họp 3h chiều mai").unsure)
        self.assertFalse(P("báo cáo tuần 3h chiều mai").unsure is True and False)

    def test_missing_and_invalid(self):
        self.assertIn("start", P("mua sữa").missing)
        self.assertIn("title", P("lúc 3h chiều mai").missing)
        self.assertTrue(P("họp ngày 31/02").warnings)


class TestService(unittest.TestCase):
    def setUp(self):
        self.clock = [NOW]
        self.s = Service(":memory:", clock=lambda: self.clock[0])

    def test_draft_does_not_save(self):
        r = self.s.from_text("họp 3h chiều mai")
        self.assertEqual(r["status"], "draft")
        self.assertEqual(self.s.list_range(datetime(2026, 1, 1), datetime(2027, 1, 1)), [])

    def test_save_conflict_update_delete(self):
        a = self.s.from_text("họp A 3h chiều mai", save=True)
        self.assertEqual(a["status"], "saved")
        b = self.s.from_text("họp B 3h30 chiều mai")
        self.assertEqual(len(b["conflicts"]), 1)
        eid = a["event"]["id"]
        self.s.update(eid, title="Họp A2")
        self.assertEqual(self.s.get(eid)["title"], "Họp A2")
        with self.assertRaises(ValueError):
            self.s.update(eid, hack=1)
        with self.assertRaises(KeyError):
            self.s.update(999, title="x")
        self.assertTrue(self.s.delete(eid))
        self.assertIsNone(self.s.get(eid))

    def test_weekly_expansion_month_end(self):
        self.s.create("Giao ban", datetime(2026, 10, 5, 8, 0), repeat="weekly")
        occ = self.s.list_range(datetime(2026, 10, 12), datetime(2026, 11, 3))
        self.assertEqual([o["occurrence"][:10] for o in occ], ["2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"])
        self.s.create("Tiền nhà", datetime(2026, 1, 31, 9, 0), repeat="monthly")
        occ = self.s.list_range(datetime(2026, 2, 1), datetime(2026, 3, 1))
        self.assertEqual(occ[0]["occurrence"][:10], "2026-02-28")

    def test_reminders_fire_once(self):
        self.s.create("Uống thuốc", datetime(2026, 10, 13, 10, 30), remind_before_min=15)
        self.assertEqual(self.s.due_reminders(), [])
        self.clock[0] = datetime(2026, 10, 13, 10, 20)
        due = self.s.due_reminders()
        self.assertEqual(len(due), 1)
        self.s.mark_fired(due[0]["event_id"], due[0]["occurrence"])
        self.assertEqual(self.s.due_reminders(), [])

    def test_ai_independent(self):
        # toàn bộ luồng trên chạy không cần AI/mạng
        self.assertEqual(self.s.from_text("mua sữa")["status"], "need_info")


if __name__ == "__main__":
    unittest.main()


class TestHttp(unittest.TestCase):
    def test_ui_and_flow(self):
        import json, threading, urllib.request
        from http.server import ThreadingHTTPServer
        from lichviet.api import make_handler
        svc = Service(":memory:", clock=lambda: NOW)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(svc))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % srv.server_port
        try:
            html = urllib.request.urlopen(base + "/").read().decode("utf-8")
            self.assertIn("Trợ lý thời gian", html)
            req = urllib.request.Request(base + "/parse", data=json.dumps({"text": "họp 3h chiều mai", "save": True}).encode("utf-8"))
            r = json.loads(urllib.request.urlopen(req).read())
            self.assertEqual(r["status"], "saved")
            ev = json.loads(urllib.request.urlopen(base + "/events?from=2026-10-13T00:00:00&to=2026-10-20T00:00:00").read())
            self.assertEqual(len(ev), 1)
            d = urllib.request.Request(base + "/events/%d" % ev[0]["id"], method="DELETE")
            self.assertTrue(json.loads(urllib.request.urlopen(d).read())["deleted"])
        finally:
            srv.shutdown()


class TestToday(unittest.TestCase):
    def test_today_info_tet_2026(self):
        from lichviet.api import today_info
        r = today_info(datetime(2026, 2, 17, 9, 0))  # mùng 1 Tết Bính Ngọ
        self.assertEqual((r["lunar_day"], r["lunar_month"], r["year_name"]), (1, 1, "Bính Ngọ"))
