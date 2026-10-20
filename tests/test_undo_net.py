"""Hoàn tác sau khi xóa (E17), nút Thử lại khi mất kết nối (E10), giải thích trang không an toàn (D4)."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.ui import PAGE
from test_ecosystem import Srv, svc


def script():
    return "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))


def undo_body_js():
    return re.search(r"const undoBody=.*?return b;\};\n", PAGE, re.S).group(0)


@unittest.skipUnless(shutil.which("node"), "không có node để chạy JavaScript")
class TestUndoRoundTrip(unittest.TestCase):
    """Lấy việc từ danh sách như trang, chạy undoBody bằng node, xóa rồi POST lại: việc mới phải giống hệt việc cũ."""

    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)

    def roundtrip(self, **kw):
        ev = self.s.create(**kw)
        code, items, _ = self.srv.call("GET", "/v1/events?from=2026-10-01T00:00:00&to=2027-12-31T00:00:00")
        self.assertEqual(code, 200)
        item = next(x for x in items if x["id"] == ev["id"])
        r = subprocess.run(["node", "-e", undo_body_js() + "console.log(JSON.stringify(undoBody(%s)));" % json.dumps(item)],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertEqual(self.srv.call("DELETE", "/v1/events/%d" % ev["id"])[0], 200)
        code, new, _ = self.srv.call("POST", "/v1/events", body)
        self.assertEqual(code, 200, new)
        self.assertNotIn("duplicate", new)
        keep = ("title", "start", "duration_min", "all_day", "repeat", "remind_before_min", "notes", "lunar_day", "lunar_month")
        self.assertEqual({k: new[k] for k in keep}, {k: ev[k] for k in keep})

    def test_viec_thuong(self):
        self.roundtrip(title="Họp nhóm", start=datetime(2026, 10, 22, 9, 0), duration_min=45, remind_before_min=15, notes="phòng 2")

    def test_viec_ca_ngay_lap_nam(self):
        self.roundtrip(title="Sinh nhật mẹ", start=datetime(2026, 11, 20), all_day=True, repeat="yearly")

    def test_gio_am_lich(self):
        self.roundtrip(title="Giỗ ông", start=datetime(2026, 12, 1), all_day=True, repeat="lunar_yearly", lunar=(12, 10),
                       remind_before_min=10080)

    def test_ram_hang_thang(self):
        self.roundtrip(title="Ăn chay", start=datetime(2026, 10, 25), all_day=True, repeat="lunar_monthly", lunar=(15, None))


class TestPageBits(unittest.TestCase):
    def test_thanh_hoan_tac(self):
        self.assertIn('id="undobtn">Hoàn tác</button>', PAGE)
        js = script()
        self.assertIn("Undo.offer(e)", js)
        self.assertIn("j('/events',{method:'POST',body:JSON.stringify(undoBody(e))})", js)

    def test_thu_lai_khi_mat_ket_noi(self):
        self.assertIn('id="netre">Thử lại</button>', PAGE)
        js = script()
        self.assertIn("$('netre').onclick", js)
        self.assertIn("if(was){refresh();due();}", js)       # nối lại được thì tự tải lại
        self.assertIn("addEventListener('online'", js)

    def test_giai_thich_trang_khong_an_toan(self):
        js = script()
        self.assertIn("const INSECURE=", js)
        self.assertIn("if(window.isSecureContext===false){toast(INSECURE);return;}", js)   # micro
        self.assertIn("window.isSecureContext===false?INSECURE", js)                      # mục Thông báo
        self.assertIn("mục 8", re.search(r"const INSECURE='([^']*)'", js).group(1))

    def test_micro_mo_khi_trang_khong_an_toan(self):
        """D8: nút micro làm mờ ngay khi mở trang, có nhãn đọc màn hình nêu lý do; bấm thì giải thích trước khi hỏi máy chủ."""
        js = script()
        self.assertIn(".ib.off{", PAGE)
        self.assertIn("mic.classList.add('off');mic.setAttribute('aria-disabled','true');", js)
        self.assertIn("mic.setAttribute('aria-label',mic.title)", js)
        start = js.index("async start(){")
        self.assertLess(js.index("toast(INSECURE)", start), js.index("j('/stt/status')", start))


if __name__ == "__main__":
    unittest.main()
