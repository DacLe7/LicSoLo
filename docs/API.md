# LicSoLo API v1 (hợp đồng cho hệ sinh thái Lạc Việt)

Mọi đường dẫn dùng được cả có và không có tiền tố `/v1`. Lỗi từ chối (401/403) luôn đọc hết thân yêu cầu trước khi trả, nên client không bị rớt kết nối. Nội dung JSON, UTF-8. App chỉ lưu và tính mốc nhắc;
**gửi thông báo là việc của hệ sinh thái**.

## Xác thực

| Cấu hình | Hành vi |
|---|---|
| `LICHVIET_API_KEY` (≥16 ký tự) | **Mọi API** (trừ `/health` và giao diện đi kèm) phải gửi khóa: header `X-Lacviet-Key: <khóa>` hoặc `Authorization: Bearer <khóa>`. Sai/thiếu: `401`. |
| không đặt khóa | Khóa là tùy chọn: mọi endpoint mở, như các bản trước. Cổng chỉ nghe `127.0.0.1` và chặn Host/Origin lạ. |
| `LICHVIET_ICS_KEY` (≥16 ký tự, tùy chọn) | Khóa riêng chỉ đọc, chỉ mở `GET /v1/calendar.ics?key=...` để đăng ký lịch qua URL. Không mở endpoint nào khác. |

Giao diện web đi kèm (trang `/` và các lời gọi cùng nguồn gốc từ chính trang đó, nhận biết bằng `Sec-Fetch-Site: same-origin`
hoặc `Origin` trùng `Host`) không cần khóa, vì trình duyệt đã chặn trang web khác. **Cổng hệ sinh thái phải gỡ các header
`Sec-Fetch-*` và `Origin` của client trước khi chuyển tiếp**, nếu không client ngoài có thể giả header để qua khóa.
Khóa so sánh thời gian cố định; sai khóa bị làm chậm 0,3 giây. Không đưa cổng 18763 ra mạng: cổng hệ sinh thái đứng trước app.
Yêu cầu từ trang web khác (Origin khác Host, `Sec-Fetch-Site: cross-site`) và Host là tên miền có dấu chấm bị từ chối
(`403`); host của cổng đặt trong `LICHVIET_ALLOWED_HOSTS`.

## Định dạng chung

- Giờ không kèm múi giờ (`start`, `occurrence`, `fire_at`) là **giờ địa phương theo `tz`** (`GET /v1/info`).
  Mỗi trường có bản `*_iso` kèm độ lệch (ví dụ `2026-10-20T09:00:00+07:00`): dùng bản này khi cần so sánh.
- Lỗi: `{"error": "..."}` với `400` (dữ liệu sai/thiếu trường), `401`, `403`, `404`, `410`, `500`.

## Nhắc việc

**`GET /v1/reminders/due`** các lần nhắc đã đến giờ mà chưa gửi (tham số: `device_id`, `channel=ui`).
Kênh mặc định dành cho notifier: sau khi gửi, gọi `POST /v1/reminders/fired`.

**`GET /v1/reminders/upcoming?days=14&device_id=`** (khóa khi đã đặt LICHVIET_API_KEY) các mốc nhắc **sắp tới** (tối đa 60 ngày, 500 mốc, sắp theo `fire_at`)
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
| `all_day`, `repeat`, `remind_before_min`, `days_left`, `user_id` | Như tên gọi. `repeat` là `null`, `daily`, `weekly`, `monthly`, `yearly` (dương lịch; 29/2 năm không nhuận thành 28/2), `lunar_yearly` hoặc `lunar_monthly`. Việc cả ngày nhắc lúc 08:00. |

**`POST /v1/reminders/fired`** `{"event_id", "occurrence": <key>}`: notifier đã gửi. Idempotent.
**`POST /v1/reminders/delivered`** (khóa khi đã đặt LICHVIET_API_KEY) `{"device_id", "event_id", "key"}`: thiết bị đã hiển thị. Idempotent.
Ba trạng thái "đã nhắc" (`fired` của notifier, `delivered` theo từng thiết bị, `ack` của giao diện) **độc lập**,
không chặn nhau. Sửa một việc xóa các trạng thái đã nhắc của việc đó.

Nhắc bù: việc một lần và giỗ được nhắc bù tới `LICHVIET_CATCHUP_DAYS` (mặc định 7) ngày khi máy từng tắt; việc lặp
ngày/tuần/tháng chỉ nhìn lùi 1 ngày. Việc **lưu với giờ đã qua** không bị nhắc.

## Thiết bị (khóa khi đã đặt LICHVIET_API_KEY)

`POST /v1/devices` `{"device_id": "[A-Za-z0-9_-]{1,64}", "platform": "ios|android|other", "label"?}` (đăng ký lại = cập nhật),
`GET /v1/devices`, `DELETE /v1/devices/<device_id>` (xóa luôn các `delivered` của thiết bị). Tối đa 20 thiết bị.
LicSoLo **không lưu token push**: token FCM/APNs do hệ sinh thái giữ.

## Đồng bộ tăng dần (khóa khi đã đặt LICHVIET_API_KEY)

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

## Lịch .ics (khóa khi đã đặt LICHVIET_API_KEY)

`GET /v1/calendar.ics?from=&to=` (mặc định từ 7 ngày trước đến 365 ngày sau, tối đa 800 ngày), `text/calendar`.
Khóa qua header hoặc `?key=<LICHVIET_ICS_KEY>`. Mỗi lần xảy ra là một `VEVENT` riêng (lặp âm lịch không có chuẩn RRULE),
giờ UTC (`Z`), việc cả ngày dùng `VALUE=DATE`, nhắc là `VALARM` với `TRIGGER` tuyệt đối. `UID` ổn định:
`lv-<id>-<yyyymmddHHMM>@lichviet`. Đồng bộ **một chiều** từ LicSoLo sang lịch điện thoại; không ghi ngược.
URL có `?key=` có thể lọt vào nhật ký của proxy: dùng `LICHVIET_ICS_KEY` riêng và xoay khi nghi ngờ lộ.

## Khác

`GET /v1/info` (`version`, `api`, `tz`, `user_id`, `events` = số việc đã lưu, `now_iso`, `features`, `auth.configured`), `GET /v1/events?from=&to=` (các lần xảy ra đã
trải ngày, có `*_iso`), `GET /v1/export` / `POST /v1/import` (sao lưu JSON, nhập hoàn tác toàn bộ nếu lỗi, có `tz`),
`POST /v1/parse` (hiểu câu tiếng Việt), `PATCH /v1/events/<id>` (sửa việc đã lưu, chỉ gửi trường cần đổi, trả kèm `conflicts`;
`404` nếu không có, `400` nếu dữ liệu sai), `DELETE /v1/events/<id>`,
`POST /v1/events` (tạo việc từ form, trả kèm `conflicts`), `GET /v1/conflicts?start=&duration_min=&exclude=` (việc có giờ trùng,
mặc định dài 60 phút; `exclude` = id việc đang sửa; trả `[{"id", "title", "occurrence"}]`),
`GET /health` (không cần khóa; kiểm tra database đọc/ghi được, trả `{"ok", "version", "db"}`; lỗi database: `503` kèm `error` tiếng Việt).
