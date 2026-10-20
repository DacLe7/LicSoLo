"""Cài app lên máy (PWA): manifest, biểu tượng, service worker.

Biểu tượng PNG được vẽ bằng mã lúc chạy (chỉ dùng thư viện chuẩn) nên kho mã không chứa tệp nhị phân.
Service worker không lưu dữ liệu người dùng: chỉ hiện trang báo "app chưa chạy" khi mất kết nối,
và xử lý bấm vào thông báo nhắc việc (mở app hoặc bấm "Đã biết").
Các tệp ở đây không chứa dữ liệu người dùng nên được phục vụ không cần khóa (như trang giao diện).
"""
import json
import struct
import zlib
from functools import lru_cache

from . import __version__

INK = (20, 35, 31)        # --ink
PAPER = (248, 244, 236)
GOLD = (245, 194, 107)    # --gold
ACC = (194, 65, 12)       # --acc

MANIFEST = json.dumps({
    "name": "Trợ lý thời gian",
    "short_name": "Lịch Việt",
    "description": "Lịch âm dương và nhắc việc bằng tiếng Việt, chạy trên máy của bạn.",
    "lang": "vi",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f3f1ec",
    "theme_color": "#14231f",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
    ],
}, ensure_ascii=False)

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="22" fill="#14231f"/>
<rect x="20" y="26" width="60" height="54" rx="6" fill="#f8f4ec"/>
<rect x="20" y="26" width="60" height="14" rx="6" fill="#f5c26b"/><rect x="20" y="34" width="60" height="6" fill="#f5c26b"/>
<rect x="33.5" y="18" width="5" height="14" rx="2.5" fill="#14231f"/><rect x="61.5" y="18" width="5" height="14" rx="2.5" fill="#14231f"/>
<circle cx="50" cy="60" r="9" fill="#c2410c"/></svg>"""

SW = """/* Lịch Việt %s: service worker. Không lưu dữ liệu, chỉ trang báo khi app chưa chạy và xử lý thông báo nhắc. */
const OFFLINE=`<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trợ lý thời gian</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f1ec;color:#1d1b18;
font:16px/1.6 "Segoe UI",system-ui,sans-serif;padding:24px;box-sizing:border-box}main{max-width:420px;text-align:center}
h1{font-size:20px}button{border:0;border-radius:12px;padding:12px 24px;font:inherit;font-weight:600;background:#14231f;color:#fff;cursor:pointer;min-height:44px}</style>
</head><body><main><h1>App chưa chạy</h1><p>Không nối được với trợ lý thời gian. Mở Pi Desktop, kiểm tra app đang chạy rồi bấm Thử lại.</p>
<button type="button" onclick="location.reload()">Thử lại</button></main></body></html>`;
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  if(e.request.mode!=='navigate')return;   /* API và tệp khác đi thẳng tới app, không lưu đệm */
  e.respondWith(fetch(e.request).catch(()=>new Response(OFFLINE,{headers:{'Content-Type':'text/html; charset=utf-8'}})));
});
const tell=m=>self.clients.matchAll({type:'window'}).then(l=>l.forEach(c=>c.postMessage(m)));
self.addEventListener('notificationclick',e=>{
  const n=e.notification,d=n.data||{};n.close();
  if(e.action==='ack'&&d.event_id){
    e.waitUntil(fetch('/reminders/ack',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({event_id:d.event_id,occurrence:d.key})}).then(()=>tell('due')).catch(()=>{}));
    return;
  }
  e.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(l=>{
    for(const c of l){if('focus' in c)return c.focus();}
    return self.clients.openWindow('/');
  }));
});
""" % __version__


def _in_rrect(x, y, x0, y0, x1, y1, r):
    if not (x0 <= x < x1 and y0 <= y < y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _color(u: float, v: float, maskable: bool):
    """Màu tại tọa độ (u, v) trong [0, 1). Giống ICON_SVG; bản maskable phủ kín nền để hệ điều hành tự cắt."""
    if not maskable and not _in_rrect(u, v, 0, 0, 1, 1, .22):
        return None   # trong suốt
    for x0 in (.335, .615):   # hai khoen treo lịch
        if _in_rrect(u, v, x0, .18, x0 + .05, .32, .025):
            return INK
    if _in_rrect(u, v, .2, .26, .8, .8, .06):
        if (u - .5) ** 2 + (v - .6) ** 2 <= .09 ** 2:
            return ACC
        return GOLD if v < .4 else PAPER
    return INK


@lru_cache(maxsize=4)
def icon_png(size: int, maskable: bool = False) -> bytes:
    """Biểu tượng PNG (RGBA nếu có góc trong suốt), khử răng cưa bằng 4 điểm lấy mẫu mỗi điểm ảnh."""
    offs = (.25, .75)
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            acc = [0, 0, 0, 0]
            for oy in offs:
                for ox in offs:
                    c = _color((x + ox) / size, (y + oy) / size, maskable)
                    if c:
                        acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; acc[3] += 1
            n = acc[3]
            row += [acc[0] // n, acc[1] // n, acc[2] // n, n * 255 // 4] if n else [0, 0, 0, 0]
        rows.append(row)
    return _png_rgba(size, size, rows)


def _png_rgba(w: int, h: int, rows) -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# đường dẫn -> (hàm tạo nội dung, Content-Type)
FILES = {
    "/manifest.webmanifest": (lambda: MANIFEST.encode("utf-8"), "application/manifest+json; charset=utf-8"),
    "/sw.js": (lambda: SW.encode("utf-8"), "text/javascript; charset=utf-8"),
    "/icon.svg": (lambda: ICON_SVG.encode("utf-8"), "image/svg+xml"),
    "/icon-192.png": (lambda: icon_png(192), "image/png"),
    "/icon-512.png": (lambda: icon_png(512), "image/png"),
    "/icon-maskable-512.png": (lambda: icon_png(512, True), "image/png"),
    "/favicon.ico": (lambda: icon_png(48), "image/png"),
}
