"""Tiến độ tải mô hình giọng nói và tự thử lại. Không tải mô hình thật: faster_whisper được giả lập."""
import importlib.util
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lichviet.stt import describe

SERVER = os.path.join(os.path.dirname(__file__), "..", "stt", "server.py")


def load_server(root):
    old = os.environ.get("HF_HOME")
    os.environ["HF_HOME"] = root
    try:
        spec = importlib.util.spec_from_file_location("stt_server_test", SERVER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HF_HOME", None)
        else:
            os.environ["HF_HOME"] = old


class FakeWhisper(types.ModuleType):
    """Lần gọi đầu lỗi (như mất mạng), các lần sau thành công."""
    def __init__(self, fail_times=1):
        super().__init__("faster_whisper")
        self.calls = 0
        outer = self

        class WhisperModel:
            def __init__(self, name, **kw):
                outer.calls += 1
                outer.kw = kw
                if outer.calls <= fail_times:
                    raise OSError("không có mạng")
        self.WhisperModel = WhisperModel


class TestServerProgress(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.srv = load_server(self.root)
        self.addCleanup(sys.modules.pop, "faster_whisper", None)

    def test_progress_capped_until_ready(self):
        self.assertEqual(self.srv.progress(242, 484), {"downloaded_mb": 242, "percent": 50})
        self.assertEqual(self.srv.progress(600, 484)["percent"], 99)
        self.assertIsNone(self.srv.progress(10, None)["percent"])

    def test_dir_mb_counts_partial_files(self):
        os.makedirs(os.path.join(self.root, "a", "b"))
        with open(os.path.join(self.root, "a", "b", "model.bin.incomplete"), "wb") as f:
            f.write(b"\0" * (3 * 1024 * 1024))
        self.assertEqual(self.srv.dir_mb(self.root), 3)

    def test_error_then_retry_until_ready(self):
        fake = FakeWhisper(fail_times=2)
        sys.modules["faster_whisper"] = fake
        sleeps = []
        self.srv.load(sleep=lambda s: (sleeps.append(s), self.assertEqual(self.srv.state["phase"], "error")))
        self.assertEqual(fake.calls, 3)
        self.assertEqual(sleeps, [self.srv.RETRY_S] * 2)
        st = self.srv.state
        self.assertTrue(st["ready"])
        self.assertEqual((st["phase"], st["percent"], st["error"], st["attempt"]), ("ready", 100, "", 3))
        self.assertEqual(fake.kw["download_root"], self.root)

    def test_missing_library_is_error_not_crash(self):
        sys.modules["faster_whisper"] = None   # import sẽ lỗi
        self.assertFalse(self.srv.load_once())
        self.assertEqual(self.srv.state["phase"], "error")
        self.assertFalse(self.srv.state["ready"])


class TestDescribe(unittest.TestCase):
    def test_downloading_shows_percent(self):
        d = describe({"ready": False, "phase": "downloading", "percent": 40, "downloaded_mb": 194, "total_mb": 484})
        self.assertEqual((d["phase"], d["percent"]), ("downloading", 40))
        self.assertIn("40%", d["detail"])
        self.assertIn("194/484 MB", d["detail"])

    def test_loading_and_ready(self):
        self.assertIn("nạp", describe({"phase": "loading"})["detail"])
        d = describe({"ready": True, "phase": "ready", "percent": 99})
        self.assertEqual((d["ready"], d["percent"], d["detail"]), (True, 100, "sẵn sàng"))

    def test_error_is_friendly_and_keeps_reason(self):
        d = describe({"ready": False, "phase": "error", "error": "Connection refused"})
        self.assertIn("tự thử lại", d["detail"])
        self.assertEqual(d["error"], "Connection refused")

    def test_old_server_without_phase(self):
        # máy chủ giọng nói bản cũ chỉ có ready/error
        self.assertEqual(describe({"ready": False})["phase"], "downloading")
        self.assertEqual(describe({"ready": False, "error": "x"})["phase"], "error")


if __name__ == "__main__":
    unittest.main()
