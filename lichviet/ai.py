"""Lớp AI TÙY CHỌN. Không đặt LICHVIET_LLM_URL, hoặc LICHVIET_AI=off, thì không có gì chạy và mọi thứ vẫn hoạt động.

AI chỉ làm một việc: khi bộ luật không hiểu câu, nhờ mô hình tách câu thành
{"title": ..., "when": "<cụm thời gian nguyên văn>"}. Việc quy đổi ra ngày giờ
vẫn do parse_vi làm (mô hình 4B đã thử tính sai ngày tương đối).
Lỗi/chậm/tắt AI -> trả None, người gọi tự quay về bộ luật.
"""
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request

log = logging.getLogger("lichviet.ai")

PROMPT = (
    "/no_think\n"
    "Tách câu lệnh lịch tiếng Việt thành JSON, chỉ trả JSON, không giải thích.\n"
    'Dạng: {"title": "việc cần làm, ngắn gọn", "when": "cụm thời gian viết lại đơn giản"}\n'
    'Viết lại "when" theo dạng đơn giản: "ngày D/M", "hôm nay", "ngày mai", "ngày kia", '
    '"thứ N tuần sau", "H giờ M phút" (kèm sáng/chiều/tối nếu có). '
    "Giữ nguyên cụm tương đối, KHÔNG tự tính ra ngày dương lịch từ 'mai', 'tuần sau'.\n"
    'Nếu không có thời gian thì "when" là "".\n'
    "Ví dụ:\n"
    'Câu: đi khám răng ngày mốt lúc 9 giờ sáng\n{"title": "đi khám răng", "when": "ngày kia 9 giờ sáng"}\n'
    'Câu: họp mồng 5 tháng 11 lúc 2 giờ chiều\n{"title": "họp", "when": "ngày 5/11 2 giờ chiều"}\n'
    'Câu: gọi mẹ tối thứ sáu tuần tới\n{"title": "gọi mẹ", "when": "thứ sáu tuần sau tối"}\n'
    "Câu: "
)

# Ép mô hình chỉ sinh JSON đúng dạng: không lan man, ít chữ hơn nên nhanh hơn.
SCHEMA = {"type": "object",
          "properties": {"title": {"type": "string"}, "when": {"type": "string"}},
          "required": ["title", "when"]}


class LLMClient:
    def __init__(self, base_url=None, timeout=45.0, max_fail=3, cooldown=60.0, slow_s=30.0, slow_limit=3):
        if base_url is None:   # chỉ bật khi LICHVIET_AI=on (nếu có đặt) và có địa chỉ
            on = os.environ.get("LICHVIET_AI", "on") in ("on", "ai", "both")
            base_url = os.environ.get("LICHVIET_LLM_URL", "") if on else ""
        self.base_url = base_url.rstrip("/")
        self.timeout, self.max_fail, self.cooldown = timeout, max_fail, cooldown
        self._lock = threading.Lock()   # mỗi lần chỉ 1 yêu cầu, tránh tranh CPU
        self._fails = 0
        self._off_until = 0.0
        self.slow_s, self.slow_limit = slow_s, slow_limit   # chậm hơn slow_s giây, liên tiếp slow_limit lần -> xin hạ bậc
        self._slow_run = 0
        self._downgrade_at = 0.0
        self.state_dir = os.environ.get("LICHVIET_AI_STATE", "/ai-models")
        self._json_mode = True          # tự tắt nếu máy chủ AI không nhận response_format
        self.last = {"status": "off", "detail": ""}   # kết quả lần gọi gần nhất, để hiển thị/gỡ lỗi

    @property
    def enabled(self) -> bool:
        return bool(self.base_url) and time.time() >= self._off_until

    # ---------- theo dõi tốc độ, tự xin hạ bậc mô hình ----------
    def hardware(self):
        """Nội dung ai-status.json do container AI ghi lúc chọn mô hình (None nếu chưa có)."""
        try:
            with open(os.path.join(self.state_dir, "ai-status.json"), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def status(self) -> dict:
        return {"enabled": self.enabled, "last": self.last, "slow_run": self._slow_run, "hardware": self.hardware()}

    def _note_latency(self, secs: float) -> None:
        if secs <= self.slow_s:
            self._slow_run = 0
            return
        self._slow_run += 1
        if self._slow_run >= self.slow_limit:
            self._slow_run = 0
            self._request_downgrade()

    def _request_downgrade(self) -> None:
        """Mô hình chạy quá chậm trên máy này: ghi file yêu cầu, container AI sẽ tự khởi động lại bằng bậc nhẹ hơn."""
        hw = self.hardware()
        if not hw or hw.get("forced") or hw.get("tier") == "tiny":
            return   # không biết cấu hình, hoặc người dùng ép bậc, hoặc đã nhỏ nhất rồi
        if time.time() - self._downgrade_at < 900:
            return
        n = int(hw.get("downgrade", 0)) + 1
        try:
            with open(os.path.join(self.state_dir, "downgrade"), "w") as f:   # ghi thẳng: thư mục không chắc cho tạo file mới
                f.write(str(n))
            self._downgrade_at = time.time()
            log.warning("AI qua cham tren bac %s, xin ha %d bac", hw.get("tier"), n)
        except Exception as e:
            log.warning("khong ghi duoc yeu cau ha bac: %s", e)

    def _post(self, text: str) -> str:
        payload = {
            "messages": [{"role": "user", "content": PROMPT + text[:500]}],
            "temperature": 0, "max_tokens": 80,
            "cache_prompt": True,   # phần hướng dẫn cố định ở đầu chỉ phải đọc một lần
        }
        if self._json_mode:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "lich", "schema": SCHEMA}}
        req = urllib.request.Request(self.base_url + "/v1/chat/completions",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out["choices"][0]["message"]["content"]

    def extract(self, text: str):
        """Trả {"title","when"} hoặc None (AI tắt, bận, lỗi, hoặc trả sai dạng). Ghi lại lý do vào self.last."""
        if not self.base_url:
            self.last = {"status": "off", "detail": "AI đang tắt hoặc chưa có địa chỉ"}
            return None
        if time.time() < self._off_until:
            self.last = {"status": "paused", "detail": "AI tạm nghỉ sau nhiều lần lỗi"}
            return None
        if not self._lock.acquire(blocking=False):
            self.last = {"status": "busy", "detail": "AI đang xử lý yêu cầu khác"}
            return None
        t0 = time.time()
        raw = ""
        try:
            try:
                raw = self._post(text)
            except urllib.error.HTTPError as e:
                if self._json_mode and e.code in (400, 422, 501):   # bản máy chủ AI này không nhận response_format
                    self._json_mode = False
                    raw = self._post(text)
                else:
                    raise
            a, b = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[a:b + 1])
            res = {"title": str(data.get("title", "")).strip(), "when": str(data.get("when", "")).strip()}
            self._fails = 0
            self._note_latency(time.time() - t0)
            self.last = {"status": "ok", "detail": "%.1f giây" % (time.time() - t0), "raw": raw[:200]}
            log.warning("AI ok %.1fs raw=%r", time.time() - t0, raw[:200])
            return res
        except Exception as e:
            self._fails += 1
            if "timed out" in str(e).lower() or isinstance(e, TimeoutError):
                self._note_latency(self.timeout + 1)   # quá hạn chờ cũng tính là chậm
            self.last = {"status": "error", "detail": "%s: %s" % (type(e).__name__, str(e)[:120]), "raw": raw[:200]}
            log.warning("AI loi %.1fs %s raw=%r", time.time() - t0, self.last["detail"], raw[:200])
            if self._fails >= self.max_fail:     # ngắt mạch: tạm nghỉ, không làm phiền máy
                self._off_until = time.time() + self.cooldown
                self._fails = 0
            return None
        finally:
            self._lock.release()
