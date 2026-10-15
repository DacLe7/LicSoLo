"""Máy chủ nhận giọng nói cục bộ (faster-whisper). Nhận WAV, trả chữ. Không gửi gì ra ngoài sau khi đã tải mô hình.

POST /transcribe   thân = tệp WAV (16 kHz, mono)  ->  {"text": "..."}
GET  /health       ->  {"ready": bool, "model": "...", "error": "..."}
Mô hình tải lần đầu từ Hugging Face vào /models rồi dùng lại.
"""
import io
import json
import os
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("STT_MODEL", "small")
THREADS = int(os.environ.get("STT_THREADS", "0") or 0)
LANG = os.environ.get("STT_LANG", "vi")
MAX_BYTES = 16 * 1024 * 1024
# gợi ý ngữ cảnh: giúp nhận đúng cách nói về giờ giấc, ngày tháng
HINT = "Họp với anh Nam lúc 3 giờ chiều mai. Nhắc uống thuốc 7 giờ tối. Giỗ ông nội ngày 15 tháng 8 âm lịch."
# những câu Whisper hay "bịa" khi gặp im lặng hoặc tiếng ồn
JUNK = ("đăng ký kênh", "ghiền mì gõ", "subscribe", "cảm ơn các bạn đã theo dõi", "hẹn gặp lại các bạn")

state = {"ready": False, "error": "", "model": MODEL}
_model = None
_lock = threading.Lock()


def load():
    global _model
    try:
        from faster_whisper import WhisperModel
        kw = {"device": "cpu", "compute_type": "int8", "download_root": os.environ.get("HF_HOME", "/models")}
        if THREADS:
            kw["cpu_threads"] = THREADS
        _model = WhisperModel(MODEL, **kw)
        state["ready"] = True
    except Exception as e:   # chưa có mạng lần đầu, hết ổ đĩa...
        state["error"] = str(e)[:300]


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
                                    condition_on_previous_text=False, initial_prompt=HINT)
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
