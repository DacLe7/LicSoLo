"""Máy chủ nhận giọng nói cục bộ (faster-whisper). Nhận WAV, trả chữ. Không gửi gì ra ngoài sau khi đã tải mô hình.

POST /transcribe   thân = tệp WAV (16 kHz, mono)  ->  {"text": "..."}
GET  /health       ->  {"ready": bool, "model": "...", "error": "...", "phase": "starting|downloading|loading|ready|error",
                        "downloaded_mb": int, "total_mb": int|null, "percent": int|null, "attempt": int}
Mô hình tải lần đầu từ Hugging Face vào /models rồi dùng lại. Tải lỗi thì tự thử lại sau STT_RETRY_S giây.
"""
import io
import json
import os
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("STT_MODEL", "small")
THREADS = int(os.environ.get("STT_THREADS", "0") or 0)
LANG = os.environ.get("STT_LANG", "vi")
MAX_BYTES = 16 * 1024 * 1024
# Gợi ý ngữ cảnh (không bắt buộc, mặc định để trống). Đừng dùng cả câu mẫu: khi âm thanh yếu, Whisper hay chép lại đúng câu gợi ý.
HINT = os.environ.get("STT_HINT", "").strip()
# những câu Whisper hay "bịa" khi gặp im lặng hoặc tiếng ồn
JUNK = ("đăng ký kênh", "ghiền mì gõ", "subscribe", "cảm ơn các bạn đã theo dõi", "hẹn gặp lại các bạn")

ROOT = os.environ.get("HF_HOME", "/models")
RETRY_S = int(os.environ.get("STT_RETRY_S", "60"))   # tải lỗi (mất mạng lần đầu...): chờ chừng này giây rồi thử lại
# Dung lượng tải về ước tính của từng mô hình (MB), để báo phần trăm khi tải lần đầu.
SIZES_MB = {"tiny": 75, "base": 145, "small": 484, "medium": 1530, "turbo": 1620,
            "large-v3-turbo": 1620, "large-v2": 3090, "large-v3": 3090, "large": 3090}

# phase: starting | downloading | loading | ready | error
state = {"ready": False, "error": "", "model": MODEL, "phase": "starting",
         "downloaded_mb": 0, "total_mb": SIZES_MB.get(MODEL), "percent": None, "attempt": 0}
_model = None
_lock = threading.Lock()


def dir_mb(root: str) -> int:
    """Tổng dung lượng (MB) các tệp trong thư mục mô hình, kể cả tệp đang tải dở (.incomplete)."""
    total = 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return total // (1024 * 1024)


def progress(downloaded_mb: int, total_mb) -> dict:
    """Phần trăm tải (tối đa 99 cho tới khi nạp xong, vì dung lượng chỉ là ước tính)."""
    if not total_mb:
        return {"downloaded_mb": downloaded_mb, "percent": None}
    return {"downloaded_mb": downloaded_mb, "percent": max(0, min(99, downloaded_mb * 100 // total_mb))}


def _watch(stop: threading.Event, start_mb: int):
    """Trong lúc tải/nạp: cập nhật số MB đã có. Dung lượng tăng là đang tải, đứng yên gần đủ là đang nạp."""
    while not stop.wait(2):
        mb = dir_mb(ROOT)
        state.update(progress(mb, state["total_mb"]))
        if mb > start_mb:
            state["phase"] = "downloading"
        if state["total_mb"] and mb >= state["total_mb"] * 0.95:
            state["phase"] = "loading"


def load_once() -> bool:
    global _model
    state["attempt"] += 1
    start_mb = dir_mb(ROOT)
    state.update(progress(start_mb, state["total_mb"]))
    state["phase"] = "loading" if state["total_mb"] and start_mb >= state["total_mb"] * 0.95 else "downloading"
    stop = threading.Event()
    threading.Thread(target=_watch, args=(stop, start_mb), daemon=True).start()
    try:
        from faster_whisper import WhisperModel
        kw = {"device": "cpu", "compute_type": "int8", "download_root": ROOT}
        if THREADS:
            kw["cpu_threads"] = THREADS
        _model = WhisperModel(MODEL, **kw)
        state.update(ready=True, error="", phase="ready", percent=100)
        return True
    except Exception as e:   # chưa có mạng lần đầu, hết ổ đĩa...
        state.update(error=str(e)[:300], phase="error")
        return False
    finally:
        stop.set()


def load(sleep=time.sleep):
    """Nạp mô hình; lỗi thì thử lại mãi sau RETRY_S giây (người dùng có thể vừa cắm mạng)."""
    while not load_once():
        sleep(RETRY_S)


def clean(text: str) -> str:
    t = " ".join(text.split()).strip()
    low = t.lower()
    if any(j in low for j in JUNK):
        return ""
    return t.rstrip(".,;")


def pcm_from_wav(wav: bytes):
    """Đọc WAV 16 kHz mono 16-bit thành mảng float32. Tự đọc, không qua PyAV (bản PyAV mới làm hỏng decode_audio của faster-whisper)."""
    import numpy as np
    try:
        with wave.open(io.BytesIO(wav), "rb") as w:
            ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except wave.Error:
        raise ValueError("không đọc được tệp WAV")
    if (ch, width, rate) != (1, 2, 16000):
        raise ValueError("cần WAV 16 kHz, mono, 16-bit")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(wav: bytes) -> str:
    audio = pcm_from_wav(wav)
    with _lock:   # mỗi lần một yêu cầu
        segs, _ = _model.transcribe(audio, language=LANG, beam_size=1, vad_filter=True,
                                    condition_on_previous_text=False,
                                    initial_prompt=HINT or None)
        return clean(" ".join(s.text for s in segs))


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, state)
        self._send(404, {"error": "không có đường dẫn này"})

    def do_POST(self):
        if self.path != "/transcribe":
            return self._send(404, {"error": "không có đường dẫn này"})
        if not state["ready"]:
            return self._send(503, {"error": "mô hình chưa sẵn sàng", **state})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BYTES:
            return self._send(400, {"error": "âm thanh rỗng hoặc quá dài"})
        try:
            self._send(200, {"text": transcribe(self.rfile.read(n))})
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            self._send(500, {"error": str(e)[:300]})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=load, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
