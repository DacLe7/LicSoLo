# LicSoLo — Trợ lý thời gian (lịch + nhắc việc, tiếng Việt)

Ứng dụng quản lý lịch và nhắc việc bằng tiếng Việt, có hiển thị âm lịch và trợ lý AI tùy chọn. Viết bằng Python thuần (package `lichviet`, chỉ dùng thư viện chuẩn, lưu bằng SQLite). Đóng gói Docker và chạy trong Pi Desktop (xem [solohost/README.md](solohost/README.md)).

## Chạy thử bằng Docker
Build image cục bộ:

    docker build -t lichviet:test .

Chạy, dữ liệu lưu trong thư mục `data/` cạnh lệnh:

    docker run --rm -p 127.0.0.1:18763:8080 -v "$PWD/data:/data" lichviet:test

Mở http://127.0.0.1:18763. Kiểm tra sức khỏe: `GET /health`.

## Cổng truy cập (PANEL_PORT)
Trên SoloHost, cổng trên máy là `PANEL_PORT` (mặc định `18763`), chỉ nghe `127.0.0.1`. Form cài đặt cho chọn `18763`, `18764`, `18765`, `28763`. Chỉ đổi khi cổng mặc định đang bị chương trình khác dùng.

## Cấu hình AI (tùy chọn)
Các biến được khai báo trong `solohost/config_options.yml`:

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `AI_MODE` | `off` / `voice` / `ai` / `both` | Chọn tính năng bật. Mặc định `off`. |
| `AI_TIER` | `auto`, `tiny`, `light`, `medium`, `large`, `xlarge` | Cỡ model. `auto` chọn theo máy. |
| `AI_MEMORY` | `4g` … `96g` | Bộ nhớ dành cho model. |
| `AI_THREADS` | `auto`, `4`, `8`, `16`, `24` | Số luồng CPU cho model. |

`AI_MODE` ánh xạ sang profile compose:

- `off`: chỉ chạy app. Lịch và nhắc việc vẫn đầy đủ.
- `voice`: thêm service `stt` (profile `voice`).
- `ai`: thêm service `llm` (profile `ai`).
- `both`: thêm cả `stt` và `llm`.

## Nhập bằng giọng nói

Nhập bằng giọng nói chạy hoàn toàn trên máy, không gửi âm thanh ra ngoài. Service `stt` dùng whisper, mô hình cố định `turbo` trong compose.

- Bật qua form cài đặt: chọn "Nhập bằng giọng nói" hoặc "Cả giọng nói và Trợ lý AI".
- Cần trình duyệt có quyền micro. Bấm mic để bắt đầu nói, bấm lại khi nói xong.
- Lần đầu chạy, service tải mô hình `turbo` (khoảng 1,6 GB) vào volume `lichviet-stt`. Cần mạng trong lần này.
- Cần khoảng 4 GB RAM cho service `stt`.
- **Tự học lỗi nghe:** khi bạn sửa một chữ mà máy nhận sai, app ghi lại cặp "nghe sai → sửa đúng" qua `POST /stt/learn`. Khi cùng một cặp được sửa đủ `LICHVIET_LEARN_MIN` lần (mặc định 2), app tự áp dụng cho các lần nhận sau.

## Múi giờ
App đọc `LICHVIET_TZ` (mặc định `Asia/Ho_Chi_Minh`). Giờ hiển thị theo múi giờ này, không theo giờ của máy chủ (UTC). Trên SoloHost, compose cố định `Asia/Ho_Chi_Minh`.

## Sao lưu và khôi phục
Dữ liệu (việc, lần nhắc đã gửi, cụm từ đã học, lỗi nghe đã học) nằm trong `/data` của container. Trên Pi Desktop là thư mục `./data` cạnh compose. Xóa thư mục đó là mất dữ liệu, nên hãy sao lưu định kỳ:

    curl -s http://127.0.0.1:18763/v1/export > sao-luu.json
    curl -s -X POST http://127.0.0.1:18763/v1/import -H "Content-Type: application/json" --data-binary @sao-luu.json

- `export` trả về JSON có `"format": "lichviet-backup"`.
- `import` **gộp thêm, không xóa gì**. Việc trùng (cùng tên, cùng giờ, cùng kiểu lặp) bị bỏ qua, nên nhập hai lần thì lần hai `added` = 0.
- Việc đã nhắc xong trong tệp được giữ trạng thái đã nhắc, không nhắc lại sau khi nhập.
- Tệp lỗi (giữa chừng cũng vậy) bị từ chối với lỗi 400 và **hoàn tác toàn bộ**, không nhập nửa chừng.

## API /v1
Mọi đường dẫn dùng được cả có và không có tiền tố `/v1` (ví dụ `/v1/today` và `/today` trả cùng kết quả). Tiền tố `/v1` là hợp đồng cho các app khác trong hệ sinh thái.

| Phương thức | Đường dẫn | Việc làm |
|---|---|---|
| GET | `/v1/info` | Tên app, phiên bản API, múi giờ, giờ hiện tại |
| GET | `/v1/today` | Ngày dương, âm lịch, năm can chi hôm nay |
| GET | `/v1/events?from=…&to=…` | Liệt kê việc trong khoảng thời gian (ISO 8601) |
| POST | `/v1/parse` | Phân tích câu tiếng Việt, body `{"text": "…", "save": false}` |
| GET | `/v1/export` | Sao lưu toàn bộ dữ liệu |
| POST | `/v1/import` | Khôi phục từ tệp sao lưu (gộp thêm) |
| GET | `/v1/phrases` | Sổ cụm từ đã học |
| DELETE | `/v1/phrases/<cụm>` | Quên một cụm từ đã học |

Thời gian trả về là giờ địa phương theo `LICHVIET_TZ`, không kèm độ lệch múi giờ. Chi tiết đầy đủ: [docs/API.md](docs/API.md).

## Xác thực API

- **Khóa tùy chọn.** `LICHVIET_API_KEY` (≥16 ký tự) bật khóa cho các endpoint cần khóa. Gửi qua header `X-Lacviet-Key: <khóa>` hoặc `Authorization: Bearer <khóa>`. Sai hoặc thiếu: `401`.
- **Không đặt khóa:** các endpoint cũ mở như các bản trước. Các endpoint mới (đồng bộ, thiết bị, mốc nhắc sắp tới, lịch `.ics`) trả `503` `chưa cấu hình LICHVIET_API_KEY`, để không mở mặc định.
- **Trên SoloHost, khóa chưa được nối vào container.** Compose không truyền `LICHVIET_API_KEY`, nên các endpoint cần khóa trả 503. Muốn dùng khóa thật phải thêm biến vào compose và khai báo trong `config_options.yml`.
- `LICHVIET_ICS_KEY` (tùy chọn, ≥16 ký tự) chỉ mở `GET /v1/calendar.ics?key=…` để đăng ký lịch qua URL.
- App từ chối yêu cầu từ trang web khác (Origin khác Host, `Sec-Fetch-Site: cross-site`) và Host là tên miền có dấu chấm (chống DNS rebinding). Host `localhost`, `127.0.0.1`, `::1` và tên không có dấu chấm (tên service Docker) được phép. Host khác thì thêm vào `LICHVIET_ALLOWED_HOSTS` (cách nhau dấu phẩy). Trên SoloHost, biến này chưa được truyền vào container.
- `/health` luôn mở. Nội dung JSON tối đa 10 MB.

## Nhắc việc

- Việc **lưu với giờ đã qua** được cảnh báo ở bản nháp và **không** bị nhắc ngay. Một việc chỉ được nhắc nếu được tạo trước mốc nhắc.
- Nhắc bù khi máy từng tắt: việc một lần và giỗ được nhắc bù trong `LICHVIET_CATCHUP_DAYS` ngày (mặc định 7); việc lặp ngày/tuần/tháng chỉ nhìn lùi 1 ngày.
- `GET /v1/reminders/due` (mặc định) và `POST /v1/reminders/fired`: dành cho notifier của hệ sinh thái.
- `GET /v1/reminders/due?channel=ui` và `POST /v1/reminders/ack`: banner "Đã biết" trong giao diện. Bấm "Đã biết" **không** làm mất thông báo notifier phải gửi, và ngược lại.
- Mỗi lần nhắc trả thêm `user_id` (đặt bằng `LICHVIET_USER_ID`, mặc định `default`) và `occurrence_iso` kèm độ lệch múi giờ.

## Lặp theo âm lịch hằng tháng

Nói "cúng rằm mỗi tháng", "ăn chay mùng 1 hàng tháng" hoặc "ngày 15 âm lịch mỗi tháng" sẽ tạo việc `lunar_monthly` (rằm = ngày 15 âm). Tháng thiếu không có ngày 30 thì dùng ngày 29; tháng nhuận bị bỏ qua. Một câu chỉ nói được một ngày âm: "mùng 1 và rằm" phải tạo thành hai việc.

## Vận hành AI

- Hạ bậc model khi AI quá chậm là **tạm thời**: sau `AI_RETRY_DAYS` ngày (mặc định 7) không bị xin hạ thêm, container llm tự khởi động lại và thử bậc cao hơn. Biến này không nằm trong form cài đặt SoloHost; muốn đổi phải sửa compose.
- Tag `server` của llama.cpp trôi theo bản mới nhất. Trên SoloHost không có biến để ghim digest.

## Lịch âm

Đổi âm - dương dùng múi giờ Việt Nam (UTC+7) với thuật toán thiên văn của Hồ Ngọc Đức, không dùng thư viện lịch Trung Quốc (UTC+8)
vì có năm lệch một ngày so với lịch Việt. Kết quả đã được đối chiếu với tính thiên văn trên 507 tháng, từ năm 2000 đến 2040
(phép đối chiếu này do người phát triển thực hiện; kịch bản đối chiếu chưa nằm trong repo). Việc lặp theo âm lịch (giỗ, `lunar_yearly`, và `lunar_monthly`) bỏ qua tháng nhuận;
tháng thiếu không có ngày 30 thì dùng ngày 29.

## App Android

Thư mục `mobile/` là app Android demo (Capacitor + TypeScript): gõ hoặc nói một việc, xem thẻ "Trợ lý hiểu là", lưu vào LicSoLo.
Việc trong LicSoLo hiện trong lịch hệ thống của điện thoại (lịch riêng "Trợ lý thời gian") và được hẹn thông báo cục bộ,
nên vẫn nhắc đúng giờ khi khóa màn hình hoặc khi máy tính đã tắt. Khi app mở, app đồng bộ mỗi 60 giây và ngay khi mạng nối lại;
khi đóng, một tác vụ nền (~15 phút) hẹn thêm thông báo cho việc mới. Chi tiết và cách build: [`mobile/README.md`](mobile/README.md).

- **Build APK**: workflow `android` (`.github/workflows/android.yml`) chạy khi `mobile/**` đổi hoặc chạy tay (Actions > android > Run workflow);
  APK debug nằm ở mục Artifacts. Bản phát hành gắn APK dùng tag `mobile-v*` (không bắt đầu bằng `v`, nên không chạy workflow đẩy image).
- **URL server** là ô cấu hình trong app (Cài đặt), mặc định `https://d.taila2d06a.ts.net`, không viết cứng trong mã.
- **Demo cần Tailscale và proxy**: điện thoại vào LicSoLo qua Tailscale, trỏ tới `lic_proxy.py` trên Windows (đổi `Host`, gỡ `Origin`/`Sec-Fetch-*`)
  rồi vào app. Đồng bộ cần máy tính bật, app đang chạy và proxy đang mở.
- **Giới hạn**: không có khóa API hay ghép nối (mọi thiết bị trong tailnet đều vào được); đồng bộ một chiều (LicSoLo -> lịch điện thoại);
  chưa có sửa việc đã lưu (xóa rồi tạo lại); không có iOS; APK chưa ký. Ghi lịch hệ thống chỉ làm khi app mở; tác vụ nền chỉ hẹn thêm thông báo.

## Chạy test

    python -m unittest discover -s tests

CI (`.github/workflows/ci.yml`) chạy cùng lệnh này trên mỗi push và pull request.

## Phát hành bản mới

1. Đảm bảo `main` đã xanh (CI chạy test).
2. Tạo và đẩy tag dạng `v*`, ví dụ `v0.5.2`:

       git tag v0.5.2
       git push origin v0.5.2

3. Workflow `publish.yml` chạy test trước; nếu test lỗi thì không đẩy image. Nếu test pass, nó đẩy `ghcr.io/dacle7/licsolo:<phiên bản>` và `latest`. Workflow `publish-stt.yml` đẩy `ghcr.io/dacle7/licsolo-stt:<phiên bản>`.
4. Cập nhật tag `image:` của `app` và `stt` trong `solohost/docker-compose.yml` lên đúng phiên bản đó, rồi kiểm tra kéo được ẩn danh trước khi giao cho Pi Desktop. Compose luôn ghim phiên bản cụ thể, không dùng `latest`.

## Ranh giới
- Lõi **không gửi** thông báo. Ứng dụng gọi `due_reminders()`, gửi qua kênh có sẵn, rồi gọi `mark_fired()`.
- Câu lệnh tiếng Việt qua `from_text(text)` trả về **bản nháp** (có cảnh báo trùng lịch). Chỉ lưu khi gọi `save=True` sau khi người dùng xác nhận.
- AI chỉ tách câu và diễn đạt lại kết quả. Quy đổi ngày giờ vẫn do `parse_vi`.
