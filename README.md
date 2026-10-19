# LicSoLo — Trợ lý thời gian (lịch + nhắc việc, tiếng Việt)

Ứng dụng quản lý lịch và nhắc việc bằng tiếng Việt, có hiển thị âm lịch và trợ lý AI tùy chọn. Viết bằng Python thuần (package `lichviet`, chỉ dùng thư viện chuẩn, lưu bằng SQLite). Đóng gói Docker và chạy trong Pi Desktop.

## Chạy thử bằng Docker
Build image cục bộ:

    docker build -t lichviet:test .

Chạy, dữ liệu lưu trong thư mục `data/` cạnh file compose:

    docker run --rm -p 127.0.0.1:18763:8080 -v "$PWD/data:/data" lichviet:test

Mở http://127.0.0.1:18763. Kiểm tra sức khỏe: `GET /health`.

Cổng trên máy chủ là `PANEL_PORT` (mặc định `18763`), chỉ đổi khi cổng đó đang bị dùng: `PANEL_PORT=18764 docker compose up -d`. Trong `solohost/docker-compose.yml` cổng này được đọc từ `${PANEL_PORT:-18763}`.

Trên Pi Desktop không build, chỉ kéo image có sẵn từ GitHub Container Registry, dùng `solohost/docker-compose.yml` và `solohost/config_options.yml`.

## Cấu hình AI (tùy chọn)
Các biến được đặt trong `config_options.yml` và truyền qua compose:

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

`AI_TIER`, `AI_MEMORY`, `AI_THREADS` chỉ hiện trong form cài đặt khi `AI_MODE` tương ứng.

## Nhập bằng giọng nói

Nhập bằng giọng nói chạy hoàn toàn trên máy, không gửi âm thanh ra ngoài. Service `stt` dùng whisper (image `ghcr.io/dacle7/licsolo-stt`). App gọi nó qua `LICHVIET_STT_URL`.

- Bật qua mục **Tính năng nâng cao** trong form cài đặt, chọn "Nhập bằng giọng nói" hoặc "Cả giọng nói và Trợ lý AI".
- **Lần đầu chạy** service tải mô hình whisper `turbo` (khoảng 1,6 GB) vào volume `lichviet-stt`. Cần mạng trong lần này. Các lần sau dùng bản đã tải. Mô hình cố định `turbo` trong compose (biến `STT_MODEL`).

## Múi giờ
Đặt `LICHVIET_TZ` (mặc định `Asia/Ho_Chi_Minh`), ví dụ `Asia/Bangkok`. Giờ hiển thị theo múi giờ này, không theo giờ của máy chủ (UTC).

## Sao lưu/khôi phục
Dữ liệu (việc, lần nhắc đã gửi, cụm từ đã học) nằm trong `/data` của container, trên Pi Desktop là thư mục `./data` cạnh compose. Xóa thư mục đó là mất dữ liệu, nên hãy sao lưu định kỳ:

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

Thời gian trả về là giờ địa phương theo `LICHVIET_TZ`, không kèm độ lệch múi giờ.

## Nhắc việc và bảo vệ API

- Việc **lưu với giờ đã qua** được cảnh báo ở bản nháp và **không** bị nhắc ngay. Một việc chỉ được nhắc nếu được tạo trước mốc nhắc.
- Nhắc bù khi máy từng tắt: việc một lần và giỗ được nhắc bù trong `LICHVIET_CATCHUP_DAYS` ngày (mặc định 7); việc lặp ngày/tuần/tháng chỉ nhìn lùi 1 ngày.
- API từ chối yêu cầu từ trang web khác (Origin khác Host, `Sec-Fetch-Site: cross-site`) và Host là tên miền có dấu chấm (chống DNS rebinding). Host `localhost`, `127.0.0.1`, `::1` và tên không có dấu chấm (tên service Docker) được phép. App khác gọi bằng host khác thì thêm vào `LICHVIET_ALLOWED_HOSTS` (cách nhau dấu phẩy). `/health` luôn mở.
- Nội dung JSON tối đa 10 MB.

## Tích hợp hệ sinh thái

Hợp đồng API (khóa `X-Lacviet-Key`, nhắc có `ref`, mốc sắp tới cho thông báo cục bộ, thiết bị, đồng bộ tăng dần,
lịch `.ics`): xem [docs/API.md](docs/API.md). Khóa do cổng hệ sinh thái cấp qua `LICHVIET_API_KEY` trong `.env`.

## Lặp theo âm lịch hằng tháng

Nói "cúng rằm mỗi tháng", "ăn chay mùng 1 hàng tháng" hoặc "ngày 15 âm lịch mỗi tháng" sẽ tạo việc `lunar_monthly` (rằm = ngày 15 âm). Tháng thiếu không có ngày 30 thì dùng ngày 29; tháng nhuận bị bỏ qua. Một câu chỉ nói được một ngày âm: "mùng 1 và rằm" phải tạo thành hai việc.

## Nhắc việc: hai kênh độc lập

- `GET /v1/reminders/due` (mặc định) và `POST /v1/reminders/fired`: dành cho notifier của hệ sinh thái.
- `GET /v1/reminders/due?channel=ui` và `POST /v1/reminders/ack`: banner "Đã biết" trong giao diện. Bấm "Đã biết" **không** làm mất thông báo notifier phải gửi, và ngược lại.
- Mỗi lần nhắc trả thêm `user_id` (đặt bằng `LICHVIET_USER_ID`) và `occurrence_iso` kèm độ lệch múi giờ (ví dụ `+07:00`). `/v1/events` có `start_iso`/`occurrence_iso`; `/v1/info` có `user_id`, `now_iso`. Các trường cũ không đổi.
- Múi giờ đặt bằng `LICHVIET_TZ` (compose đọc từ `.env`). Tệp sao lưu ghi `tz`; nhập sang máy khác múi giờ thì kết quả có `tz_warning` (giờ giữ nguyên số).

## Vận hành AI

- Hạ bậc model khi AI quá chậm là **tạm thời**: sau `AI_RETRY_DAYS` ngày (mặc định 7) không bị xin hạ thêm, container llm tự khởi động lại và thử bậc cao hơn.
- Muốn cố định image llama.cpp, đặt `LLM_IMAGE=ghcr.io/ggml-org/llama.cpp@sha256:<digest>` trong `.env` (lấy digest bằng `docker pull` rồi `docker inspect`). Mặc định vẫn là tag `server` trôi theo bản mới.
- Workflow publish chạy test trước; test lỗi thì không đẩy image.

## Chạy test
    python -m unittest discover -s tests

## Phát hành bản mới
Đẩy một tag dạng `v*` (ví dụ `v0.1.0`). GitHub Actions build và đẩy image lên `ghcr.io/dacle7/licsolo:<tag>`. Sau đó cập nhật dòng `image:` trong compose trên Pi Desktop.

    git tag v0.1.0
    git push origin v0.1.0

## Ranh giới
- Lõi **không gửi** thông báo. Ứng dụng gọi `due_reminders()`, gửi qua kênh có sẵn, rồi gọi `mark_fired()`.
- Câu lệnh tiếng Việt qua `from_text(text)` trả về **bản nháp** (có cảnh báo trùng lịch). Chỉ lưu khi gọi `save=True` sau khi người dùng xác nhận.
- AI chỉ tách câu và diễn đạt lại kết quả. Quy đổi ngày giờ vẫn do `parse_vi`.
