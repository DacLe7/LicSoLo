import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from .service import Service, CursorTooOld
from .ui import PAGE
from .lunar import solar_to_lunar
from .tz import get_tz
from . import ics

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


USER_ID = os.environ.get("LICHVIET_USER_ID", "default")   # app một người dùng; hệ sinh thái có thể đặt để định danh


def with_iso(item: dict) -> dict:
    """Thêm bản ISO 8601 kèm độ lệch múi giờ (+07:00) bên cạnh giờ địa phương không kèm múi giờ (giữ tương thích)."""
    out = dict(item)
    for k in ("start", "occurrence"):
        if isinstance(out.get(k), str):
            try:
                out[k + "_iso"] = datetime.fromisoformat(out[k]).replace(tzinfo=get_tz()).isoformat()
            except ValueError:
                pass
    return out


def _flag(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes")


def _event_fields(b: dict) -> dict:
    """Kiểm tra và đổi trường JSON của việc sang tham số service (dùng chung cho POST và PATCH /events)."""
    bad = set(b) - EVENT_FIELDS
    if bad:
        raise ValueError("trường không hợp lệ: %s" % ", ".join(sorted(bad)))
    if "start" in b:
        b["start"] = datetime.fromisoformat(b["start"])
    if b.get("lunar") is not None:
        b["lunar"] = tuple(b["lunar"])
    return b


def today_info(now):
    """Hôm nay theo giờ người dùng: dương lịch + âm lịch + năm can chi (cho phần đầu trang)."""
    ld, lm, ly, leap = solar_to_lunar(now.date())
    return {"date": now.date().isoformat(), "lunar_day": ld, "lunar_month": lm, "lunar_year": ly,
            "leap": bool(leap), "year_name": CAN[ly % 10] + " " + CHI[ly % 12]}



def _key_from_env(name: str) -> str:
    k = os.environ.get(name, "")
    if k and len(k) < 16:
        raise ValueError("%s quá ngắn (cần ít nhất 16 ký tự)" % name)
    return k


def make_handler(svc: Service):
    api_key = _key_from_env("LICHVIET_API_KEY")   # khóa cho app/hệ sinh thái; trống = chế độ cục bộ cũ
    ics_key = _key_from_env("LICHVIET_ICS_KEY")   # khóa chỉ đọc cho đăng ký lịch .ics qua URL (?key=)

    class H(BaseHTTPRequestHandler):
        def _fail_auth(self, code, msg):
            time.sleep(0.3)   # làm chậm dò khóa
            self._send(code, {"error": msg})
            return False

        def _is_ui(self) -> bool:
            """Trang giao diện đi kèm chạy trên chính máy chủ này (cùng nguồn gốc trong trình duyệt).
            Trình duyệt đã chặn trang khác (Origin/Sec-Fetch-Site), nên ở đây được tin; client khác phải có khóa."""
            if self.headers.get("Sec-Fetch-Site") == "same-origin":
                return True
            origin = self.headers.get("Origin")
            return bool(origin) and urlparse(origin).netloc.lower() == (self.headers.get("Host") or "").strip().lower()

        def _auth(self, required: bool, q=None, ics_ok: bool = False) -> bool:
            """Kiểm tra khóa.
            - Khi đã đặt LICHVIET_API_KEY: MỌI API (trừ /health và giao diện đi kèm) phải có khóa qua
              header X-Lacviet-Key hoặc Authorization: Bearer; sai/thiếu → 401.
            - Khi chưa đặt khóa: mọi endpoint mở như bản trước (khóa là tùy chọn). Cổng vẫn chỉ nghe 127.0.0.1 và chặn Host/Origin lạ.
            - ics_ok: ?key= khớp LICHVIET_ICS_KEY cũng được (chỉ cho đăng ký lịch .ics)."""
            if ics_ok and ics_key and q and hmac.compare_digest((q.get("key") or "").encode(), ics_key.encode()):
                return True
            if api_key:
                given = self.headers.get("X-Lacviet-Key") or ""
                auth = self.headers.get("Authorization") or ""
                if not given and auth.lower().startswith("bearer "):
                    given = auth[7:].strip()
                if hmac.compare_digest(given.encode(), api_key.encode()):
                    return True
                if self._is_ui() and not ics_ok:
                    return True
                return self._fail_auth(401, "thiếu hoặc sai khóa (header X-Lacviet-Key)")
            return True   # chưa đặt khóa: mở (required chỉ còn ý nghĩa khi bật khóa)

        def _send_raw(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        _consumed = False   # đã đọc hết thân yêu cầu chưa

        def _drain(self):
            """Đọc và bỏ phần thân yêu cầu còn lại trước khi trả lỗi.
            Nếu đóng kết nối khi thân còn trong bộ đệm, Windows gửi RST và phía client thấy 'connection aborted'
            thay vì nhận được mã 4xx."""
            if self._consumed or self.command not in ("POST", "PUT", "DELETE", "PATCH"):
                return
            self._consumed = True
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self.close_connection = True
                return
            cap = max(MAX_BODY, MAX_AUDIO)
            if n > cap:
                self.close_connection = True   # quá lớn để đọc: báo đóng kết nối, không đọc tiếp
                return
            left = max(n, 0)
            while left > 0:
                chunk = self.rfile.read(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)

        def _send(self, code, obj):
            self._drain()
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            if self.close_connection:
                self.send_header("Connection", "close")
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
                raise ValueError("nội dung quá lớn")   # chưa đọc: _send sẽ đọc bỏ (hoặc đóng kết nối nếu quá lớn)
            raw = self.rfile.read(n)
            self._consumed = True
            b = json.loads(raw or b"{}")
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
            u = self._url()
            if u.path in ("/health", "/", "/index.html"):
                return True
            # Mọi API khác đi qua khóa khi đã đặt LICHVIET_API_KEY; chưa đặt thì mở.
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self._auth(required=False, q=q, ics_ok=u.path.endswith("/calendar.ics"))

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
            except CursorTooOld as e:
                self._send(410, {"error": str(e), "action": "resync", "since": "0"})
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
                                        "user_id": USER_ID,
                                        "features": ["changes", "upcoming", "devices", "delivered", "ics", "event_update", "event_check",
                                                     "repeat_yearly", "skip_acked", "skip_delivered"],
                                        "auth": {"header": "X-Lacviet-Key", "configured": bool(api_key)},
                                        "now_iso": svc.clock().replace(tzinfo=get_tz()).isoformat(timespec="seconds"),
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
                return self._run(lambda: [with_iso(e) for e in svc.list_range(
                    datetime.fromisoformat(q["from"]), datetime.fromisoformat(q["to"]))])
            if u.path == "/ai/status":
                return self._run(svc.llm.status)
            if u.path == "/reminders/due":
                if not self._auth(required=False):
                    return
                return self._run(lambda: [{**with_iso(d), "fire_at_iso": with_iso({"start": d["fire_at"]})["start_iso"],
                                           "user_id": USER_ID}
                                          for d in svc.due_reminders(q.get("channel", ""), q.get("device_id") or None,
                                                     _flag(q.get("skip_delivered")))])
            if u.path == "/reminders/upcoming":
                if not self._auth(required=True):
                    return
                return self._run(lambda: [{**with_iso(d), "fire_at_iso": with_iso({"start": d["fire_at"]})["start_iso"],
                                           "user_id": USER_ID}
                                          for d in svc.upcoming_reminders(int(q.get("days", 14)), q.get("device_id") or None,
                                                         _flag(q.get("skip_acked")))])
            if u.path == "/events/changes":
                if not self._auth(required=True):
                    return

                def go():
                    res = svc.changes_since(int(q.get("since", 0) or 0), int(q.get("limit", 200)))
                    for c in res["changes"]:
                        if c["op"] == "upsert":
                            c["event"] = with_iso(c["event"])
                    return {**res, "user_id": USER_ID}
                return self._run(go)
            if u.path == "/devices":
                if not self._auth(required=True):
                    return
                return self._run(svc.list_devices)
            if u.path == "/calendar.ics":
                if not self._auth(required=True, q=q, ics_ok=True):
                    return
                try:
                    now = svc.clock()
                    lo = datetime.fromisoformat(q["from"]) if q.get("from") else now - timedelta(days=7)
                    hi = datetime.fromisoformat(q["to"]) if q.get("to") else now + timedelta(days=365)
                    if hi <= lo or (hi - lo).days > 800:
                        raise ValueError("khoảng thời gian không hợp lệ (to sau from, tối đa 800 ngày)")
                    body = ics.render(svc.calendar_items(lo, hi), now, get_tz()).encode("utf-8")
                except ValueError as e:
                    return self._send(400, {"error": str(e)})
                return self._send_raw(200, body, "text/calendar; charset=utf-8")
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
                self._consumed = True
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
                    return svc.create(**_event_fields(self._body()))
                return self._run(go)
            if u.path == "/events/check":   # cảnh báo trùng giờ cho form Sửa: chỉ đọc, không chặn
                def go():
                    b = self._body()
                    start = datetime.fromisoformat(b["start"])
                    dur = b.get("duration_min")
                    if dur is not None and (isinstance(dur, bool) or not isinstance(dur, int) or dur < 1):
                        raise ValueError("duration_min phải là số nguyên dương hoặc null")
                    ex = b.get("exclude_id")
                    if ex is not None and (isinstance(ex, bool) or not isinstance(ex, int)):
                        raise ValueError("exclude_id phải là số nguyên")
                    if b.get("all_day"):
                        return {"conflicts": []}
                    return {"conflicts": [with_iso(c) for c in svc.conflicts(start, dur, ex)]}
                return self._run(go)
            if u.path == "/reminders/ack":
                def go():
                    b = self._body()
                    svc.ack(b["event_id"], b["occurrence"])
                    return {"ok": True}
                return self._run(go)
            if u.path == "/devices":
                if not self._auth(required=True):
                    return
                def go():
                    b = self._body()
                    return svc.register_device(b["device_id"], b["platform"], b.get("label"))
                return self._run(go)
            if u.path == "/reminders/delivered":
                if not self._auth(required=True):
                    return
                def go():
                    b = self._body()
                    svc.mark_delivered(b["device_id"], b["event_id"], b["key"])
                    return {"ok": True}
                return self._run(go)
            if u.path == "/reminders/fired":
                if not self._auth(required=False):
                    return
                def go():
                    b = self._body()
                    svc.mark_fired(b["event_id"], b["occurrence"])
                    return {"ok": True}
                return self._run(go)
            self._send(404, {"error": "không có đường dẫn này"})

        def do_PATCH(self):
            if not self._guard():
                return
            u = self._url()
            if u.path.startswith("/events/") and u.path.count("/") == 2:
                def go():
                    eid = int(u.path.rsplit("/", 1)[1])
                    b = _event_fields(self._body())
                    if "lunar" in b:   # [ngày, tháng] hoặc null (bỏ ngày âm)
                        ld, lm = b.pop("lunar") or (None, None)
                        b["lunar_day"], b["lunar_month"] = ld, lm
                    return with_iso(svc.update(eid, **b))
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
            if u.path.startswith("/devices/"):
                if not self._auth(required=True):
                    return
                return self._run(lambda: {"deleted": svc.remove_device(unquote(u.path.split("/", 2)[2]))})
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
