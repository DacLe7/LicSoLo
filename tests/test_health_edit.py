"""/health kiểm tra database và trả phiên bản; báo lỗi database bằng tiếng Việt; sửa việc đã lưu qua PATCH."""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet import __version__
from lichviet.service import db_error_vi
from lichviet.ui import PAGE
from test_ecosystem import Srv, svc, NOW, KEY


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)

    def test_health_ok_has_version(self):
        code, body, _ = self.srv.call("GET", "/health")
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": True, "version": __version__, "db": "ok"})
        self.assertEqual(self.srv.call("GET", "/v1/health")[0], 200)

    def test_health_writes_meta(self):
        self.s.health()
        row = self.s.con.execute("SELECT value FROM meta WHERE key='health_check'").fetchone()
        self.assertEqual(row[0], "2026-10-19T09:00:00")

    def test_health_db_broken_gives_503_vietnamese(self):
        def boom():
            raise RuntimeError(db_error_vi("/data/lichviet.db", sqlite3.OperationalError("attempt to write a readonly database")))
        with mock.patch.object(self.s, "health", boom):
            code, body, _ = self.srv.call("GET", "/health")
        self.assertEqual(code, 503)
        self.assertFalse(body["ok"])
        self.assertIn("không có quyền ghi", body["error"])

    def test_info_has_version(self):
        code, body, _ = self.srv.call("GET", "/v1/info")
        self.assertEqual(body["version"], __version__)

    def test_ui_shows_version(self):
        self.assertIn('id="ver"', PAGE)
        self.assertIn("phiên bản", PAGE)


class TestDbErrors(unittest.TestCase):
    def test_messages(self):
        cases = {"attempt to write a readonly database": "không có quyền ghi",
                 "unable to open database file": "không có quyền ghi",
                 "database or disk is full": "ổ đĩa đầy",
                 "database is locked": "khóa",
                 "file is not a database": "bị hỏng"}
        for raw, want in cases.items():
            self.assertIn(want, db_error_vi("x.db", sqlite3.OperationalError(raw)), raw)

    def test_real_corrupt_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "hong.db")
        with open(p, "wb") as f:
            f.write(b"day khong phai sqlite" * 100)
        from lichviet import Service
        s = Service(p)
        with self.assertRaises(RuntimeError) as cm:
            s.health()
        self.assertIn("Không dùng được database", str(cm.exception))

    def test_serve_exits_on_bad_db(self):
        from lichviet import api
        with mock.patch.object(api.Service, "health", side_effect=RuntimeError("Không dùng được database x")):
            with self.assertRaises(SystemExit) as cm, self.assertLogs("lichviet.api", "CRITICAL"):
                api.serve(":memory:", port=0)
        self.assertEqual(cm.exception.code, 2)


class TestPatch(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)
        self.ev = self.s.create("Họp nhóm", datetime(2026, 10, 20, 9, 0))

    def test_patch_title_and_time(self):
        code, body, _ = self.srv.call("PATCH", "/v1/events/%d" % self.ev["id"],
                                      {"title": " Họp dự án ", "start": "2026-10-20T14:30:00", "remind_before_min": 15})
        self.assertEqual(code, 200, body)
        self.assertEqual(body["title"], "Họp dự án")
        self.assertEqual(body["start"], "2026-10-20T14:30:00")
        self.assertTrue(body["start_iso"].endswith("+07:00"))
        self.assertEqual(body["remind_before_min"], 15)
        self.assertEqual(body["conflicts"], [])

    def test_patch_reports_conflict(self):
        other = self.s.create("Gặp khách", datetime(2026, 10, 20, 15, 0))
        code, body, _ = self.srv.call("PATCH", "/events/%d" % self.ev["id"], {"start": "2026-10-20T15:30:00"})
        self.assertEqual(code, 200)
        self.assertEqual([c["id"] for c in body["conflicts"]], [other["id"]])

    def test_patch_logs_change(self):
        self.srv.call("PATCH", "/events/%d" % self.ev["id"], {"title": "Mới"})
        ch = self.s.changes_since(0)["changes"]
        self.assertEqual(ch[-1]["event"]["title"], "Mới")

    def test_patch_errors(self):
        eid = self.ev["id"]
        self.assertEqual(self.srv.call("PATCH", "/events/9999", {"title": "x"})[0], 404)
        self.assertEqual(self.srv.call("PATCH", "/events/abc", {"title": "x"})[0], 404)
        code, body, _ = self.srv.call("PATCH", "/events/%d" % eid, {"title": "   "})
        self.assertEqual((code, body["error"]), (400, "thiếu tiêu đề"))
        self.assertEqual(self.srv.call("PATCH", "/events/%d" % eid, {"hack": 1})[0], 400)
        self.assertEqual(self.srv.call("PATCH", "/events/%d" % eid, {"repeat": "yearly_x"})[0], 400)
        self.assertEqual(self.srv.call("PATCH", "/events/%d" % eid, {"repeat": "lunar_yearly"})[0], 400)
        self.assertEqual(self.srv.call("PATCH", "/events/%d" % eid, {"start": "ngày mai"})[0], 400)
        self.assertEqual(self.s.get(eid)["title"], "Họp nhóm")   # lỗi thì không đổi gì

    def test_patch_lunar(self):
        code, body, _ = self.srv.call("PATCH", "/events/%d" % self.ev["id"],
                                      {"repeat": "lunar_yearly", "lunar": [10, 3]})
        self.assertEqual(code, 200, body)
        self.assertEqual((body["lunar_day"], body["lunar_month"], body["repeat"]), (10, 3, "lunar_yearly"))

    def test_patch_needs_key_when_configured(self):
        srv = Srv(self.s, {"LICHVIET_API_KEY": KEY, "LICHVIET_ICS_KEY": ""})
        self.addCleanup(srv.close)
        self.assertEqual(srv.call("PATCH", "/events/%d" % self.ev["id"], {"title": "x"})[0], 401)
        self.assertEqual(srv.call("PATCH", "/events/%d" % self.ev["id"], {"title": "x"},
                                  {"X-Lacviet-Key": KEY})[0], 200)

    def test_patch_cross_site_blocked(self):
        code, _, _ = self.srv.call("PATCH", "/events/%d" % self.ev["id"], {"title": "x"},
                                   {"Origin": "http://evil.example"})
        self.assertEqual(code, 403)

    def test_ui_has_edit_button(self):
        self.assertIn("method:'PATCH'", PAGE)
        self.assertIn('class="del ed"', PAGE)


if __name__ == "__main__":
    unittest.main()
