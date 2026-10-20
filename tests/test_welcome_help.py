"""Lần đầu mở: lời chào kèm câu mẫu; mục Hướng dẫn nhanh: mọi câu ví dụ đều được hiểu."""
import os
import re
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.ui import PAGE
from test_ecosystem import Srv, svc


def help_examples():
    sec = re.search(r'<details class="more" id="help">(.*?)</details>', PAGE, re.S).group(1)
    return re.findall(r"<q>(.*?)</q>", sec)


def welcome_examples():
    return re.findall(r"'([^']+)'", re.search(r"const TRIES=\[(.*?)\];", PAGE).group(1))


class TestWelcome(unittest.TestCase):
    def setUp(self):
        self.s = svc()
        self.srv = Srv(self.s, {"LICHVIET_API_KEY": "", "LICHVIET_ICS_KEY": ""})
        self.addCleanup(self.srv.close)

    def test_info_counts_events(self):
        self.assertEqual(self.srv.call("GET", "/v1/info")[1]["events"], 0)
        self.s.create("Họp", datetime(2026, 10, 20, 9, 0))
        self.assertEqual(self.srv.call("GET", "/v1/info")[1]["events"], 1)
        self.assertEqual(self.s.event_count(), 1)

    def test_welcome_markup(self):
        self.assertIn('id="welcome" hidden', PAGE)   # ẩn sẵn, chỉ hiện khi /info báo 0 việc
        self.assertIn("welcome(x.events)", PAGE)
        self.assertIn("welcome(1)", PAGE)            # lưu xong thì ẩn
        self.assertGreaterEqual(len(welcome_examples()), 3)


class TestExamplesParse(unittest.TestCase):
    """Câu ví dụ trong giao diện phải ra bản nháp đầy đủ, nếu không người mới bấm thử sẽ thấy app 'không hiểu'."""

    def check(self, sentences):
        s = svc()
        for t in sentences:
            with self.subTest(t=t):
                r = s.from_text(t)
                self.assertEqual(r["status"], "draft", r)
                d = r["draft"]
                self.assertTrue(d["title"])
                self.assertEqual(d.get("warnings") or [], [])

    def test_help_examples(self):
        ex = help_examples()
        self.assertGreaterEqual(len(ex), 12)
        self.check(ex)

    def test_welcome_and_chip_examples(self):
        chips = re.findall(r"'([^']+)'", re.search(r"const SAMPLES=\[(.*?)\];", PAGE).group(1))
        self.check(welcome_examples() + chips)

    def test_help_repeat_kinds(self):
        s = svc()
        want = {"uống thuốc 7h tối mỗi ngày": "daily", "họp nhóm 9h thứ hai hằng tuần": "weekly",
                "đóng tiền nhà ngày 5 mỗi tháng": "monthly", "giỗ ông nội 15/8 âm lịch": "lunar_yearly",
                "cúng rằm mỗi tháng": "lunar_monthly"}
        for t, rep in want.items():
            self.assertIn(t, help_examples())
            self.assertEqual(s.from_text(t)["draft"]["repeat"], rep, t)
        self.assertEqual(s.from_text("đi đám cưới chủ nhật 11h trưa, nhắc tôi trước 1 ngày")["draft"]["remind_before_min"], 1440)

    def test_user_guide_examples(self):
        """Bảng "Các kiểu câu app hiểu" trong docs/HUONG_DAN.md phải đúng với bộ hiểu câu."""
        path = os.path.join(os.path.dirname(__file__), "..", "docs", "HUONG_DAN.md")
        with open(path, encoding="utf-8") as f:
            doc = f.read()
        table = doc.split("### Các kiểu câu app hiểu", 1)[1].split("Mẹo:", 1)[0]
        ex = []
        for row in table.splitlines():
            if row.startswith("| ") and "Ngày đã qua" not in row:
                ex += [t for t in re.findall(r'"([^"]+)"', row) if t != "báo trước 30 phút"]
        self.assertGreaterEqual(len(ex), 12)
        self.check(ex)


if __name__ == "__main__":
    unittest.main()
