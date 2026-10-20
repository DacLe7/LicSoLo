# Dùng thử trên điện thoại Android — so sánh các cách

Tài liệu này dành cho chủ dự án và người muốn **demo app (với mô hình thật) từ điện thoại Android**. Người dùng
bình thường chỉ cần đọc phần [Khuyến nghị](#khuyến-nghị).

## Bối cảnh

- App chạy trong Pi Desktop trên máy tính, cổng `127.0.0.1:18763` (xem `solohost/docker-compose.yml`). Chỉ chính máy
  đó mở được. Đây là **mặc định cố ý** và không đổi: dữ liệu lịch, giọng nói, câu lệnh không ra mạng.
- Mô hình thật nằm ở máy tính: nhận giọng nói Whisper `turbo` (~1,6 GB, giới hạn 8 GB RAM), AI hiểu câu Qwen3 GGUF
  (1,7B tới 30B tùy RAM). Điện thoại tầm trung không chạy nổi các mô hình này.
- Trình duyệt chỉ cho dùng **micro, service worker (cài app PWA), thông báo hệ thống** trên *trang an toàn*:
  `https://…` hoặc `http://localhost` / `http://127.0.0.1`. Trang `http://192.168.x.x` **không** phải trang an toàn,
  nên mở qua địa chỉ mạng nội bộ thì nút micro, thông báo và cài app đều không hoạt động.
- App chặn tên máy có dấu chấm trong `Host` (chống DNS rebinding). Địa chỉ IP hay tên `*.ts.net` phải được thêm vào
  `LICHVIET_ALLOWED_HOSTS` thì app mới trả lời.
- Giao diện đi kèm được tin theo `Sec-Fetch-Site: same-origin` (`api._is_ui`) **chỉ khi mở trên chính máy này**
  (`127.0.0.1`, `localhost`, kể cả `localhost` qua `adb reverse`). Mở qua tên/IP thêm trong `LICHVIET_ALLOWED_HOSTS`
  và đã đặt `LICHVIET_API_KEY` thì trang hiện ô **"Nhập khóa để mở lịch"**; khóa lưu trong trình duyệt đó.
  Chưa đặt khóa thì **ai mở được trang là dùng được app** (app ghi cảnh báo trong log lúc khởi động).
  Mọi cách cho điện thoại vào app vì vậy phải tự giới hạn *ai* tới được trang.

## Các cách

### 1. Cáp USB + `adb reverse` (khuyến nghị để demo)

Trên máy tính có [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) (vài chục MB):

```
adb reverse tcp:18763 tcp:18763
```

Điện thoại mở `http://localhost:18763`: trình duyệt điện thoại coi đây là `localhost`, cáp USB chuyển thẳng về cổng
`127.0.0.1:18763` của máy tính.

- Được: mô hình thật trên máy tính; **là trang an toàn** nên micro, thông báo, cài app PWA đều chạy; không mở cổng nào ra
  mạng; không cần đổi cấu hình app hay `LICHVIET_ALLOWED_HOSTS` (Host là `localhost`).
- Mất: phải bật *Tùy chọn nhà phát triển → Gỡ lỗi USB*; điện thoại phải cắm cáp; rút cáp hoặc khởi động lại thì
  chạy lại lệnh trên. Thông báo chỉ tới khi app trên điện thoại đang mở và cáp đang cắm.
- Riêng tư: tốt nhất trong các cách dùng mô hình thật. Dữ liệu chỉ đi qua cáp.

### 2. Mạng riêng ảo (Tailscale hoặc tương tự) + HTTPS

Cài Tailscale trên máy tính và điện thoại, rồi trên máy tính: `tailscale serve --bg 18763` (trỏ về
`http://127.0.0.1:18763`). Điện thoại mở `https://<tên-máy>.<tailnet>.ts.net`.

- Cần đặt `LICHVIET_ALLOWED_HOSTS=<tên-máy>.<tailnet>.ts.net` cho service `app` (Host có dấu chấm).
- Được: trang an toàn (HTTPS) nên micro, thông báo, PWA chạy; dùng được ở mọi nơi, không cần cáp; không đổi cổng
  `127.0.0.1` của app (Tailscale chạy trên máy tính và tự chuyển tiếp).
- Mất: phụ thuộc dịch vụ ngoài và tài khoản; máy chủ điều phối của Tailscale biết danh sách thiết bị (không thấy nội dung,
  đường truyền mã hóa đầu cuối). Mọi thiết bị trong tailnet đều mở được app: dùng ACL giới hạn chỉ điện thoại của bạn.
  **Không** dùng `tailscale funnel` (mở ra Internet công khai).

### 3. Mở cổng cho mạng nội bộ (LAN), HTTP thường — không khuyến nghị

Sửa cổng thành `0.0.0.0:18763:8080` và đặt `LICHVIET_ALLOWED_HOSTS=192.168.1.10` (IP máy tính), điện thoại mở
`http://192.168.1.10:18763`.

- Được: dễ, không cần cáp hay dịch vụ ngoài.
- Mất: **không phải trang an toàn** nên micro, thông báo hệ thống, cài app đều tắt (chỉ gõ câu và xem lịch được).
  Lách bằng cờ `chrome://flags/#unsafely-treat-insecure-origin-as-secure` trên điện thoại chỉ nên dùng khi demo.
- Riêng tư: kém nhất. Mọi máy cùng Wi-Fi đều mở được app và đọc/xóa lịch (khóa API không chặn trang, xem Bối cảnh);
  dữ liệu và âm thanh đi trên mạng không mã hóa. Tuyệt đối không làm ở Wi-Fi quán cà phê, công ty, khách sạn.
- Nếu vẫn cần: thêm reverse proxy HTTPS có mật khẩu (ví dụ Caddy với `tls internal` + `basic_auth`) trước cổng
  `127.0.0.1:18763`, cài chứng chỉ gốc của Caddy lên điện thoại. Làm được nhưng nhiều bước, dễ sai.

### 4. Cài app (PWA) lên điện thoại

Không phải một cách kết nối riêng: PWA chỉ là vỏ mở trang của app. Cài được khi điện thoại tới app bằng trang an toàn
(cách 1 hoặc 2). Dữ liệu và mô hình vẫn ở máy tính; máy tính tắt thì PWA hiện "App chưa chạy".

### 5. Mô hình nhỏ chạy ngay trên điện thoại

- Giọng nói: Whisper `tiny`/`base` (75–145 MB) chạy được bằng whisper.cpp trên Android, nhưng tiếng Việt sai nhiều
  (nhất là số, giờ, tên riêng). `small` (~480 MB) khá hơn nhưng chậm trên máy tầm trung.
- Hiểu câu: phần lớn câu được bộ luật (`lichviet/parser.py`, Python thuần) hiểu, không cần AI. Có thể chuyển bộ luật sang
  JavaScript/Kotlin để chạy hẳn trên điện thoại; AI dự phòng dùng Qwen3 0,6B/1,7B (400 MB–2 GB) qua llama.cpp.
- Được: riêng tư tuyệt đối, chạy không cần máy tính.
- Mất: khối lượng làm lớn (app Android riêng hoặc WebAssembly), chất lượng thấp hơn mô hình trên máy tính, tốn pin và bộ nhớ.
  Không phải "demo mô hình thật".
- Không dùng nhận giọng nói có sẵn của trình duyệt (Web Speech API) làm mặc định: trên Chrome Android âm thanh được gửi
  lên máy chủ Google.

## So sánh nhanh

| Cách | Mô hình thật | Micro / thông báo / PWA | Mở ra mạng | Công sức | Riêng tư |
|---|---|---|---|---|---|
| 1. USB + `adb reverse` | Có | Có | Không | Thấp | Rất tốt |
| 2. Tailscale + HTTPS | Có | Có | Chỉ tailnet | Vừa | Tốt (phụ thuộc dịch vụ ngoài) |
| 3. LAN HTTP | Có | Không | Cả Wi-Fi | Thấp | Kém |
| 3b. LAN + proxy HTTPS có mật khẩu | Có | Có | Cả Wi-Fi (có mật khẩu) | Cao | Khá |
| 5. Mô hình trên điện thoại | Không (bản nhỏ) | Có | Không | Rất cao | Rất tốt |

## Khuyến nghị

- **Demo**: cách 1 (cáp USB + `adb reverse`). Không đổi gì trong app.
- **Dùng hằng ngày trên điện thoại**: cách 2, giới hạn ACL chỉ điện thoại của bạn.
- Không mở cổng ra LAN bằng HTTP (cách 3) trừ khi demo ngắn ở mạng nhà tin cậy, xong thì đóng lại.
- Chỉ cần lịch trên điện thoại (không cần nhập): nút tải `.ics` cạnh từng việc, gửi tệp sang điện thoại.

## Đã làm và sẽ làm trong code

Nguyên tắc: chỉ thêm phần nhỏ, **tự bật**, an toàn; không bao giờ đổi mặc định `127.0.0.1`.

- [x] Test khóa mặc định: compose chỉ mở cổng trên `127.0.0.1`; chạy ngoài Docker thì `serve()` và `LICHVIET_HOST`
  mặc định `127.0.0.1` (trong container app nghe `0.0.0.0` là bình thường, cổng ra ngoài do compose quyết định)
  (`tests/test_android_plan.py`). Ai lỡ đổi sẽ làm test đỏ.
- [ ] Hướng dẫn từng bước cách 1 trong `docs/HUONG_DAN.md` (bật gỡ lỗi USB, cài platform-tools, chạy lệnh).
- [x] Khi truy cập qua tên ngoài danh sách máy này (Host nằm trong `LICHVIET_ALLOWED_HOSTS`) và đã đặt
  `LICHVIET_API_KEY`: giao diện cũng phải nhập khóa (lưu trong trình duyệt), không tin `same-origin` nữa
  (`api.host_is_local`, ô nhập khóa trong trang, tải tệp sao lưu/.ics kèm khóa; `tests/test_remote_key.py`).
  Mở thêm địa chỉ mà chưa đặt khóa: log cảnh báo lúc khởi động.
- [ ] Trong mục "Thông báo và cài app": khi trang không phải trang an toàn, giải thích vì sao micro/thông báo tắt
  và trỏ tới cách 1/2 thay vì chỉ ẩn nút.
