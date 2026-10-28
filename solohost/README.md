# Gói SoloHost (Pi Desktop)

Gồm `docker-compose.yml` và `config_options.yml`. Pi Desktop chỉ kéo image đã phát hành từ GHCR, không build.

## Image đang ghim

| Service | Image | Ghi chú |
|---|---|---|
| `app` | `ghcr.io/dacle7/licsolo:0.5.2` | Lịch, nhắc việc, giao diện, API `/v1` |
| `stt` | `ghcr.io/dacle7/licsolo-stt:0.5.2` | Chỉ chạy khi bật nhập bằng giọng nói (profile `voice`) |
| `llm` | `ghcr.io/ggml-org/llama.cpp:server` | Chỉ chạy khi bật Trợ lý AI (profile `ai`). Tag `server` trôi theo bản mới |

Khi có bản phát hành mới: sửa tag `image:` của `app` và `stt` cùng một phiên bản, rồi `docker compose pull && docker compose up -d`.

## App Android

Kèm theo repo có app Android demo trong `mobile/` (không nằm trong gói SoloHost và không đổi image). App đọc LicSoLo qua API `/v1` của bản `app` đang chạy,
ghi việc vào lịch điện thoại và hẹn thông báo cục bộ. Build APK bằng workflow `android` trên GitHub (Actions > android, tải ở Artifacts); hướng dẫn ở [`mobile/README.md`](../mobile/README.md).

- URL server là ô cấu hình trong app (mặc định `https://d.taila2d06a.ts.net`).
- Demo cần Tailscale và `lic_proxy.py` (proxy đổi `Host`, gỡ `Origin`/`Sec-Fetch-*`) trên máy Windows chạy Pi Desktop.
- Giới hạn: không có khóa API (mọi thiết bị trong tailnet đều vào được), đồng bộ một chiều, chưa có sửa việc đã lưu.

## Cấu hình

`config_options.yml` khai báo các biến Pi Desktop hiển thị trong form cài đặt: `AI_MODE`, `AI_TIER`, `AI_MEMORY`, `AI_THREADS`, `PANEL_PORT`, `UID`. Mọi `${VAR}` trong compose phải có trong danh sách này. Pi Desktop từ chối file nếu có biến không khai báo.

- **Múi giờ** cố định `Asia/Ho_Chi_Minh` trong compose.
- **Giọng nói** cố định mô hình `turbo` (`STT_MODEL: "turbo"`). Không có biến chọn mô hình.
- **Khóa API** (`LICHVIET_API_KEY`) chưa được truyền vào container trên SoloHost. Xem phần xác thực bên dưới.

## Cổng truy cập

Cổng trên máy là `PANEL_PORT`, mặc định `18763`, chỉ nghe `127.0.0.1`. Form cài đặt có các lựa chọn `18763`, `18764`, `18765`, `28763`. Chỉ đổi khi cổng mặc định đang bị dùng.

## Xác thực API

- Không có khóa trên SoloHost: các endpoint cũ mở như các bản trước, còn các endpoint cần khóa (đồng bộ, thiết bị, mốc nhắc sắp tới, `.ics`) trả **503** `chưa cấu hình LICHVIET_API_KEY`.
- App chỉ nghe `127.0.0.1` và chặn Host/Origin lạ. Không đưa cổng này ra mạng.

## Giọng nói

- Lần chạy đầu tiên tải mô hình `turbo` khoảng 1,6 GB vào volume `lichviet-stt`. Cần mạng trong lần này, các lần sau dùng bản đã tải.
- Cần khoảng 4 GB RAM cho service `stt`.
- Trình duyệt cần quyền micro: bấm mic để bắt đầu nói, bấm lại khi nói xong.

## Sao lưu và khôi phục

Dữ liệu nằm trong thư mục `./data` cạnh compose. Xóa thư mục đó là mất dữ liệu.

    curl -s http://127.0.0.1:18763/v1/export > sao-luu.json
    curl -s -X POST http://127.0.0.1:18763/v1/import -H "Content-Type: application/json" --data-binary @sao-luu.json

`import` gộp thêm và không xóa gì. Tệp lỗi bị từ chối với 400 và hoàn tác toàn bộ.
