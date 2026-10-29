"""PATCH /events, lặp hằng năm dương lịch, giảm nhắc trùng (skip_acked/skip_delivered), ngày quá khứ, /events/check."""
import sys, os, json, threading, unittest, urllib.request, urllib.error
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import Service
from lichviet.ai import LLMClient
from lichviet.api import make_handler, Server
from lichviet.parser import parse_vi
from lichviet.lunar import solar_to_lunar

PNOW = datetime(2026, 10, 20, 9, 30)   # Thứ Ba, giờ giả lập cho parser


def at(text):
    r = parse_vi(text, PNOW)
    return r.start, r.all_day, r.repeat, r.title, r.warnings


class Box:
    """Service + máy chủ HTTP thử, đồng hồ chỉnh tay được."""
    def __init__(self, now=datetime(2026, 10, 19, 9, 0)):
        self.now = now
        self.svc = Service(":memory:", clock=lambda: self.now, llm=LLMClient(""))
        self.srv = Server(("127.0.0.1", 0), make_handler(self.svc))
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def call(self, method, path, body=None):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                   method=method)
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                raw = x.read()
                return x.status, (json.loads(raw) if "json" in x.headers.get("Content-Type", "") else raw.decode())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            finally:
                e.close()

    def add(self, title, start, **kw):
        return self.svc.create(title, datetime.fromisoformat(start), **kw)

    def close(self):
        self.srv.shutdown(); self.srv.server_close()


class Base(unittest.TestCase):
    def setUp(self):
        self.b = Box()
        self.addCleanup(self.b.close)


# ------------------------------------------------------------------ 1) PATCH /events/<id>
class TestPatch(Base):
    def test_edit_title_time_repeat(self):
        ev = self.b.add("Họp nhóm", "2026-11-02T14:30:00")
        c, out = self.b.call("PATCH", "/v1/events/%d" % ev["id"],
                             {"title": "  Họp tổ  ", "start": "2026-11-03T15:00:00", "repeat": "weekly"})
        self.assertEqual(c, 200)
        self.assertEqual((out["title"], out["start"], out["repeat"]), ("Họp tổ", "2026-11-03T15:00:00", "weekly"))
        self.assertEqual(out["start_iso"], "2026-11-03T15:00:00+07:00")
        self.assertEqual(self.b.svc.get(ev["id"])["repeat"], "weekly")

    def test_partial_keeps_other_fields(self):
        ev = self.b.add("Uống thuốc", "2026-11-02T07:00:00", remind_before_min=5, notes="sau ăn")
        c, out = self.b.call("PATCH", "/events/%d" % ev["id"], {"duration_min": 15})
        self.assertEqual(c, 200)
        self.assertEqual((out["title"], out["remind_before_min"], out["notes"], out["duration_min"]),
                         ("Uống thuốc", 5, "sau ăn", 15))

    def test_missing_event_404(self):
        self.assertEqual(self.b.call("PATCH", "/v1/events/999", {"title": "x"})[0], 404)
        self.assertEqual(self.b.call("PATCH", "/v1/events/999", {})[0], 404)

    def test_bad_input_400(self):
        ev = self.b.add("A", "2026-11-02T14:30:00")
        p = "/v1/events/%d" % ev["id"]
        for body in ({"colour": "red"}, {"start": "ngày mai"}, {"repeat": "biweekly"}, {"title": "  "},
                     {"lunar": "abc"}, {"duration_min": -5}, {"duration_min": "60"}, {"repeat": "lunar_yearly"}):
            c, out = self.b.call("PATCH", p, body)
            self.assertEqual(c, 400, body)
            self.assertIn("error", out)
        self.assertEqual(self.b.call("PATCH", "/v1/events/abc", {"title": "x"})[0], 400)
        self.assertEqual(self.b.svc.get(ev["id"])["title"], "A")   # không sửa nửa chừng

    def test_unknown_field_message(self):
        ev = self.b.add("A", "2026-11-02T14:30:00")
        c, out = self.b.call("PATCH", "/v1/events/%d" % ev["id"], {"title": "B", "id": 5})
        self.assertEqual(c, 400)
        self.assertIn("id", out["error"])
        self.assertEqual(self.b.svc.get(ev["id"])["title"], "A")

    def test_empty_body_returns_event(self):
        ev = self.b.add("A", "2026-11-02T14:30:00")
        c, out = self.b.call("PATCH", "/v1/events/%d" % ev["id"], {})
        self.assertEqual((c, out["title"]), (200, "A"))

    def test_shows_in_changes_as_upsert(self):
        ev = self.b.add("A", "2026-11-02T14:30:00")
        cur = self.b.call("GET", "/v1/events/changes")[1]["cursor"]
        self.b.call("PATCH", "/v1/events/%d" % ev["id"], {"title": "B"})
        res = self.b.call("GET", "/v1/events/changes?since=" + cur)[1]
        self.assertEqual([(c["op"], c["event"]["title"]) for c in res["changes"]], [("upsert", "B")])

    def test_clears_reminder_state(self):
        ev = self.b.add("Họp", "2026-10-19T08:00:00")
        self.b.svc.register_device("d1", "android")
        self.b.svc.mark_fired(ev["id"], "2026-10-19T08:00:00")
        self.b.svc.ack(ev["id"], "2026-10-19T08:00:00")
        self.b.svc.mark_delivered("d1", ev["id"], "2026-10-19T08:00:00")
        con = self.b.svc.con
        for t in ("fired", "acked", "delivered"):
            self.assertEqual(con.execute("select count(*) from %s" % t).fetchone()[0], 1)
        self.b.call("PATCH", "/v1/events/%d" % ev["id"], {"title": "Họp lại"})
        for t in ("fired", "acked", "delivered"):
            self.assertEqual(con.execute("select count(*) from %s" % t).fetchone()[0], 0, t)

    def test_duplicate_rejected(self):
        a = self.b.add("A", "2026-11-02T14:30:00")
        self.b.add("B", "2026-11-02T14:30:00")
        c, out = self.b.call("PATCH", "/v1/events/%d" % a["id"], {"title": "b"})
        self.assertEqual(c, 400)
        self.assertIn("trùng", out["error"])
        self.assertEqual(self.b.call("PATCH", "/v1/events/%d" % a["id"], {"title": "A"})[0], 200)   # trùng chính nó thì được

    def test_lunar_edit_and_repeat_switch(self):
        g = self.b.add("Giỗ", "2026-11-06T00:00:00", all_day=True, repeat="lunar_yearly", lunar=(15, 9))
        c, out = self.b.call("PATCH", "/v1/events/%d" % g["id"], {"lunar": [16, 9]})
        self.assertEqual((c, out["lunar_day"], out["lunar_month"]), (200, 16, 9))
        c, out = self.b.call("PATCH", "/v1/events/%d" % g["id"], {"repeat": "yearly"})   # sang dương lịch: bỏ ngày âm
        self.assertEqual((c, out["repeat"], out["lunar_day"], out["lunar_month"]), (200, "yearly", None, None))
        c, out = self.b.call("PATCH", "/v1/events/%d" % g["id"], {"repeat": "lunar_yearly", "lunar": [1, 2]})
        self.assertEqual((c, out["lunar_day"]), (200, 1))


# ------------------------------------------------------------------ 2) lặp hằng năm
class TestYearlyParser(unittest.TestCase):
    def test_birthday(self):
        self.assertEqual(at("sinh nhật mẹ 5/3"), (datetime(2027, 3, 5), True, "yearly", "Sinh nhật mẹ", []))

    def test_anniversary_with_yearly_word(self):
        s, allday, rep, title, _ = at("kỷ niệm cưới 20/10 hằng năm")
        self.assertEqual((s, allday, rep, title), (datetime(2026, 10, 20), True, "yearly", "Kỷ niệm cưới"))

    def test_word_forms(self):
        for t in ("nộp thuế 31/3 hàng năm", "nộp thuế ngày 31 tháng 3 mỗi năm", "nop thue 31/3 hang nam"):
            s, _, rep, title, _ = at(t)
            self.assertEqual((s, rep), (datetime(2027, 3, 31), "yearly"), t)
            self.assertTrue(title.lower().startswith("nộp thuế") or title.lower().startswith("nop thue"), title)

    def test_with_time(self):
        s, allday, rep, _, _ = at("sinh nhật bố 7/11 8h sáng")
        self.assertEqual((s, allday, rep), (datetime(2026, 11, 7, 8, 0), False, "yearly"))

    def test_lunar_wins(self):
        for t in ("sinh nhật mẹ 5/3 âm lịch", "kỷ niệm 15/8 âm lịch hằng năm", "sinh nhật bà 5/3 âm hằng năm"):
            r = parse_vi(t, PNOW)
            self.assertEqual(r.repeat, "lunar_yearly", t)
            self.assertIsNotNone(r.lunar, t)
        r = parse_vi("giỗ ông 15/8 hằng năm", PNOW)
        self.assertEqual((r.repeat, r.lunar), ("lunar_yearly", (15, 8)))

    def test_plain_dates_not_yearly(self):
        for t in ("họp 5/3", "đi khám 20/10 lúc 9h", "nộp báo cáo hằng năm"):
            self.assertIsNone(at(t)[2], t)
        self.assertTrue(any("hằng năm" in w for w in at("nộp báo cáo hằng năm")[4]))

    def test_other_repeat_wins(self):
        self.assertEqual(at("sinh nhật 5/3 mỗi tháng")[2], "monthly")


class TestYearlyService(Base):
    def occ(self, ev_id, lo, hi):
        return [e["occurrence"] for e in self.b.svc.list_range(datetime.fromisoformat(lo), datetime.fromisoformat(hi))
                if e["id"] == ev_id]

    def test_each_year_same_day_and_time(self):
        ev = self.b.add("Sinh nhật mẹ", "2026-03-05T08:30:00", repeat="yearly")
        self.assertEqual(self.occ(ev["id"], "2026-01-01T00:00:00", "2029-01-01T00:00:00"),
                         ["2026-03-05T08:30:00", "2027-03-05T08:30:00", "2028-03-05T08:30:00"])
        self.assertEqual(self.occ(ev["id"], "2025-01-01T00:00:00", "2026-03-05T08:30:00"), [])   # không lùi trước start

    def test_feb_29(self):
        ev = self.b.add("Sinh nhật bé", "2024-02-29T00:00:00", all_day=True, repeat="yearly")
        got = self.occ(ev["id"], "2024-01-01T00:00:00", "2029-01-01T00:00:00")
        self.assertEqual([g[:10] for g in got], ["2024-02-29", "2025-02-28", "2026-02-28", "2027-02-28", "2028-02-29"])

    def test_across_leap_year_window(self):
        ev = self.b.add("Kỷ niệm", "2027-02-28T09:00:00", repeat="yearly")
        self.assertEqual(self.occ(ev["id"], "2028-02-01T00:00:00", "2028-03-01T00:00:00"), ["2028-02-28T09:00:00"])

    def test_far_window(self):
        ev = self.b.add("Sinh nhật", "2026-03-05T00:00:00", all_day=True, repeat="yearly")
        self.assertEqual(self.occ(ev["id"], "2031-03-05T00:00:00", "2031-03-06T00:00:00"), ["2031-03-05T00:00:00"])

    def test_due_catches_up_like_one_off(self):
        self.b.now = datetime(2026, 3, 4, 12, 0)
        ev = self.b.add("Sinh nhật mẹ", "2026-03-05T00:00:00", all_day=True, repeat="yearly")
        self.b.now = datetime(2027, 3, 5, 8, 0)
        d = self.b.svc.due_reminders()
        self.assertEqual([(x["event_id"], x["kind"], x["occurrence"]) for x in d],
                         [(ev["id"], "on_time", "2027-03-05T00:00:00")])
        self.b.now = datetime(2027, 3, 11, 20, 0)    # trong 7 ngày bù (tính từ 00:00 ngày diễn ra)
        self.assertEqual(len(self.b.svc.due_reminders()), 1)
        self.b.now = datetime(2027, 3, 13, 8, 0)     # quá 7 ngày
        self.assertEqual(self.b.svc.due_reminders(), [])

    def test_only_on_time_stage(self):
        self.b.add("Sinh nhật", "2026-10-25T09:00:00", repeat="yearly")
        up = self.b.svc.upcoming_reminders(30)
        self.assertEqual([u["kind"] for u in up], ["on_time"])
        self.assertEqual(up[0]["repeat"], "yearly")

    def test_create_validates_and_dedups(self):
        a = self.b.add("SN", "2026-03-05T00:00:00", repeat="yearly", all_day=True)
        self.assertTrue(self.b.add("sn", "2026-03-05T00:00:00", repeat="yearly", all_day=True).get("duplicate"))
        c, out = self.b.call("POST", "/v1/events", {"title": "X", "start": "2026-03-05T09:00:00", "repeat": "yearly"})
        self.assertEqual((c, out["repeat"]), (200, "yearly"))
        self.assertTrue(a["id"])

    def test_backup_roundtrip(self):
        self.b.add("Sinh nhật mẹ", "2026-03-05T00:00:00", all_day=True, repeat="yearly")
        dump = self.b.svc.export_all()
        other = Box()
        self.addCleanup(other.close)
        res = other.svc.import_all(dump)
        self.assertEqual((res["added"], res["skipped"]), (1, 0))
        self.assertEqual(other.svc.con.execute("select repeat from events").fetchone()[0], "yearly")
        self.assertEqual(other.svc.import_all(dump)["added"], 0)

    def test_ics_one_vevent_per_occurrence(self):
        self.b.add("Sinh nhật mẹ", "2026-12-05T00:00:00", all_day=True, repeat="yearly")
        c, body = self.b.call("GET", "/v1/calendar.ics?from=2026-11-01T00:00:00&to=2028-12-31T00:00:00")
        self.assertEqual(c, 200)
        self.assertEqual(body.count("BEGIN:VEVENT"), 3)
        for y in ("2026", "2027", "2028"):
            self.assertIn("DTSTART;VALUE=DATE:%s1205" % y, body)

    def test_in_changes(self):
        ev = self.b.add("SN", "2026-03-05T00:00:00", repeat="yearly", all_day=True)
        ch = self.b.call("GET", "/v1/events/changes")[1]["changes"]
        self.assertEqual([(c["op"], c["event"]["id"], c["event"]["repeat"]) for c in ch], [("upsert", ev["id"], "yearly")])

    def test_lunar_yearly_unchanged(self):
        ld, lm = solar_to_lunar(datetime(2026, 11, 10).date())[:2]
        ev = self.b.add("Giỗ ông", "2026-11-10T00:00:00", all_day=True, repeat="lunar_yearly", lunar=(ld, lm))
        kinds = sorted({u["kind"] for u in self.b.svc.upcoming_reminders(30) if u["event_id"] == ev["id"]})
        self.assertEqual(kinds, ["on_time", "prepare_1d", "prepare_7d"])


# ------------------------------------------------------------------ 5) giảm nhắc trùng
class TestSkipFlags(Base):
    def setUp(self):
        super().setUp()
        self.b.now = datetime(2026, 10, 19, 9, 0)
        self.b.svc.register_device("pa", "android")
        self.b.svc.register_device("pb", "android")

    def keys(self, path):
        c, out = self.b.call("GET", path)
        self.assertEqual(c, 200)
        return [x["key"] for x in out]

    def test_upcoming_skip_acked_and_fired(self):
        a = self.b.add("A", "2026-10-20T09:00:00")
        b_ = self.b.add("B", "2026-10-20T10:00:00")
        c_ = self.b.add("C", "2026-10-20T11:00:00")
        self.b.svc.ack(a["id"], "2026-10-20T09:00:00")
        self.b.svc.mark_fired(b_["id"], "2026-10-20T10:00:00")
        everything = ["2026-10-20T09:00:00", "2026-10-20T10:00:00", "2026-10-20T11:00:00"]
        self.assertEqual(self.keys("/v1/reminders/upcoming?days=7"), everything)                # mặc định không đổi
        self.assertEqual(self.keys("/v1/reminders/upcoming?days=7&skip_acked=0"), everything)
        self.assertEqual(self.keys("/v1/reminders/upcoming?days=7&skip_acked=1"), ["2026-10-20T11:00:00"])
        self.assertEqual(self.keys("/v1/reminders/upcoming?days=7&skip_acked=true&device_id=pa"), ["2026-10-20T11:00:00"])
        self.assertTrue(c_["id"])

    def test_upcoming_skip_acked_per_stage(self):
        ld, lm = solar_to_lunar(datetime(2026, 11, 10).date())[:2]
        g = self.b.add("Giỗ", "2026-11-10T00:00:00", all_day=True, repeat="lunar_yearly", lunar=(ld, lm))
        k = [x["key"] for x in self.b.svc.upcoming_reminders(30)]
        self.assertEqual(len(k), 3)
        self.b.svc.ack(g["id"], "2026-11-10T00:00:00#7d")
        left = [x["key"] for x in self.b.svc.upcoming_reminders(30, skip_acked=True)]
        self.assertEqual(left, [x for x in k if not x.endswith("#7d")])

    def test_due_skip_delivered_any_device(self):
        self.b.now = datetime(2026, 10, 19, 12, 0)
        a = self.b.add("A", "2026-10-19T09:00:00")
        self.b.svc.con.execute("update events set created='2026-10-01T00:00:00'")
        b_ = self.b.add("B", "2026-10-19T10:00:00")
        self.b.svc.con.execute("update events set created='2026-10-01T00:00:00'")
        self.b.svc.con.commit()
        self.b.svc.mark_delivered("pa", a["id"], "2026-10-19T09:00:00")      # A: thiết bị pa
        self.b.svc.mark_delivered("pb", b_["id"], "2026-10-19T10:00:00")     # B: thiết bị pb
        both = ["2026-10-19T09:00:00", "2026-10-19T10:00:00"]
        self.assertEqual(self.keys("/v1/reminders/due?channel=ui"), both)    # mặc định không đổi
        self.assertEqual(self.keys("/v1/reminders/due?channel=ui&skip_delivered=0"), both)
        self.assertEqual(self.keys("/v1/reminders/due?channel=ui&skip_delivered=1"), [])
        self.assertEqual(self.keys("/v1/reminders/due?skip_delivered=1"), [])   # kênh notifier cũng áp dụng
        self.assertEqual(self.keys("/v1/reminders/due"), both)
        # vẫn giữ độc lập: ack của giao diện cũng ẩn
        c_ = self.b.add("C", "2026-10-19T11:00:00")
        self.b.svc.con.execute("update events set created='2026-10-01T00:00:00'")
        self.b.svc.con.commit()
        self.assertEqual(self.keys("/v1/reminders/due?channel=ui&skip_delivered=1"), ["2026-10-19T11:00:00"])
        self.b.svc.ack(c_["id"], "2026-10-19T11:00:00")
        self.assertEqual(self.keys("/v1/reminders/due?channel=ui&skip_delivered=1"), [])

    def test_info_features(self):
        f = self.b.call("GET", "/v1/info")[1]["features"]
        for name in ("event_update", "event_check", "repeat_yearly", "skip_acked", "skip_delivered"):
            self.assertIn(name, f)


# ------------------------------------------------------------------ 6) ngày quá khứ, trùng giờ
class TestPastDates(unittest.TestCase):
    def test_hom_kia(self):
        self.assertEqual(at("đi chợ hôm kia")[:2], (datetime(2026, 10, 18), True))
        s, allday, _, title, _ = at("họp hôm kia 8h")
        self.assertEqual((s, allday, title), (datetime(2026, 10, 18, 8, 0), False, "Họp"))
        self.assertEqual(at("hôm qua họp 8h")[0], datetime(2026, 10, 19, 8, 0))   # cũ không đổi

    def test_n_days_weeks_ago(self):
        self.assertEqual(at("đi khám 3 ngày trước")[:2], (datetime(2026, 10, 17), True))
        self.assertEqual(at("đi khám ba ngày trước 9h")[0], datetime(2026, 10, 17, 9, 0))
        self.assertEqual(at("họp 2 tuần trước")[0], datetime(2026, 10, 6))
        self.assertEqual(at("họp 1 tuần trước 14h")[0], datetime(2026, 10, 13, 14, 0))
        self.assertEqual(at("đi khám 3 ngày trước")[3], "Đi khám")

    def test_weekday_last_week(self):
        # Thứ Ba 20/10: tuần trước bắt đầu thứ Hai 12/10
        self.assertEqual(at("họp thứ năm tuần trước")[0], datetime(2026, 10, 15))
        self.assertEqual(at("họp thứ hai tuần trước 9h")[0], datetime(2026, 10, 12, 9, 0))
        self.assertEqual(at("họp chủ nhật tuần trước")[0], datetime(2026, 10, 18))
        self.assertEqual(at("họp thứ năm tuần trước")[3], "Họp")
        self.assertEqual(at("họp thứ năm tuần sau")[0], datetime(2026, 10, 29))   # cũ không đổi

    def test_vague_phrases_need_info(self):
        for t in ("bữa hổm đi chợ", "hồi trước gặp anh Nam", "mấy hôm trước đi khám 3h chiều", "bữa hổm họp 8h",
                  "hôm trước họp", "tuần trước họp 9h", "lần trước đi khám"):
            r = parse_vi(t, PNOW)
            self.assertIsNone(r.start, t)
            self.assertIn("start", r.missing, t)
            self.assertTrue(r.vague, t)

    def test_past_warning_kept(self):
        b = Box()
        self.addCleanup(b.close)
        b.now = PNOW
        r = b.svc.from_text("đi khám 3 ngày trước")
        self.assertEqual(r["status"], "draft")
        self.assertIn("thời điểm này đã qua, bạn kiểm tra lại ngày giờ", r["draft"]["warnings"])
        r = b.svc.from_text("bữa hổm đi chợ")
        self.assertEqual((r["status"], r["missing"]), ("need_info", ["start"]))
        self.assertIsNone(r["draft"]["start"])


class TestCheck(Base):
    def setUp(self):
        super().setUp()
        self.ev = self.b.add("Họp A", "2026-11-02T14:00:00", duration_min=60)
        self.b.add("Cả ngày", "2026-11-02T00:00:00", all_day=True)

    def check(self, **body):
        return self.b.call("POST", "/v1/events/check", body)

    def test_conflict_and_none(self):
        c, out = self.check(start="2026-11-02T14:30:00", duration_min=30, all_day=False)
        self.assertEqual(c, 200)
        self.assertEqual([x["title"] for x in out["conflicts"]], ["Họp A"])
        self.assertIn("occurrence_iso", out["conflicts"][0])
        self.assertEqual(self.check(start="2026-11-02T15:00:00", duration_min=30)[1], {"conflicts": []})
        self.assertEqual(self.check(start="2026-11-02T13:00:00", duration_min=60)[1], {"conflicts": []})   # chạm đầu mút
        self.assertEqual(len(self.check(start="2026-11-02T13:30:00")[1]["conflicts"]), 1)                  # mặc định 60 phút

    def test_exclude_id(self):
        out = self.check(start="2026-11-02T14:00:00", duration_min=60, exclude_id=self.ev["id"])[1]
        self.assertEqual(out["conflicts"], [])

    def test_all_day_is_empty(self):
        self.assertEqual(self.check(start="2026-11-02T00:00:00", all_day=True)[1], {"conflicts": []})

    def test_bad_input(self):
        self.assertEqual(self.check(duration_min=30)[0], 400)
        self.assertEqual(self.check(start="mai")[0], 400)
        self.assertEqual(self.check(start="2026-11-02T14:00:00", duration_min="x")[0], 400)
        self.assertEqual(self.check(start="2026-11-02T14:00:00", exclude_id="x")[0], 400)

    def test_read_only(self):
        n = self.b.svc.con.execute("select count(*) from events").fetchone()[0]
        self.check(start="2026-11-02T14:30:00", duration_min=30)
        self.assertEqual(self.b.svc.con.execute("select count(*) from events").fetchone()[0], n)


if __name__ == "__main__":
    unittest.main()
