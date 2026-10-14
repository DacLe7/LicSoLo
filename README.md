# LicSoLo — Trợ lý thời gian (lịch + nhắc việc, tiếng Việt)

Ứng dụng quản lý lịch và nhắc việc bằng tiếng Việt, có hiển thị âm lịch và trợ lý AI tùy chọn. Viết bằng Python thuần (package `lichviet`, chỉ dùng thư viện chuẩn, lưu bằng SQLite). Đóng gói Docker và chạy trong Pi Desktop.

## Chạy thử bằng Docker
Build image cục bộ:

    docker build -t lichviet:test .

Chạy, dữ liệu lưu trong thư mục `data/` cạnh file compose:

    docker run --rm -p 127.0.0.1:18763:8080 -v "$PWD/data:/data" lichviet:test

Mở http://127.0.0.1:18763. Kiểm tra sức khỏe: `GET /health`.

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
