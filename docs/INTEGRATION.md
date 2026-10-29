# Bàn giao: tích hợp LicSoLo (SoloHost) vào app hệ sinh thái Lạc Việt

Tài liệu cho dev chính. Mỗi khẳng định gắn một nhãn:
**[Chắc chắn]** đọc trong mã, trong test, hoặc đã chạy; **[Có khả năng cao]** suy luận có căn cứ; **[Ước đoán]** chưa kiểm chứng.
Nguồn đọc: `lichviet/api.py`, `lichviet/service.py`, `lichviet/lunar.py`, `docs/API.md`, `solohost/*`, `mobile/src/*`. Số dòng chỉ để tra cứu, có thể lệch khi mã đổi.
Server đang chạy bản `0.5.2` (image `ghcr.io/dacle7/licsolo:0.5.2`). Liên hệ: **Lê Thành Đạt** (Lạc Việt Node).

> **Cập nhật nhánh `feat/improvements` (chưa phát hành image):** `PATCH /v1/events/<id>`, lặp `yearly`, `skip_acked`/`skip_delivered`, `POST /v1/events/check`,
> ngày quá khứ trong parser đã có trong mã (mục 9). Các mục 3 và 4.2 bên dưới mô tả bản `0.5.2`; chỗ nào đã đổi có ghi chú **[Đã làm]**.
> Số test hiện tại: 137 pytest + 80 vitest (trước đó 93 + 49).

## 1. Mục đích và kết luận

- LicSoLo trên SoloHost **đủ tính năng lõi để tích hợp**: hiểu câu tiếng Việt, lưu việc, lặp (kể cả âm lịch), nhắc việc có mốc ổn định,
  đồng bộ tăng dần, lịch `.ics`, nhập giọng nói. [Chắc chắn: có trong mã và test; chạy được trong 93 test của repo]
- App Android trong `mobile/` **chỉ là công cụ kiểm chứng** (chứng minh API đủ dùng cho một client thật). Không phải sản phẩm cuối, không nên kế thừa mã giao diện của nó.
- Cái chặn tích hợp không phải tính năng mà là **cấu hình và bảo mật khi chạy trên SoloHost** (mục 4).

## 2. Đã kiểm chứng gì

Do Lê Thành Đạt thử trên Redmi A5 (Android), qua Tailscale và một proxy tạm (mục 5): nhập chữ và giọng nói, `/parse`, lưu, xóa, `/events`, `/stt`,
`/stt/learn`, ghi vào lịch hệ thống, thông báo cục bộ, xóa đồng bộ. [Chắc chắn: kết quả do chủ dự án báo; tôi (Claude) không chạy trên máy thật]

- Bản APK đã thử trên máy thật là **bản build đầu tiên** (workflow `android`, run `40661155714`, commit `851e6cd`), chưa có đồng bộ nền.
- Bản **`mobile-v0.1.0`** (Release trên GitHub) có thêm **đồng bộ nền** (`@capacitor/background-runner`) và đồng bộ 60 giây khi app mở.
  Phần này **CHƯA chạy trên máy thật**: chỉ có test tự động (`vitest`, `tsc`) và CI build APK. [Chắc chắn]
- Các điểm nghi vấn của phần nền, đã đọc trong mã nguồn plugin nhưng chưa thử: (a) runner đọc giờ hẹn bằng `SimpleDateFormat` không đặt múi giờ nên app cộng độ lệch múi giờ của máy vào giờ hẹn;
  (b) `channelId` không được runner đọc nên thông báo nền đi qua kênh "default"; (c) runner không hủy được thông báo của app và ngược lại. [Chắc chắn là đọc trong mã; hành vi thật: Ước đoán]
- Chưa kiểm chứng trên máy thật: lịch `ACCOUNT_TYPE_LOCAL` có hiện trong Google Calendar và lịch Xiaomi hay không. [Ước đoán]

## 3. Giao diện nên dùng khi tích hợp

Chi tiết từng trường: `docs/API.md`. Mọi đường dẫn dùng được cả có và không có `/v1`. [Chắc chắn]

| Endpoint | Dùng để | Ghi chú |
|---|---|---|
| `GET /v1/events/changes?since=<cursor>&limit=200` | Đồng bộ tăng dần việc gốc | `since=0` = toàn bộ. Mỗi việc một lần, ở trạng thái mới nhất. `op: delete` là bia mộ (gỡ sự kiện lịch). `has_more` thì gọi tiếp. Con trỏ cũ hơn `LICHVIET_TOMBSTONE_DAYS` (mặc định 90): `410 {"action":"resync","since":"0"}`, phải tải lại từ 0 và thay toàn bộ. |
| `GET /v1/reminders/upcoming?days=14&device_id=` | Hẹn thông báo cục bộ trên thiết bị | Tối đa 60 ngày, 500 mốc, sắp theo `fire_at`. Mỗi mốc có `ref` ổn định. |
| `POST /v1/devices`, `GET /v1/devices`, `DELETE /v1/devices/<id>` | Đăng ký thiết bị | `device_id` `[A-Za-z0-9_-]{1,64}`, tối đa 20 thiết bị. LicSoLo không lưu token push. |
| `POST /v1/reminders/delivered` | Thiết bị báo đã hiển thị một mốc | Chống nhắc lặp giữa thông báo cục bộ và push. Độc lập với `fired` (notifier) và `ack` (giao diện). |
| `GET /v1/calendar.ics?from=&to=` | Đăng ký lịch qua URL | Một chiều. Mặc định -7 đến +365 ngày, tối đa 800 ngày. Khóa riêng `LICHVIET_ICS_KEY` qua `?key=`. |
| `POST /v1/parse` `{"text","save"}` | Hiểu câu, trả bản nháp | `save:false` trả nháp + cảnh báo trùng giờ; `save:true` lưu. |
| `POST /v1/events` | Tạo việc bằng trường rõ ràng | Chỉ nhận `title,start,duration_min,all_day,repeat,remind_before_min,notes,lunar`; trường lạ bị `400`. Việc trùng trả `duplicate:true`, không lưu thêm. |
| `PATCH /v1/events/<id>` | Sửa một phần việc | **[Đã làm, sau 0.5.2]** Cùng tập trường với `POST`; kiểm tra trên trạng thái sau khi sửa; `404` khi không có; xóa trạng thái đã nhắc; ghi vào `/events/changes`. |
| `POST /v1/events/check` | Cảnh báo trùng giờ | **[Đã làm, sau 0.5.2]** `{start, duration_min, all_day, exclude_id?}` → `{conflicts}`. Chỉ đọc. |
| `DELETE /v1/events/<id>` | Xóa việc | Xóa cả chuỗi lặp. |
| `GET /v1/events?from=&to=` | Các lần xảy ra đã bung lặp | Có `occurrence`, `occurrence_iso`, `id`, `repeat`, `remind_before_min`... |
| `GET /v1/stt/status`, `POST /v1/stt`, `POST /v1/stt/learn` | Nhập giọng nói | `/stt`: thân là WAV 16 kHz mono 16 bit, `Content-Type: audio/wav`, tối đa 8 MB, trả `{"text"}`. `503` khi giọng nói tắt hoặc chưa sẵn sàng. `/stt/learn` `{"heard","fixed"}`. (**[Đã làm]** đã có trong `docs/API.md`.) |

### Quy ước cần nhớ [Chắc chắn, từ `service.py`, `api.py`, `docs/API.md`]

- **Giờ**: `start`, `occurrence`, `fire_at` là **giờ địa phương theo `tz`** (từ `GET /v1/info`), **không kèm độ lệch**. Bản `*_iso` kèm độ lệch (`+07:00`).
  So sánh và đổi sang mili giây thì dùng `*_iso`; hiển thị và tính ngày thì dùng chuỗi địa phương để không phụ thuộc múi giờ của máy.
- **`ref`** của một mốc nhắc: `lv-<id>-<yyyymmddHHMM>` cho mốc đúng giờ, thêm hậu tố `-7d` hoặc `-1d` cho giỗ (`lv-9-202611100000-7d`). `event_ref` = `lv-<id>`.
  `key` (dùng khi báo `fired`/`delivered`) là `occurrence` kèm hậu tố `#7d`/`#1d` (dấu `#`, khác `ref` dùng dấu `-`).
- **UID trong `.ics`**: `lv-<id>-<yyyymmddHHMM>@lichviet`. Cùng phần `lv-<id>-<yyyymmddHHMM>` với `ref`, nên có thể dùng một mã cho cả lịch và thông báo.
- **Việc cả ngày nhắc lúc 08:00** của ngày đó (trừ `remind_before_min`).
- **Giỗ (`lunar_yearly`) có 3 mốc nhắc**: trước 7 ngày (`kind=prepare_7d`), trước 1 ngày (`prepare_1d`), và đúng giờ (`on_time`, trừ `remind_before_min`).
- **Lặp âm lịch được bung từng lần** (không có RRULE): `.ics` ra một `VEVENT` mỗi lần; `GET /events` trả từng lần. `GET /events/changes` trả **việc gốc** (kèm `lunar_day`/`lunar_month`), không bung.
- Sửa một việc xóa trạng thái "đã nhắc" của việc đó. Nhắc bù: việc một lần và giỗ tới `LICHVIET_CATCHUP_DAYS` (mặc định 7); việc lặp ngày/tuần/tháng chỉ nhìn lùi 1 ngày. Việc lưu với giờ đã qua không bị nhắc.

## 4. Điều kiện chặn đã biết (đọc kỹ)

### 4.1. SoloHost không truyền được `LICHVIET_API_KEY` và `LICHVIET_ALLOWED_HOSTS`

- `solohost/docker-compose.yml` chỉ truyền cho `app`: `LICHVIET_LLM_URL`, `LICHVIET_STT_URL`, `LICHVIET_AI`, `LICHVIET_TZ`. Không có `LICHVIET_API_KEY`, `LICHVIET_ALLOWED_HOSTS`, `LICHVIET_ICS_KEY`. [Chắc chắn]
- `solohost/config_options.yml` hiện chỉ có các trường kiểu `select` (`AI_MODE`, `AI_TIER`, `AI_MEMORY`, `AI_THREADS`, `PANEL_PORT`). [Chắc chắn]
  Theo Lê Thành Đạt, Pi Desktop từ chối biến chưa khai báo trong form; **tôi chưa tự kiểm chứng điều này** và chưa biết form có hỗ trợ trường nhập chữ hay không. [Ước đoán]
- Hệ quả: **không thể bật khóa API** trên SoloHost, và truy cập bằng tên có dấu chấm (ví dụ `*.ts.net`) bị `403` vì `host_ok()` chỉ nhận `localhost`, `127.0.0.1`, `::1`, tên không có dấu chấm,
  hoặc tên trong `LICHVIET_ALLOWED_HOSTS`. [Chắc chắn]
- **Đính chính quan trọng**: `README.md` (trước PR này) và brief demo ghi rằng khi chưa đặt khóa thì các endpoint đồng bộ trả `503`. **Mã không như vậy.** Ở `0.5.2`, chưa đặt `LICHVIET_API_KEY` thì
  `_auth()` trả `True`: `/v1/events/changes`, `/v1/reminders/upcoming`, `/v1/devices`, `/v1/calendar.ics` đều **mở và trả 200** (test `test_no_key_configured_means_open`; tag `v0.5.2` chứa đúng mã này). [Chắc chắn]
  `503` trong `api.py` chỉ dành cho giọng nói tắt hoặc chưa sẵn sàng. `README.md` đã được sửa trong PR này. Vì vậy bản demo hoàn toàn dùng được các endpoint "hệ sinh thái" nếu qua được kiểm tra Host.
  Vấn đề thật là ngược lại: **mọi endpoint mở cho bất kỳ ai tới được cổng**, vì không có cách bật khóa.
- Phương án (**chưa kiểm chứng phương án nào**):
  1. **Ghép nối trong app, khóa tự sinh lưu SQLite**: app tự sinh khóa lần đầu, lưu trong DB, ưu tiên hơn biến môi trường; một endpoint ghép nối (chỉ chấp nhận từ giao diện đi kèm lúc chưa có khóa) trả khóa cho cổng hệ sinh thái. Không phụ thuộc Pi Desktop. [Ước đoán: cần sửa `lichviet/api.py`; chưa viết]
  2. **Trường khai báo mới trong `config_options.yml`** (nhập chữ/mật khẩu) và truyền biến vào compose: gọn nhất nếu Pi Desktop hỗ trợ loại trường đó. [Ước đoán: chưa biết Pi Desktop có hỗ trợ không]
  3. Với `LICHVIET_ALLOWED_HOSTS`: cùng cơ chế, hoặc để cổng hệ sinh thái đổi `Host` về `127.0.0.1`/tên không dấu chấm như proxy tạm (mục 5) và không cần biến này. [Có khả năng cao]

### 4.2. Sửa việc qua HTTP **[Đã làm, sau 0.5.2]**

> Đã thêm `PATCH /v1/events/<id>` (mục 9). Phần dưới là hiện trạng của `0.5.2`, giữ lại để hiểu vì sao cần làm.

- `service.update(event_id, **fields)` có trong `lichviet/service.py` (trường cho phép: `title,start,duration_min,all_day,repeat,remind_before_min,notes,lunar_day,lunar_month`),
  nhưng `lichviet/api.py` **không có `PATCH`/`PUT /v1/events/<id>`** (chỉ có `do_GET`, `do_POST`, `do_DELETE`). [Chắc chắn]
- Hiện muốn sửa phải xóa rồi tạo lại (đổi `id`, mất trạng thái nhắc). Cần thêm `PATCH /v1/events/<id>` gọi `service.update`; `update` đã ghi nhật ký đồng bộ (`_log_change`) nên `/events/changes` sẽ phản ánh; `update` cũng xóa trạng thái đã nhắc/ack/delivered. [Chắc chắn]

### 4.3. Miễn trừ "giao diện đi kèm" dựa vào header do client đặt

- Khi đã đặt khóa, yêu cầu có `Sec-Fetch-Site: same-origin` hoặc `Origin` trùng `Host` được coi là giao diện đi kèm và **không cần khóa** (`_is_ui()` trong `api.py`). [Chắc chắn]
  Trình duyệt không cho trang web khác giả header này, nhưng **client không phải trình duyệt đặt được tùy ý**. [Chắc chắn]
- Do đó **cổng hệ sinh thái phải gỡ `Origin` và `Sec-Fetch-*` của client trước khi chuyển tiếp** (đã ghi trong `docs/API.md`), nếu không client ngoài có thể giả header để qua khóa. [Chắc chắn]
- **Không nên cho tên không có dấu chấm đi ngang** (ví dụ tên service Docker `app`): `host_ok()` cho qua mọi tên không có dấu chấm, nên chúng thoát kiểm tra DNS rebinding. Chỉ để cổng đứng trước và đổi `Host` sang giá trị mình kiểm soát. [Chắc chắn về mã; cách khai thác: Có khả năng cao]
- Không đưa cổng `18763` ra mạng; cổng hệ sinh thái đứng trước app. [Chắc chắn: theo `docs/API.md`]

## 5. Tái hiện thử nghiệm

1. Chạy LicSoLo trên Pi Desktop (cổng mặc định `18763`, chỉ nghe `127.0.0.1`).
2. Dựng một **proxy ngược** trên cùng máy, nghe cổng khác (bản demo dùng `18764`): nhận yêu cầu, **đổi `Host` thành `127.0.0.1:18763`**, **gỡ `Origin` và mọi `Sec-Fetch-*`**, chuyển vào `127.0.0.1:18763`, trả nguyên phản hồi.
   Gỡ `Origin` để app không từ chối vì Origin khác Host; đổi `Host` để qua `host_ok()`. [Chắc chắn: mô tả hành vi của bản `lic_proxy.py` do Lê Thành Đạt dùng; mã proxy không nằm trong repo]
3. Công khai proxy trong tailnet: `tailscale serve` trỏ tới `127.0.0.1:18764`. Điện thoại vào `https://<máy>.<tailnet>.ts.net`.
4. Cài APK (Release `mobile-v0.1.0`, hoặc artifact của workflow `android`), cho phép cài từ nguồn không xác định, cấp quyền lịch, thông báo, báo thức chính xác, micro. Đặt URL server trong Cài đặt của app.
5. Đọc `mobile/README.md` (build, quy tắc đồng bộ, giới hạn) và checklist kiểm thử trong brief (tạo việc trên máy tính, mở app, khóa màn hình, tắt máy tính, xóa việc, giỗ âm lịch).

## 6. Thuật toán đồng bộ của app kiểm chứng (để tham khảo)

Mã: `mobile/src/sync.ts` (đồng bộ lịch), `mobile/src/reminders.ts` (mốc nhắc, dùng chung với runner nền), `mobile/src/runner.ts` (nền). Có test: `mobile/tests/`.

- Lấy các lần xảy ra từ hôm nay -7 đến hôm nay +120 ngày bằng `GET /v1/events`; riêng `lunar_yearly` lấy tới +400 ngày (hai lần gọi, gộp theo ref). "Hôm nay" lấy từ `info.now` của server, không từ đồng hồ máy. [Chắc chắn]
- Mỗi lần xảy ra có `ref = lv-<id>-<yyyymmddHHMM>`. Ghi vào lịch hệ thống: `ref` vào `_SYNC_ID`, hash nội dung (tên, giờ bắt đầu, giờ kết thúc, cả ngày, ghi chú) vào `SYNC_DATA1`.
  Diff: ref mới thì thêm, hash khác thì sửa, ref không còn thì xóa; ref bị ghi trùng thì xóa bản thừa. Mọi thay đổi ghi trong **một** `applyBatch`. [Chắc chắn]
- Việc cả ngày: 00:00 UTC, `EVENT_TIMEZONE=UTC` (yêu cầu của `CalendarContract`). Việc có giờ: tính từ `occurrence_iso`, mặc định 60 phút nếu thiếu `duration_min`. Sự kiện **không** gắn `VALARM` hệ thống để khỏi nhắc hai lần. [Chắc chắn]
- Mốc nhắc tính trên điện thoại, **chép quy tắc `service._stages`/`_fire_points`**: gốc là giờ diễn ra (cả ngày: 08:00); việc thường nhắc `gốc - remind_before_min`; giỗ có 3 mốc (-7 ngày, -1 ngày, đúng giờ). Chỉ hẹn mốc chưa qua giờ và trong 30 ngày, tối đa 200 mốc gần nhất. Mỗi lần đồng bộ hủy hết rồi hẹn lại; `id` thông báo là băm FNV-1a 31 bit của `ref`. [Chắc chắn]
- **[Đã làm, sau 0.5.2]** App kiểm chứng giờ ưu tiên `GET /v1/reminders/upcoming` (mục 9.3); quy tắc tính tại chỗ ở trên chỉ còn là **dự phòng** khi endpoint lỗi hoặc server cũ.
- **Quy tắc này đang trùng với server. Khi tích hợp, nên bỏ phần tính ở client và dùng `GET /v1/reminders/upcoming`** (đã có `ref`, `fire_at_iso`, `kind`, loại mốc đã `delivered`): ít mã hơn và không lệch khi server đổi quy tắc. Nhớ `upcoming` cần khóa khi đã bật khóa. [Chắc chắn về API; lợi ích: Có khả năng cao]
- Dùng `/v1/events/changes` thay cho quét khoảng thời gian sẽ nhẹ hơn (cursor, bia mộ), nhưng trả việc gốc: client phải tự bung lặp, hoặc kết hợp với `/events`. Bản demo chọn quét khoảng vì đơn giản. [Có khả năng cao]
- Nền (`runner.ts`): chỉ lấy `/v1/events` và **hẹn thêm** thông báo; không ghi được lịch hệ thống vì runner không gọi được plugin tự viết. App và runner ghi lại mốc mình đã hẹn (`appRefs`, `bgRefs`) để một mốc không nổ hai lần. [Chắc chắn về thiết kế; hành vi trên máy thật: chưa kiểm chứng]
- Không chạy chồng hai lần đồng bộ; lỗi mạng thì dừng và giữ nguyên lịch cũ. [Chắc chắn: có test]

## 7. Lịch âm

- Đổi âm - dương theo **múi giờ UTC+7**, thuật toán thiên văn của **Hồ Ngọc Đức** (`lichviet/lunar.py`), không dùng thư viện lịch Trung Quốc (UTC+8) vì có năm lệch một ngày. [Chắc chắn]
- **Đã đối chiếu 507 tháng từ 2000 đến 2040 với tính thiên văn độc lập (`ephem`): lệch 0**. Chạy lại: `pip install ephem && python tools/verify_lunar.py [năm_đầu] [năm_cuối]`. [Chắc chắn: đã chạy khi viết tài liệu này]
- Hai tháng có trăng mới **sát nửa đêm** giờ Việt Nam (dưới 10 phút): **27/11/2008 23:54** và **21/04/2031 23:56**. Kết quả đúng với `ephem` nhưng nhạy với sai số; nếu thay thuật toán hay đổi múi giờ, hãy chạy lại kịch bản. [Chắc chắn]
- **Giỗ (`lunar_yearly`) và `lunar_monthly` bỏ qua tháng nhuận.** Tháng thiếu không có ngày 30 thì dùng ngày 29. [Chắc chắn: `next_solar`, `next_lunar_monthly`]
  Hệ quả: giỗ rơi vào năm có tháng nhuận trùng số tháng chỉ nhắc ở tháng thường. [Có khả năng cao]

## 8. Việc nên làm, theo thứ tự

1. **Quyết định cơ chế khóa và Host** (mục 4.1): thử Pi Desktop có nhận trường nhập chữ không; nếu không, làm phương án ghép nối trong app. Đây là điều kiện để không phơi API mở trên mạng.
2. ~~Thêm **`PATCH /v1/events/<id>`**~~ **[Đã làm, chưa phát hành]**: có test, đã ghi trong `docs/API.md`. Còn lại: phát hành image mới (mục 8.8).
3. Dựng **cổng hệ sinh thái**: đổi `Host`, gỡ `Origin`/`Sec-Fetch-*`, gắn khóa (mục 4.3). Thay `lic_proxy.py` tạm.
4. Client hệ sinh thái dùng **`/v1/reminders/upcoming`** (hẹn thông báo cục bộ, báo `delivered`) và **`/v1/events/changes`** (cursor, xử lý `410`) thay cho logic tính mốc nhắc trong `mobile/`.
5. Đăng ký thiết bị (`/v1/devices`); token push do hệ sinh thái giữ.
6. ~~Bổ sung `/v1/stt*` vào `docs/API.md`.~~ **[Đã làm]**
7. Chạy thật phần **đồng bộ nền** của `mobile-v0.1.0` trên máy thật trước khi dựa vào nó; nếu thông báo lệch giờ, tắt công tắc "Đồng bộ nền".
8. Phát hành server mới (nếu sửa `lichviet/`): tag `v*` chạy workflow publish đẩy image lên GHCR. Tag `mobile-v*` thì không.

## 9. Cải tiến trên nhánh `feat/improvements` (chưa phát hành image, chưa chạy trên máy thật)

Cộng thêm, không phá hợp đồng `docs/API.md`: client cũ vẫn chạy. Chỉ có test tự động (pytest, `unittest` của CI, vitest, `tsc`, build mobile); **không có phần nào được thử trên điện thoại thật**.

### 9.1. Sửa việc đã lưu: `PATCH /v1/events/<id>`
- Dùng `service.update`, đã đọc và bổ sung: (a) ghi `changes` dạng `upsert` nên `/events/changes` thấy; (b) xóa `fired`/`acked`/`delivered` của việc đó (đã có sẵn);
  (c) **trước đó thiếu** kiểm tra trên trạng thái sau khi sửa (lặp âm lịch phải còn ngày âm, tiêu đề không rỗng, kiểu số, không trùng việc khác): đã thêm.
- Trước đây `update` với id không tồn tại và không có trường nào trả `None` thay vì lỗi; nay là `404`.
- `mobile/src/api.ts` có `update()`; chưa có giao diện sửa trong app.

### 9.2. Lặp hằng năm dương lịch: `repeat: "yearly"`
- Sinh nhật, kỷ niệm. 29/2 → 28/2 vào năm không nhuận. Chỉ mốc `on_time`. Có trong sao lưu, `.ics`, `/events/changes`.
- Parser: `sinh nhật`, `kỷ niệm`, `hằng/hàng/mỗi năm` + ngày-tháng dương (không có "âm") → `yearly`. Có "âm lịch" hoặc đám giỗ: vẫn `lunar_yearly` (âm ưu tiên).
  `hằng năm` mà không có ngày-tháng thì không thành `yearly`, chỉ cảnh báo.
- **Đổi hành vi có chủ đích:** câu như "sinh nhật bạn 5/11" trước đây ra việc một lần, nay ra việc lặp hằng năm.
- Mobile: cửa sổ lấy xa 400 ngày áp cho cả `yearly`.

### 9.3. Giảm nhắc trùng giữa máy tính và điện thoại (mặc định tắt)
- Server: `GET /v1/reminders/upcoming?skip_acked=1` (bỏ mốc đã `ack`/`fired`), `GET /v1/reminders/due?skip_delivered=1` (bỏ mốc mà bất kỳ thiết bị nào đã báo `delivered`). Giao diện web gọi `due` với `skip_delivered=1`.
- Mobile: `device_id` ổn định (`android-<uuid>`, lưu trong kho chung), `POST /v1/devices` (đăng ký lại là cập nhật; đổi URL server thì đăng ký lại; server báo "chưa đăng ký" thì đăng ký lại và thử lại một lần),
  lấy mốc từ `/upcoming?days=30&device_id=...&skip_acked=1`, **dự phòng** quy tắc tự tính khi endpoint lỗi, server cũ hoặc chưa đăng ký được (thử đăng ký lại sau tối đa 10 phút).
  Sau mỗi lần đồng bộ, `POST /v1/reminders/delivered` cho các mốc app đã hẹn mà giờ nhắc đã qua; lỗi thì giữ lại thử lần sau, bỏ sau 14 ngày.
- Runner nền: **có làm**, trong phạm vi hạn chế: dùng `/upcoming` và báo `delivered` bằng `fetch` khi app đã đăng ký thiết bị với đúng server đó; **không tự đăng ký** (việc của app).
  Chưa thử trên máy thật; `fetch` POST trong môi trường background-runner chưa được chạy thử. [Ước đoán]
- **Giới hạn (mục 5):** đây chỉ giảm trùng giữa các lần đồng bộ. Mốc đã hẹn sẵn trên hai thiết bị thì vẫn nổ cả hai đúng giờ; chống trùng đúng lúc nổ cần **push**, chưa làm ở bản này.
  "Đã hiện" là giả định (hệ điều hành đã hẹn thì tới giờ tự hiện), không phải xác nhận thật từ hệ điều hành. Mốc app đã hẹn mà việc bị sửa/xóa trước giờ không được báo.

### 9.4. Ngày quá khứ và cảnh báo trùng giờ ở form Sửa
- Parser: `hôm kia`, `N ngày/tuần trước` (số hoặc chữ), `thứ X tuần trước`. Giữ cảnh báo "thời điểm này đã qua".
  Cụm mơ hồ (`bữa hổm`, `hồi trước`, `mấy hôm trước`, `hôm trước`, `lần trước`, `tuần/tháng/năm trước` đứng một mình): **không đoán**, `need_info` với `missing` có `start`, và không gọi AI.
- `POST /v1/events/check`; form Sửa trong giao diện web gọi khi đổi ngày/giờ/cả ngày và trước khi Lưu, hiện ghi chú "Trùng giờ với …". Chỉ cảnh báo, không chặn. Form không có ô thời lượng nên gửi `duration_min` của bản nháp.
  Phần giao diện web chỉ được kiểm tra cú pháp JavaScript và test chuỗi (không có trình duyệt trong CI).
