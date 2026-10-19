# LicSoLo API v1 (hợp đồng cho hệ sinh thái Lạc Việt)

Mọi đường dẫn dùng được cả có và không có tiền tố `/v1`. Nội dung JSON, UTF-8. App chỉ lưu và tính mốc nhắc;
**gửi thông báo là việc của hệ sinh thái**.

## Xác thực

| Cấu hình | Hành vi |
|---|---|
| `LICHVIET_API_KEY` (≥16 ký tự) | Gửi khóa bằng header `X-Lacviet-Key: <khóa>` hoặc `Authorization: Bearer <khóa>`. Sai/thiếu: `401`. |
| không đặt khóa | Chế độ cục bộ như bản trước: endpoint cũ mở. **Endpoint mới (đánh dấu 🔒) trả `503`**, không bao giờ mở mặc định. |
| `LICHVIET_ICS_KEY` (≥16 ký tự, tùy chọn) | Khóa riêng chỉ đọc, chỉ mở `GET /v1/calendar.ics?key=...` để đăng ký lịch qua URL. Không mở endpoint nào khác. |

Giao diện web trong máy dùng `?channel=ui` và các endpoint của nó, không cần khóa. Khóa so sánh thời gian cố định;
sai khóa bị làm chậm 0,3 giây. Cổng của hệ sinh thái phải đứng trước app, không đưa cổng 18763 ra mạng.
Yêu cầu từ trang web khác (Origin khác Host, `Sec-Fetch-Site: cross-site`) và Host là tên miền có dấu chấm bị từ chối
(`403`); host của cổng đặt trong `LICHVIET_ALLOWED_HOSTS`.

## Định dạng chung

- Giờ không kèm múi giờ (`start`, `occurrence`, `fire_at`) là **giờ địa phương theo `tz`** (`GET /v1/info`).
  Mỗi trường có bản `*_iso` kèm độ lệch (ví dụ `2026-10-20T09:00:00+07:00`): dùng bản này khi cần so sánh.
- Lỗi: `{"error": "..."}` với `400` (dữ liệu sai/thiếu trường), `401`, `403`, `404`, `410`, `503`, `500`.

## Nhắc việc

**`GET /v1/reminders/due`** các lần nhắc đã đến giờ mà chưa gửi (tham số: `device_id`, `channel=ui`).
Kênh mặc định dành cho notifier: sau khi gửi, gọi `POST /v1/reminders/fired`.

**`GET /v1/reminders/upcoming?days=14&device_id=`** 🔒 các mốc nhắc **sắp tới** (tối đa 60 ngày, 500 mốc, sắp theo `fire_at`)
để điện thoại tự hẹn thông báo cục bộ. iOS chỉ giữ ~64 thông báo chờ: lấy mốc gần nhất trước.

Mỗi phần tử:

| Trường | Ý nghĩa |
|---|---|
| `ref` | Mã ổn định của **một mốc nhắc** (`lv-<id>-<yyyymmddHHMM>[-7d\|-1d]`). Dùng làm id thông báo; hẹn lại cùng `ref` thì ghi đè, không trùng. |
| `event_ref` | Mã của việc (`lv-<id>`), để mở đúng việc khi khách bấm thông báo. |
| `event_id`, `key` | Truyền lại khi báo đã gửi/hiển thị. |
| `title`, `notes` (≤200 ký tự) | Nội dung hiển thị. |
| `occurrence`, `fire_at` (+ `_iso`) | Giờ diễn ra và giờ cần nhắc. |
| `kind` | `on_time`, `prepare_7d`, `prepare_1d` (giỗ nhắc trước 7 ngày và 1 ngày). |
| `all_day`, `repeat`, `remind_before_min`, `days_left`, `user_id` | Như tên gọi. Việc cả ngày nhắc lúc 08:00. |

**`POST /v1/reminders/fired`** `{"event_id", "occurrence": <key>}`: notifier đã gửi. Idempotent.
**`POST /v1/reminders/delivered`** 🔒 `{"device_id", "event_id", "key"}`: thiết bị đã hiển thị. Idempotent.
Ba trạng thái "đã nhắc" (`fired` của notifier, `delivered` theo từng thiết bị, `ack` của giao diện) **độc lập**,
không chặn nhau. Sửa một việc xóa các trạng thái đã nhắc của việc đó.

Nhắc bù: việc một lần và giỗ được nhắc bù tới `LICHVIET_CATCHUP_DAYS` (mặc định 7) ngày khi máy từng tắt; việc lặp
ngày/tuần/tháng chỉ nhìn lùi 1 ngày. Việc **lưu với giờ đã qua** không bị nhắc.

## Thiết bị 🔒

`POST /v1/devices` `{"device_id": "[A-Za-z0-9_-]{1,64}", "platform": "ios|android|other", "label"?}` (đăng ký lại = cập nhật),
`GET /v1/devices`, `DELETE /v1/devices/<device_id>` (xóa luôn các `delivered` của thiết bị). Tối đa 20 thiết bị.
LicSoLo **không lưu token push**: token FCM/APNs do hệ sinh thái giữ.

## Đồng bộ tăng dần 🔒

`GET /v1/events/changes?since=<cursor>&limit=200` (`since=0` hoặc bỏ trống = toàn bộ việc hiện có).

```json
{"cursor": "42", "has_more": false, "user_id": "default",
 "changes": [{"seq": 41, "op": "upsert", "event": {"id": 7, "title": "...", "start": "...", "start_iso": "...", "repeat": null, "...": "..."}},
             {"seq": 42, "op": "delete", "event_id": 3}]}
```

- Mỗi việc chỉ xuất hiện một lần, ở trạng thái mới nhất. `delete` là bia mộ: gỡ sự kiện lịch tương ứng.
- `has_more=true`: gọi tiếp ngay với `cursor` vừa nhận. Hết thì lưu `cursor` cho lần sau.
- Bia mộ giữ `LICHVIET_TOMBSTONE_DAYS` ngày (mặc định 90). Con trỏ cũ hơn: `410 {"action":"resync","since":"0"}`:
  tải lại từ `since=0` và thay toàn bộ dữ liệu đang giữ.
- Bản nâng cấp từ trước khi có nhật ký coi mọi việc hiện có là `upsert` nên lần đồng bộ đầu thấy đủ.
- `event` là việc gốc (lặp âm lịch giữ `repeat` + `lunar_day`/`lunar_month`); muốn các lần đã trải ngày dùng `GET /v1/events`.

## Lịch .ics 🔒

`GET /v1/calendar.ics?from=&to=` (mặc định từ 7 ngày trước đến 365 ngày sau, tối đa 800 ngày), `text/calendar`.
Khóa qua header hoặc `?key=<LICHVIET_ICS_KEY>`. Mỗi lần xảy ra là một `VEVENT` riêng (lặp âm lịch không có chuẩn RRULE),
giờ UTC (`Z`), việc cả ngày dùng `VALUE=DATE`, nhắc là `VALARM` với `TRIGGER` tuyệt đối. `UID` ổn định:
`lv-<id>-<yyyymmddHHMM>@lichviet`. Đồng bộ **một chiều** từ LicSoLo sang lịch điện thoại; không ghi ngược.
URL có `?key=` có thể lọt vào nhật ký của proxy: dùng `LICHVIET_ICS_KEY` riêng và xoay khi nghi ngờ lộ.

## Khác

`GET /v1/info` (`api`, `tz`, `user_id`, `now_iso`, `features`, `auth.configured`), `GET /v1/events?from=&to=` (các lần xảy ra đã
trải ngày, có `*_iso`), `GET /v1/export` / `POST /v1/import` (sao lưu JSON, nhập hoàn tác toàn bộ nếu lỗi, có `tz`),
`POST /v1/parse` (hiểu câu tiếng Việt), `GET /health` (không cần khóa).
