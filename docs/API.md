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

**`GET /v1/reminders/due`** các lần nhắc đã đến giờ mà chưa gửi (tham số: `device_id`, `channel=ui`, `skip_delivered=1`).
Kênh mặc định dành cho notifier: sau khi gửi, gọi `POST /v1/reminders/fired`.
`skip_delivered=1` (mặc định **tắt**, hành vi cũ không đổi) bỏ thêm các mốc mà **bất kỳ thiết bị nào** đã báo `delivered`;
giao diện web dùng `channel=ui&skip_delivered=1` để máy tính không nhắc lại điều điện thoại đã nhắc.

**`GET /v1/reminders/upcoming?days=14&device_id=&skip_acked=1`** (khóa khi đã đặt LICHVIET_API_KEY) các mốc nhắc **sắp tới** (tối đa 60 ngày, 500 mốc, sắp theo `fire_at`)
để điện thoại tự hẹn thông báo cục bộ. iOS chỉ giữ ~64 thông báo chờ: lấy mốc gần nhất trước.
`device_id` (đã đăng ký, nếu không `400 thiết bị chưa đăng ký`) bỏ các mốc thiết bị đó đã báo `delivered`.
`skip_acked=1` (mặc định **tắt**) bỏ thêm các mốc đã bấm "Đã biết" (`ack`) hoặc đã `fired`.

> **Giới hạn:** `skip_delivered` và `skip_acked` chỉ **giảm trùng giữa các lần đồng bộ** (mốc nào đã được báo thì lần lấy sau không có nữa).
> Chúng **không** chống trùng đúng lúc thông báo nổ: hai thiết bị đã hẹn sẵn cùng một mốc thì cả hai vẫn nổ. Chống trùng đúng lúc cần push
> từ hệ sinh thái; bản này không làm.

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
**`POST /v1/reminders/delivered`** (khóa khi đã đặt LICHVIET_API_KEY) `{"device_id", "event_id", "key"}`: thiết bị đã hiển thị. Idempotent.
Ba trạng thái "đã nhắc" (`fired` của notifier, `delivered` theo từng thiết bị, `ack` của giao diện) **độc lập**,
không chặn nhau. Sửa một việc xóa các trạng thái đã nhắc của việc đó.

Nhắc bù: việc một lần và giỗ được nhắc bù tới `LICHVIET_CATCHUP_DAYS` (mặc định 7) ngày khi máy từng tắt; việc lặp
ngày/tuần/tháng chỉ nhìn lùi 1 ngày. Việc **lưu với giờ đã qua** không bị nhắc.

## Việc: tạo, sửa, xóa, kiểm tra trùng giờ

Trường của một việc (`title, start, duration_min, all_day, repeat, remind_before_min, notes, lunar`); trường lạ bị `400`.
`start` là ISO 8601 (giờ địa phương); `lunar` là mảng `[ngày, tháng]` âm lịch hoặc `null`.

**`POST /v1/events`** tạo việc. Việc trùng (cùng tên không phân biệt hoa thường, cùng `start`, cùng `repeat`) trả việc cũ kèm `duplicate:true`.

**`PATCH /v1/events/<id>`** sửa **một phần**: chỉ gửi các trường cần đổi, cùng cách kiểm tra như `POST`. Trả việc đã cập nhật (có `start_iso`).
Kiểm tra trên trạng thái **sau khi sửa**: `repeat` là `lunar_yearly`/`lunar_monthly` thì phải còn ngày âm; đổi `repeat` sang kiểu dương lịch mà không gửi `lunar` thì
ngày âm cũ bị xóa; `lunar: null` xóa ngày âm; sửa thành trùng một việc khác (cùng tên, giờ, kiểu lặp) thì `400`. Việc không tồn tại: `404`.
Sửa ghi nhật ký đồng bộ (`/events/changes` thấy một `upsert`) và **xóa trạng thái đã nhắc** (`fired`, `ack`, `delivered`) của việc đó. Thân rỗng `{}` chỉ trả việc hiện tại.

**`DELETE /v1/events/<id>`** xóa việc (cả chuỗi lặp) → `{"deleted": true|false}`.

**`POST /v1/events/check`** `{"start", "duration_min"?, "all_day"?, "exclude_id"?}` → `{"conflicts": [...]}`: các lần xảy ra trùng khoảng
`[start, start + duration)` (mặc định 60 phút; chạm đầu mút không tính). Việc cả ngày (`all_day:true`) luôn trả mảng rỗng. `exclude_id` bỏ qua một việc (khi sửa chính nó).
Chỉ đọc, không ghi gì; mỗi phần tử có `occurrence` và `occurrence_iso`. Đây là **cảnh báo**, không chặn việc lưu.

### Kiểu lặp (`repeat`)

| Giá trị | Ý nghĩa |
|---|---|
| `null` | một lần |
| `daily`, `weekly`, `monthly` | mỗi ngày, tuần, tháng (tháng ngắn thì lấy ngày cuối tháng) |
| `yearly` | **hằng năm theo dương lịch** (sinh nhật, kỷ niệm): mỗi năm cùng ngày-tháng và cùng giờ với `start`; không lặp trước `start`. Việc `start` vào **29/2** thì năm không nhuận rơi vào **28/2**, năm nhuận lại 29/2. Chỉ có mốc nhắc `on_time` (không có mốc trước như giỗ). Nhắc bù như việc một lần (`LICHVIET_CATCHUP_DAYS`). |
| `lunar_yearly` | hằng năm theo âm lịch (giỗ), cần `lunar`; có mốc `prepare_7d`, `prepare_1d` |
| `lunar_monthly` | hằng tháng theo âm lịch (rằm, mùng 1), cần ngày âm |

`yearly` có trong sao lưu (`/export`, `/import`), trong `.ics` (mỗi lần xảy ra một `VEVENT`) và trong `/events/changes` như mọi kiểu lặp khác.
Client cũ gặp `repeat:"yearly"` mà không biết thì nên coi như việc lặp bất kỳ; cửa sổ lấy xa (400 ngày) nên áp cho cả `yearly` như giỗ.

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

`GET /v1/info` (`api`, `tz`, `user_id`, `now_iso`, `features`, `auth.configured`; `features` thêm `event_update`, `event_check`, `repeat_yearly`, `skip_acked`, `skip_delivered`
để client biết server có hỗ trợ), `GET /v1/events?from=&to=` (các lần xảy ra đã
trải ngày, có `*_iso`), `GET /v1/export` / `POST /v1/import` (sao lưu JSON, nhập hoàn tác toàn bộ nếu lỗi, có `tz`),
`GET /health` (không cần khóa).

**`POST /v1/parse`** `{"text", "save"?}` hiểu câu tiếng Việt: `status` là `draft` (bản nháp + `conflicts`), `saved` (khi `save:true`) hoặc `need_info` (kèm `missing`: `title`, `start`).
Ngày trong quá khứ hiểu được: `hôm qua`, `hôm kia`, `N ngày trước`, `N tuần trước`, `thứ X tuần trước` (kèm cảnh báo "thời điểm này đã qua, bạn kiểm tra lại ngày giờ").
Câu mơ hồ không xác định được ngày (`bữa hổm`, `hồi trước`, `mấy hôm trước`, `tuần trước` một mình...) **không được đoán**: trả `need_info` với `missing` có `start`,
và không hỏi AI. `sinh nhật`/`kỷ niệm`/`hằng năm`/`mỗi năm` kèm ngày-tháng dương (không có "âm") cho `repeat:"yearly"`; có "âm lịch" thì vẫn là `lunar_yearly`.

### Nhập giọng nói

- **`GET /v1/stt/status`** → `{"enabled", "ready", "model"?, "detail"}`. `enabled:false` khi giọng nói tắt; `ready:false` khi mô hình còn đang tải.
- **`POST /v1/stt`** thân là **WAV 16 kHz mono 16 bit** (`Content-Type: audio/wav`), tối đa 8 MB → `{"text": "..."}`. Chữ đã qua các lỗi nghe đã học (xem `/stt/learn`).
  `400` khi âm thanh rỗng hoặc quá dài; `503` khi giọng nói tắt hoặc chưa sẵn sàng.
- **`POST /v1/stt/learn`** `{"heard": "<chữ nhận giọng>", "fixed": "<chữ người dùng đã sửa rồi mới gửi>"}` → `{"learned": <số cặp>}`. App ghi nhớ cặp "nghe ra X nhưng ý là Y"
  (chỉ thay thế 1-3 từ, phía nghe sai không chứa số); một cặp được áp dụng sau khi được sửa đủ `LICHVIET_LEARN_MIN` lần (mặc định 2).
  Xem và xóa: `GET /v1/heard`, `DELETE /v1/heard/<cụm>`.
