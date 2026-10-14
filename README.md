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
| `AI_MODE` | `off` / `on` | Bật trợ lý AI. Mặc định `off`. |
| `AI_TIER` | `auto`, `tiny`, `light`, `medium`, `large`, `xlarge` | Cỡ model. `auto` chọn theo máy. |
| `AI_MEMORY` | `4g` … `96g` | Bộ nhớ dành cho model. |
| `AI_THREADS` | `auto`, `4`, `8`, `16`, `24` | Số luồng CPU cho model. |

Khi bật AI, compose chạy thêm service `llm` (profile `ai`).

## Múi giờ
Đặt `LICHVIET_TZ` (mặc định `Asia/Ho_Chi_Minh`), ví dụ `Asia/Bangkok`. Giờ hiển thị theo múi giờ này, không theo giờ của máy chủ (UTC).

## Sao lưu/khôi phục
Dữ liệu (việc, lần nhắc đã gửi, cụm từ đã học) nằm trong `/data` của container, trên Pi Desktop là thư mục `./data` cạnh compose. Xóa thư mục đó là mất dữ liệu, nên hãy sao lưu định kỳ:

    curl -s http://127.0.0.1:18763/v1/export > sao-luu.json
    curl -s -X POST http://127.0.0.1:18763/v1/import -H "Content-Type: application/json" --data-binary @sao-luu.json

- `export` trả về JSON có `"format": "lichviet-backup"`.
- `import` **gộp thêm, không xóa gì**. Việc trùng (cùng tên, cùng giờ, cùng kiểu lặp) bị bỏ qua, nên nhập hai lần thì lần hai `added` = 0.
- Việc đã nhắc xong trong tệp được giữ trạng thái đã nhắc, không nhắc lại sau khi nhập.
- Tệp sai định dạng bị từ chối với lỗi 400, không nhập gì.

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
