"""Nhập bằng giọng nói (TÙY CHỌN). Chỉ làm một việc: gửi âm thanh WAV cho máy chủ nhận giọng nói cục bộ, nhận lại chữ.

Chữ nhận được sẽ đi qua đúng đường phân tích như gõ tay. Tắt/lỗi thì chỉ báo lỗi, không ảnh hưởng phần còn lại.
"""
import json
import os
import urllib.error
import urllib.request

from .speech import digits_from_words

MAX_BYTES = 8 * 1024 * 1024   # khoảng 4 phút WAV 16 kHz mono, quá đủ cho một câu lệnh


class STTClient:
    def __init__(self, base_url=None, timeout=120.0):
        if base_url is None:   # chỉ bật khi chế độ là voice hoặc both
            mode = os.environ.get("LICHVIET_AI", "off")
            base_url = os.environ.get("LICHVIET_STT_URL", "") if mode in ("voice", "both") else ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def status(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "ready": False, "detail": "chưa bật"}
        try:
            with urllib.request.urlopen(self.base_url + "/health", timeout=2) as r:
                s = json.loads(r.read())
        except Exception:
            return {"enabled": True, "ready": False, "phase": "starting",
                    "detail": "máy chủ giọng nói chưa khởi động xong"}
        return describe(s)

    def transcribe(self, wav: bytes) -> str:
        if not self.enabled:
            raise RuntimeError("Nhập bằng giọng nói chưa được bật")
        if not wav or len(wav) > MAX_BYTES:
            raise ValueError("âm thanh rỗng hoặc quá dài")
        req = urllib.request.Request(self.base_url + "/transcribe", data=wav, method="POST",
                                     headers={"Content-Type": "audio/wav"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return digits_from_words((json.loads(r.read()).get("text") or "").strip())
        except urllib.error.HTTPError as e:
            if e.code == 503:
                raise RuntimeError("Mô hình giọng nói đang tải (lần đầu mất vài phút), bạn gõ tạm hoặc thử lại sau")
            try:   # nói rõ nguyên nhân thay vì báo lỗi chung
                why = json.loads(e.read()).get("error", "")
            except Exception:
                why = ""
            raise RuntimeError("Nhận giọng nói gặp lỗi" + (": " + why if why else ""))
        except Exception:
            raise RuntimeError("Không nối được máy chủ giọng nói")


def describe(s: dict) -> dict:
    """Đổi trạng thái thô của máy chủ giọng nói thành câu dễ hiểu cho giao diện."""
    ready = bool(s.get("ready"))
    phase = "ready" if ready else (s.get("phase") or ("error" if s.get("error") else "downloading"))
    pct, got, total = s.get("percent"), s.get("downloaded_mb"), s.get("total_mb")
    if ready:
        detail = "sẵn sàng"
    elif phase == "downloading":
        detail = "đang tải mô hình giọng nói lần đầu"
        if isinstance(got, int) and isinstance(total, int) and total:
            detail += " (%d%%, %d/%d MB)" % (pct if isinstance(pct, int) else 0, got, total)
        detail += ", chỉ tải một lần, có thể mất vài phút"
    elif phase == "loading":
        detail = "đã tải xong, đang nạp mô hình vào bộ nhớ"
    elif phase == "error":
        detail = "tải mô hình chưa được (kiểm tra mạng hoặc dung lượng ổ đĩa), app sẽ tự thử lại"
    else:
        detail = "máy chủ giọng nói đang khởi động"
    out = {"enabled": True, "ready": ready, "model": s.get("model"), "phase": phase, "detail": detail,
           "percent": 100 if ready else pct, "downloaded_mb": got, "total_mb": total}
    if phase == "error" and s.get("error"):
        out["error"] = str(s["error"])[:300]
    return out
