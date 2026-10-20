"""Cài đặt cá nhân: tên, lời chào, nhắc trước mặc định, giờ nhắc việc cả ngày; có trong tệp sao lưu."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import ics
from lichviet.service import DEFAULT_SETTINGS
from lichviet.tz import get_tz
from lichviet.ui import PAGE
from test_ecosystem import Srv, svc, NOW


class TestSettingsService(unittest.TestCase):
    def setUp(self):
        self.s = svc()

    def test_mac_dinh(self):
        self.assertEqual(self.s.settings(), DEFAULT_SETTINGS)

    def test_doi_va_chuan_hoa(self):
        st = self.s.update_settings(name="  Lan   Anh ", default_remind_min=15)
        self.assertEqual(st["name"], "Lan Anh")
        self.assertEqual(st["default_remind_min"], 15)
        self.assertEqual(self.s.settings(), st)
        self.s.update_settings(greeting=False)
        self.assertEqual(self.s.settings()["name"], "Lan Anh")   # đổi một trường không xóa trường khác

    def test_gia_tri_sai(self):
        for bad in ({"name": "x" * 41}, {"greeting": "có"}, {"default_remind_min": -1},
                    {"default_remind_min": 10081}, {"default_remind_min": "15"}, {"all_day_hour": 24},
                    {"all_day_hour": True}, {"mau": "đỏ"}):
            with self.assertRaises(ValueError, msg=bad):
                self.s.update_settings(**bad)
        self.assertEqual(self.s.settings(), DEFAULT_SETTINGS)

    def test_du_lieu_hong_dung_mac_dinh(self):
        self.s.con.execute("INSERT INTO meta(key,value) VALUES('settings','{\"name\": 5, \"all_day_hour\": 99')")
        self.assertEqual(self.s.settings(), DEFAULT_SETTINGS)
        self.s.con.execute("UPDATE meta SET value='{\"name\": \"Hà\", \"all_day_hour\": 99}' WHERE key='settings'")
        self.assertEqual(self.s.settings(), {**DEFAULT_SETTINGS, "name": "Hà"})

    def test_nhac_truoc_mac_dinh(self):
        self.s.update_settings(default_remind_min=30)
        d = self.s.from_text("họp 3h chiều mai")["draft"]
        self.assertEqual(d["remind_before_min"], 30)
        self.assertTrue(d["remind_default"])
        self.assertEqual(d["warnings"], [])
        # câu nói rõ nhắc trước thì theo câu
        d = self.s.from_text("họp 3h chiều mai, báo trước 10 phút")["draft"]
        self.assertEqual(d["remind_before_min"], 10)
        self.assertFalse(d["remind_default"])
        ev = self.s.from_text("đi chợ 8h sáng thứ bảy", save=True)["event"]
        self.assertEqual(ev["remind_before_min"], 30)

    def test_khong_dat_thi_khong_nhac_truoc(self):
        d = self.s.from_text("họp 3h chiều mai")["draft"]
        self.assertIsNone(d["remind_before_min"])
        self.assertFalse(d["remind_default"])

    def test_gio_nhac_viec_ca_ngay(self):
        t = [datetime(2026, 10, 19, 6, 0)]
        s1, s2 = svc(lambda: t[0]), svc(lambda: t[0])
        e = s1.create("Nộp thuế", datetime(2026, 10, 19), all_day=True)
        e2 = s2.create("Nộp thuế", datetime(2026, 10, 19), all_day=True)
        s2.update_settings(all_day_hour=10)
        t[0] = NOW   # 9h
        self.assertEqual([x["event_id"] for x in s1.due_reminders()], [e["id"]])   # mặc định 8h: đã tới
        self.assertEqual(s2.due_reminders(), [])                                   # 10h: chưa tới
        up = s2.upcoming_reminders(days=2)
        self.assertEqual(up[0]["event_id"], e2["id"])
        self.assertEqual(up[0]["fire_at"], "2026-10-19T10:00:00")

    def test_ics_theo_gio_nhac_ca_ngay(self):
        e = self.s.create("Sinh nhật mẹ", datetime(2026, 11, 20), all_day=True, repeat="yearly")
        self.s.update_settings(all_day_hour=7)
        t = ics.render_event(self.s.event_calendar(e["id"]), NOW, get_tz())
        self.assertIn("TRIGGER:PT420M", t)


class TestSettingsBackup(unittest.TestCase):
    def test_sao_luu_va_khoi_phuc(self):
        a = svc()
        a.update_settings(name="Minh", default_remind_min=60, all_day_hour=6)
        data = json.loads(json.dumps(a.export_all()))
        self.assertEqual(data["settings"]["name"], "Minh")
        b = svc()
        res = b.import_all(data)
        self.assertTrue(res.get("settings"))
        self.assertEqual(b.settings(), a.settings())

    def test_khong_ghi_de_cai_dat_da_co(self):
        a = svc()
        a.update_settings(name="Minh")
        b = svc()
        b.update_settings(name="Hoa")
        res = b.import_all(a.export_all())
        self.assertNotIn("settings", res)
        self.assertEqual(b.settings()["name"], "Hoa")

    def test_tep_cu_khong_co_cai_dat(self):
        b = svc()
        b.import_all({"format": "lichviet-backup", "version": 1, "events": []})
        self.assertEqual(b.settings(), DEFAULT_SETTINGS)
        self.assertIsNone(b.con.execute("SELECT 1 FROM meta WHERE key='settings'").fetchone())

    def test_cai_dat_sai_trong_tep_bi_bo_qua(self):
        b = svc()
        b.import_all({"format": "lichviet-backup", "events": [],
                      "settings": {"name": "Tú", "all_day_hour": 30, "la": 1}})
        self.assertEqual(b.settings(), {**DEFAULT_SETTINGS, "name": "Tú"})


class TestSettingsApi(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)

    def test_get_patch(self):
        code, body, _ = self.srv.call("GET", "/v1/settings")
        self.assertEqual((code, body), (200, DEFAULT_SETTINGS))
        code, body, _ = self.srv.call("PATCH", "/v1/settings", {"name": "Lan", "default_remind_min": 15})
        self.assertEqual(code, 200)
        self.assertEqual(body["name"], "Lan")
        self.assertEqual(self.srv.call("GET", "/settings")[1]["default_remind_min"], 15)

    def test_patch_sai_tra_400_tieng_viet(self):
        code, body, _ = self.srv.call("PATCH", "/v1/settings", {"all_day_hour": 25})
        self.assertEqual(code, 400)
        self.assertIn("giờ nhắc việc cả ngày", body["error"])

    def test_info_co_tinh_nang(self):
        self.assertIn("settings", self.srv.call("GET", "/v1/info")[1]["features"])


def _js_func(name):
    m = re.search(r"const %s=.*?\};\n" % name, PAGE, re.S)
    return m.group(0)


class TestSettingsUi(unittest.TestCase):
    def test_co_muc_cai_dat(self):
        for i in ("me_name", "me_greet", "me_rm", "me_ad", "greet"):
            self.assertIn('id="%s"' % i, PAGE)
        self.assertIn("/settings", PAGE)
        self.assertIn("remind_default", PAGE)

    @unittest.skipUnless(shutil.which("node"), "không có node để chạy JavaScript")
    def test_loi_chao(self):
        js = _js_func("greetText") + """
const out=[[8,'Lan',2],[12,'',0],[15,'Lan',null],[19,'Minh',1],[23,'Lan',0],[2,'',null]].map(a=>greetText(...a));
console.log(JSON.stringify(out));"""
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out[0], ["Chào buổi sáng, Lan!", "Hôm nay có 2 việc trong lịch."])
        self.assertEqual(out[1], ["Chào buổi trưa!", "Hôm nay chưa có việc nào trong lịch."])
        self.assertEqual(out[2], ["Chào buổi chiều, Lan!", ""])
        self.assertEqual(out[3][0], "Chào buổi tối, Minh!")
        self.assertEqual(out[4][0], "Khuya rồi, Lan nghỉ sớm nhé.")
        self.assertEqual(out[5][0], "Khuya rồi, nghỉ sớm nhé.")


if __name__ == "__main__":
    unittest.main()
