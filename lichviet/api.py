import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from .service import Service
from .ui import PAGE
from .lunar import solar_to_lunar
from .tz import get_tz

API_VERSION = 1

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

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def _run(self, fn):
            try:
                self._send(200, fn())
            except KeyError:
                self._send(404, {"error": "không tìm thấy"})
            except (ValueError, json.JSONDecodeError) as e:
                self._send(400, {"error": str(e)})

        def do_GET(self):
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
            u = self._url()
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
                    b["start"] = datetime.fromisoformat(b["start"])
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
            u = self._url()
            if u.path.startswith("/phrases/"):
                return self._run(lambda: {"deleted": svc.forget_phrase(unquote(u.path.split("/", 2)[2]))})
            if u.path.startswith("/events/"):
                return self._run(lambda: {"deleted": svc.delete(int(u.path.rsplit("/", 1)[1]))})
            self._send(404, {"error": "không có đường dẫn này"})

        def log_message(self, *a):
            pass
    return H


def serve(db_path="lichviet.db", host="127.0.0.1", port=8765):
    ThreadingHTTPServer((host, port), make_handler(Service(db_path))).serve_forever()
