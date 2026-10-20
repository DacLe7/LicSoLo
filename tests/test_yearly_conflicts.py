"""Lặp hằng năm theo dương lịch (sinh nhật, kỷ niệm) và kiểm tra trùng giờ cho form Sửa.
Giờ giả lập: Thứ Hai 19/10/2026 09:00 (NOW của test_ecosystem)."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import ics
from lichviet.parser import fold, parse_vi
from lichviet.tz import get_tz
from test_ecosystem import NOW, Srv, svc


def p(text, now=NOW):
    return parse_vi(text, now)


class TestYearlyParse(unittest.TestCase):
    def test_hang_nam_moi_nam(self):
        for t in ("sinh nhật mẹ 20/11 hằng năm", "sinh nhat me 20/11 hang nam", "sinh nhật mẹ 20/11 mỗi năm",
                  "sinh nhật mẹ ngày 20 tháng 11 hàng năm"):
            r = p(t)
            self.assertEqual((r.repeat, r.start, r.all_day), ("yearly", datetime(2026, 11, 20), True), t)
            self.assertEqual(fold(r.title), "sinh nhat me", t)
            self.assertEqual(r.warnings, [], t)

    def test_ngay_da_qua_trong_nam_lay_nam_sau(self):
        r = p("kỷ niệm ngày cưới 2/9 mỗi năm")
        self.assertEqual((r.repeat, r.start), ("yearly", datetime(2027, 9, 2)))
        self.assertEqual(r.title, "Kỷ niệm ngày cưới")

    def test_co_gio(self):
        r = p("tiệc tất niên 7h tối 28/12 hằng năm")
        self.assertEqual((r.repeat, r.start, r.all_day), ("yearly", datetime(2026, 12, 28, 19, 0), False))

    def test_nam_sinh_doi_sang_lan_toi(self):
        r = p("sinh nhật bố 5/3/1960 hằng năm")
        self.assertEqual((r.repeat, r.start), ("yearly", datetime(2027, 3, 5)))
        self.assertNotIn("1960", r.title)

    def test_29_2(self):
        r = p("sinh nhật bé 29/2 hằng năm")
        self.assertEqual((r.repeat, r.start), ("yearly", datetime(2024, 2, 29)))
        self.assertTrue(any("28/2" in w for w in r.warnings), r.warnings)
        self.assertEqual(p("sinh nhật bé 30/2 hằng năm").start, None)

    def test_sinh_nhat_tu_lap_co_canh_bao(self):
        for t in ("sinh nhật mẹ 20/11", "kỷ niệm ngày cưới 2/9", "thôi nôi bé 5 tháng 12"):
            r = p(t)
            self.assertEqual(r.repeat, "yearly", t)
            self.assertTrue(any("lặp hằng năm" in w for w in r.warnings), (t, r.warnings))

    def test_sinh_nhat_co_nam_hoac_ngay_tuong_doi_khong_tu_lap(self):
        self.assertIsNone(p("tiệc sinh nhật bé 20/11/2026").repeat)
        self.assertIsNone(p("mua quà sinh nhật mai").repeat)

    def test_viec_thuong_khong_tu_lap(self):
        self.assertIsNone(p("nộp báo cáo 25/10").repeat)

    def test_am_lich_hang_nam_van_la_am_lich(self):
        r = p("sinh nhật bà 10/3 âm lịch hằng năm")
        self.assertEqual((r.repeat, r.lunar), ("lunar_yearly", (10, 3)))
        r = p("sinh nhật bà 10/3 âm lịch")
        self.assertEqual(r.repeat, "lunar_yearly")
        self.assertFalse(any("lặp hằng năm" in w for w in r.warnings), r.warnings)

    def test_nam_la_so_khong_phai_lap(self):
        r = p("họp mỗi năm phút")   # "năm phút" không phải "mỗi năm"
        self.assertNotEqual(r.repeat, "yearly")


class TestYearlyService(unittest.TestCase):
    def test_occurrences(self):
        s = svc()
        s.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        occ = [e["occurrence"] for e in s.list_range(datetime(2026, 1, 1), datetime(2030, 1, 1))]
        self.assertEqual(occ, ["2026-11-20T00:00:00", "2027-11-20T00:00:00", "2028-11-20T00:00:00", "2029-11-20T00:00:00"])

    def test_29_2_nam_khong_nhuan_thanh_28_2(self):
        s = svc()
        s.create("Sinh nhật bé", datetime(2024, 2, 29), all_day=True, repeat="yearly")
        occ = [e["occurrence"][:10] for e in s.list_range(datetime(2026, 1, 1), datetime(2029, 1, 1))]
        self.assertEqual(occ, ["2026-02-28", "2027-02-28", "2028-02-29"])

    def test_bat_dau_lau_roi_van_nhanh(self):
        s = svc()
        s.create("Sinh nhật ông", datetime(1930, 6, 1, 8, 0), repeat="yearly")
        occ = [e["occurrence"] for e in s.list_range(datetime(2027, 1, 1), datetime(2028, 1, 1))]
        self.assertEqual(occ, ["2027-06-01T08:00:00"])

    def test_nhac_dung_ngay(self):
        clk = [datetime(2026, 11, 19, 9, 0)]
        s = svc(lambda: clk[0])
        s.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        clk[0] = datetime(2027, 11, 20, 8, 5)
        due = s.due_reminders()
        self.assertEqual([d["occurrence"] for d in due], ["2027-11-20T00:00:00"])

    def test_from_text_saves_yearly_and_edit_back(self):
        s = svc()
        r = s.from_text("sinh nhật mẹ 20/11 hằng năm", save=True)
        ev = r["event"]
        self.assertEqual(ev["repeat"], "yearly")
        ev2 = s.update(ev["id"], repeat=None)
        self.assertIsNone(ev2["repeat"])
        self.assertEqual(s.update(ev["id"], repeat="yearly")["repeat"], "yearly")

    def test_backup_roundtrip(self):
        a = svc()
        a.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        b = svc()
        self.assertEqual(b.import_all(a.export_all())["added"], 1)
        self.assertEqual(b.list_range(datetime(2027, 11, 1), datetime(2027, 12, 1))[0]["repeat"], "yearly")

    def test_ics_moi_nam_mot_vevent(self):
        s = svc()
        s.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        out = ics.render(s.calendar_items(datetime(2026, 10, 1), datetime(2028, 12, 31)), NOW, get_tz())
        self.assertEqual(out.count("BEGIN:VEVENT"), 3)
        self.assertIn("DTSTART;VALUE=DATE:20271120", out)
        self.assertIn("Lặp hằng năm", out)


class TestConflictsApi(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)
        self.a = self.s.create("Họp nhóm", datetime(2026, 10, 20, 9, 0), duration_min=60)

    def test_trung_va_khong_trung(self):
        c, l, _ = self.srv.call("GET", "/v1/conflicts?start=2026-10-20T09:30:00")
        self.assertEqual(c, 200)
        self.assertEqual([(x["id"], x["title"]) for x in l], [(self.a["id"], "Họp nhóm")])
        self.assertEqual(set(l[0]), {"id", "title", "occurrence"})
        self.assertEqual(self.srv.call("GET", "/v1/conflicts?start=2026-10-20T10:00:00")[1], [])
        # 8h kéo dài 90 phút chạm 9h
        self.assertEqual(len(self.srv.call("GET", "/v1/conflicts?start=2026-10-20T08:00:00&duration_min=90")[1]), 1)

    def test_bo_qua_viec_dang_sua(self):
        c, l, _ = self.srv.call("GET", "/v1/conflicts?start=2026-10-20T09:00:00&exclude=%d" % self.a["id"])
        self.assertEqual((c, l), (200, []))

    def test_tham_so_sai(self):
        self.assertEqual(self.srv.call("GET", "/v1/conflicts")[0], 400)
        self.assertEqual(self.srv.call("GET", "/v1/conflicts?start=mai")[0], 400)
        self.assertEqual(self.srv.call("GET", "/v1/conflicts?start=2026-10-20T09:00:00&duration_min=0")[0], 400)
        self.assertEqual(self.srv.call("GET", "/v1/conflicts?start=2026-10-20T09:00:00&exclude=x")[0], 400)

    def test_post_events_tra_trung_gio(self):
        c, ev, _ = self.srv.call("POST", "/v1/events", {"title": "Gọi khách", "start": "2026-10-20T09:15:00"})
        self.assertEqual(c, 200)
        self.assertEqual([x["title"] for x in ev["conflicts"]], ["Họp nhóm"])
        c, ev, _ = self.srv.call("POST", "/v1/events", {"title": "Nghỉ", "start": "2026-10-21T00:00:00", "all_day": True})
        self.assertEqual(ev["conflicts"], [])

    def test_post_events_yearly(self):
        c, ev, _ = self.srv.call("POST", "/v1/events", {"title": "Sinh nhật", "start": "2026-11-20T00:00:00",
                                                     "all_day": True, "repeat": "yearly"})
        self.assertEqual((c, ev["repeat"]), (200, "yearly"))

    def test_ui_goi_kiem_tra_trung(self):
        from lichviet.ui import PAGE
        self.assertIn("'/conflicts?start='", PAGE)
        self.assertIn('id="e_cf" aria-live="polite"', PAGE)
        self.assertIn("['yearly','Mỗi năm']", PAGE)


if __name__ == "__main__":
    unittest.main()
