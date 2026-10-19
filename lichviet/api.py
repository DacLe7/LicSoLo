import json
import logging
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from .service import Service
from .ui import PAGE
from .lunar import solar_to_lunar
from .tz import get_tz

log = logging.getLogger("lichviet.api")
MAX_BODY = 10 * 1024 * 1024   # JSON (kể cả tệp sao lưu); âm thanh có giới hạn riêng MAX_AUDIO
EVENT_FIELDS = {"title", "start", "duration_min", "all_day", "repeat", "remind_before_min", "notes", "lunar"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def host_ok(host_header: str) -> bool:
    """Chỉ nhận Host là máy này hoặc tên không có dấu chấm (tên service trong mạng Docker, ví dụ "app").
    Tên miền có dấu chấm bị từ chối: chặn DNS rebinding. Thêm host khác bằng LICHVIET_ALLOWED_HOSTS (cách nhau dấu phẩy)."""
    h = (host_header or "").strip().lower()
    h = h[1:h.index("]")] if h.startswith("[") and "]" in h else h.rsplit(":", 1)[0] if h.count(":") == 1 else h
    extra = {x.strip().lower() for x in os.environ.get("LICHVIET_ALLOWED_HOSTS", "").split(",") if x.strip()}
    return bool(h) and (h in LOCAL_HOSTS or "." not in h or h in extra)


def origin_ok(origin: str, host_header: str) -> bool:
    """Yêu cầu từ trang web khác (CSRF) mang Origin khác Host: từ chối. Không có Origin (curl, app khác) thì cho qua."""
    if not origin:
        return True
    return urlparse(origin).netloc.lower() == (host_header or "").strip().lower()

API_VERSION = 1
MAX_AUDIO = 8 * 1024 * 1024

CAN = ["Canh", "Tân", "Nhâm", "Quý", "Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ"]
CHI = ["Thân", "Dậu", "Tuất", "Hợi", "Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi"]


def today_info(now):
    """Hôm nay theo giờ người dùng: dương lịch + âm lịch + năm can chi (cho phần đầu trang)."""
    ld, lm, ly, leap = solar_to_lunar(now.date())
    return {"date": now.date().isoformat(), "lunar_day": ld, "lunar_month": lm, "lunar_year": ly,
            "leap": bool(leap), "year_name": CAN[ly % 10] + " " + CHI[ly % 12]}



def make_handler(svc: Service):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _url(self):
            """Mọi đường dẫn dùng được cả có và không có /v1 (hợp đồng cho app khác trong hệ sinh thái)."""
            u = urlparse(self.path)
            if u.path == "/v1" or u.path.startswith("/v1/"):
                u = u._replace(path=u.path[3:] or "/")
            return u

        def _length(self):
            try:
                return int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ValueError("Content-Length không hợp lệ")

        def _body(self):
            n = self._length()
            if n < 0 or n > MAX_BODY:
                raise ValueError("nội dung quá lớn")
            b = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(b, dict):
                raise ValueError("nội dung phải là đối tượng JSON")
            return b

        def _guard(self):
            """Chặn yêu cầu từ trang web khác và Host lạ (DNS rebinding). /health luôn qua để healthcheck chạy."""
            if self._url().path == "/health":
                return True
            if not host_ok(self.headers.get("Host")):
                self._send(403, {"error": "Host không được phép"})
                return False
            if (self.headers.get("Sec-Fetch-Site") == "cross-site"
                    or not origin_ok(self.headers.get("Origin"), self.headers.get("Host"))):
                self._send(403, {"error": "yêu cầu từ trang khác bị từ chối"})
                return False
            return True

        def _run(self, fn):
            try:
                self._send(200, fn())
            except KeyError as e:
                if e.args and isinstance(e.args[0], str):   # thiếu trường trong yêu cầu
                    self._send(400, {"error": "thiếu trường: %s" % e.args[0]})
                else:
                    self._send(404, {"error": "không tìm thấy"})
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                self._send(400, {"error": str(e)})
            except RuntimeError as e:   # giọng nói tắt hoặc chưa sẵn sàng
                self._send(503, {"error": str(e)})
            except Exception:
                log.exception("lỗi không lường trước")
                self._send(500, {"error": "lỗi nội bộ"})

        def do_GET(self):
            if not self._guard():
                return
            u = self._url()
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path in ("/", "/index.html"):
                b = PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
            if u.path == "/today":
                return self._run(lambda: today_info(svc.clock()))
            if u.path == "/info":
                return self._send(200, {"app": "lichviet", "api": API_VERSION, "tz": str(get_tz()),
                                        "now": svc.clock().isoformat(timespec="seconds"),
                                        "time_format": "ISO 8601, giờ địa phương của tz (không kèm độ lệch)"})
            if u.path == "/export":
                return self._run(svc.export_all)
            if u.path == "/phrases":
                return self._run(svc.phrases)
            if u.path == "/heard":
                return self._run(svc.heard_list)
            if u.path == "/stt/status":
                return self._run(svc.stt.status)
            if u.path == "/health":
                return self._send(200, {"ok": True})
            if u.path == "/events":
                return self._run(lambda: svc.list_range(datetime.fromisoformat(q["from"]),
                                                         datetime.fromisoformat(q["to"])))
            if u.path == "/ai/status":
                return self._run(svc.llm.status)
            if u.path == "/reminders/due":
                return self._run(svc.due_reminders)
            self._send(404, {"error": "không có đường dẫn này"})

        def do_POST(self):
            if not self._guard():
                return
            u = self._url()
            if u.path == "/stt":
                try:
                    n = self._length()
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                if n <= 0 or n > MAX_AUDIO:
                    return self._send(400, {"error": "âm thanh rỗng hoặc quá dài"})
                return self._run(lambda: {"text": svc.transcribe(self.rfile.read(n))})
            if u.path == "/stt/learn":
                b = self._body()
                return self._run(lambda: {"learned": svc.learn_heard(str(b.get("heard", "")), str(b.get("fixed", "")))})
            if u.path == "/import":
                return self._run(lambda: svc.import_all(self._body()))
            if u.path == "/parse":
                def go():
                    b = self._body()
                    return svc.from_text(b["text"], save=bool(b.get("save")))
                return self._run(go)
            if u.path == "/events":
                def go():
                    b = self._body()
                    bad = set(b) - EVENT_FIELDS
                    if bad:
                        raise ValueError("trường không hợp lệ: %s" % ", ".join(sorted(bad)))
                    b["start"] = datetime.fromisoformat(b["start"])
                    if b.get("lunar") is not None:
                        b["lunar"] = tuple(b["lunar"])
                    return svc.create(**b)
                return self._run(go)
            if u.path == "/reminders/fired":
                def go():
                    b = self._body()
                    svc.mark_fired(b["event_id"], b["occurrence"])
                    return {"ok": True}
                return self._run(go)
            self._send(404, {"error": "không có đường dẫn này"})

        def do_DELETE(self):
            if not self._guard():
                return
            u = self._url()
            if u.path.startswith("/heard/"):
                return self._run(lambda: {"deleted": svc.forget_heard(unquote(u.path.split("/", 2)[2]))})
            if u.path.startswith("/phrases/"):
                return self._run(lambda: {"deleted": svc.forget_phrase(unquote(u.path.split("/", 2)[2]))})
            if u.path.startswith("/events/"):
                return self._run(lambda: {"deleted": svc.delete(int(u.path.rsplit("/", 1)[1]))})
            self._send(404, {"error": "không có đường dẫn này"})

        def log_message(self, *a):
            pass
    return H


class Server(ThreadingHTTPServer):
    request_queue_size = 64   # mặc định 5: nhiều yêu cầu cùng lúc bị reset kết nối
    daemon_threads = True


def serve(db_path="lichviet.db", host="127.0.0.1", port=8765):
    Server((host, port), make_handler(Service(db_path))).serve_forever()
