# Gói SoloHost (bản nháp, chưa kiểm chứng)

Gồm `docker-compose.yml` và `config_options.yml`. Phía gốc có `Dockerfile` và workflow đẩy image lên GHCR.

## Việc cần làm trước khi nộp
1. **Đẩy image lên registry công khai:** SoloHost chỉ nhận image có sẵn. Tạo repo GitHub, tạo tag `v0.1.0`, workflow `image.yml` sẽ build và đẩy lên `ghcr.io/<tổ chức>/lichviet:v0.1.0`; đặt gói ở chế độ public. Rồi sửa `LACVIET_OWNER` / phiên bản trong compose.
2. **Đã đối chiếu `config_options.yml` với mẫu chính thức** (title, output_file, fields, options.set, visible_if). Không dùng `fixed_values` vì mẫu chỉ có `detect: uid|gid`.
3. **Chưa kiểm chứng:** `COMPOSE_PROFILES` trong `.env` có được SoloHost chấp nhận không; giới hạn `mem_limit`, `cpus` có được giữ không; `-hf` tải mô hình có bị chặn mạng không. Nếu `-hf` bị chặn, đổi sang file mô hình có sẵn trong volume.
4. **Chưa có chỗ gọi API:** app lõi nghe 127.0.0.1:8080; cách app công ty gọi vào cần xác minh.

## Giới hạn đã đặt
App 256 MB / 0,5 CPU. AI mặc định tắt; khi bật: RAM theo lựa chọn (mặc định 4 GB), luồng theo lựa chọn, ưu tiên CPU thấp, một yêu cầu mỗi lần, tự ngắt sau 3 lần lỗi liên tiếp.
