# Trợ lý thời gian: app Android demo cho LicSoLo

Bản demo chạy trên điện thoại thật. Gõ hoặc nói một việc, xem thẻ "Trợ lý hiểu là", lưu vào LicSoLo.
Mọi việc trong LicSoLo hiện trong **lịch hệ thống** (lịch riêng "Trợ lý thời gian") và được hẹn **thông báo cục bộ**,
nên vẫn nhắc đúng giờ khi khóa màn hình hoặc khi máy tính đã tắt (miễn là app đã đồng bộ trước đó).

Không sửa server. App dùng các endpoint `/v1` không cần khóa của bản 0.5.2 (`info`, `parse`, `events`, `stt`, `stt/learn`).
Chưa có khóa API, ghép nối hay xác thực: đó là việc của lúc tích hợp vào hệ sinh thái Lạc Việt.

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `src/sync.ts` | Logic đồng bộ thuần TypeScript: diff lịch, tính mốc nhắc, hash, chống chạy chồng. Có test. |
| `src/timeutil.ts` | Phép tính giờ trên chuỗi giờ địa phương của server, không phụ thuộc múi giờ điện thoại. |
| `src/api.ts` | Máy khách HTTP (`CapacitorHttp`, không vướng CORS). |
| `src/native.ts` | Nối với plugin Android và quyền. |
| `src/main.ts`, `style.css`, `voice.ts` | Giao diện (không framework), ghi âm và đổi sang WAV (chép từ `lichviet/ui.py`). |
| `android/.../LvCalendarPlugin.kt` | Plugin Kotlin ghi `CalendarContract` (lịch riêng chỉ đọc, ghi theo lô, mã đồng bộ). |
| `android/.../LvSystemPlugin.kt` | Mở các trang cài đặt hệ thống (quyền, tự khởi động, pin, báo thức chính xác). |
| `tests/sync.test.ts` | Test vitest, giả lập lịch, thông báo và HTTP. |

URL server là ô cấu hình trong **Cài đặt** (mặc định `https://d.taila2d06a.ts.net`, không viết cứng trong mã).

## Chạy test

```powershell
cd mobile
npm ci
npm test          # vitest
npm run typecheck
```

## Build APK trên Windows (Android Studio)

1. Cài [Node.js 22+](https://nodejs.org) và [Android Studio](https://developer.android.com/studio) (kèm Android SDK 36 và JDK 21; Android Studio mới đã có JDK 21 đi kèm).
2. Trong thư mục `mobile`:
   ```powershell
   npm ci
   npm run build
   npx cap sync android
   ```
3. Mở thư mục `mobile/android` bằng Android Studio, chờ Gradle sync xong, rồi chọn **Build > Build APK(s)**.
   Hoặc dòng lệnh: `cd android; .\gradlew.bat assembleDebug`.
4. APK nằm ở `mobile/android/app/build/outputs/apk/debug/app-debug.apk`.

Hoặc để GitHub dựng: workflow `android` (`.github/workflows/android.yml`) chạy khi `mobile/**` đổi hoặc chạy tay
(Actions > android > Run workflow); tải APK ở mục Artifacts.

## Cài lên điện thoại

- Cách 1: nối cáp, bật **Tùy chọn nhà phát triển > Gỡ lỗi USB**, rồi `adb install -r app-debug.apk`
  (hoặc nút Run trong Android Studio).
- Cách 2: chép `app-debug.apk` sang điện thoại, mở bằng Trình quản lý tệp, cho phép **cài từ nguồn không xác định**.

Lần mở đầu app xin lần lượt: lịch, thông báo, báo thức chính xác (mic được hỏi khi bấm nút mic lần đầu).
Sau đó vào **Cài đặt** làm theo hướng dẫn HyperOS: bật Tự khởi động và đặt pin "Không hạn chế" cho **cả app này lẫn Tailscale**.

## Đường truy cập

Điện thoại vào LicSoLo qua Tailscale tại `https://d.taila2d06a.ts.net`, trỏ tới `lic_proxy.py` (cổng 18764) trên Windows,
proxy này đổi `Host` và gỡ `Origin`/`Sec-Fetch-*` rồi chuyển vào app (cổng 18763). Đồng bộ cần máy tính bật,
Pi Desktop đang Running và cửa sổ `lic_proxy.py` đang mở.

## Quy tắc đồng bộ

- Chạy khi mở app, khi quay lại màn hình chính, mỗi 60 giây khi app đang mở, ngay khi mạng nối lại, sau mỗi lần lưu hoặc xóa, và khi bấm **Đồng bộ ngay**. Không chạy chồng.
- Lấy việc từ hôm nay - 7 ngày đến hôm nay + 120 ngày; giỗ (`lunar_yearly`) đến hôm nay + 400 ngày.
- Lịch: mỗi lần xảy ra có `ref = lv-<id>-<yyyymmddHHMM>` (cùng dạng UID trong `.ics` của server), lưu ở `_SYNC_ID`; mã băm nội dung ở
  `SYNC_DATA1`. Ref mới thì thêm, hash khác thì sửa, ref mất thì xóa. Việc cả ngày: 00:00 UTC, `EVENT_TIMEZONE=UTC`.
  Sự kiện không gắn báo nhắc của hệ thống (app tự nhắc, tránh nhắc hai lần).
- Thông báo: chép quy tắc `service._stages` / `_fire_points` của server. Việc thường nhắc trước `remind_before_min`;
  việc cả ngày nhắc 08:00; giỗ có ba mốc (−7 ngày, −1 ngày, đúng giờ). Chỉ hẹn mốc trong 30 ngày tới, tối đa 200 mốc.
  Mỗi lần đồng bộ hủy hết rồi hẹn lại. Khi tích hợp hệ sinh thái, chuyển sang `GET /v1/reminders/upcoming`.
- Lỗi mạng: dừng, giữ nguyên lịch và thông báo cũ.

## Đồng bộ nền (`@capacitor/background-runner`)

- Tác vụ JS (`src/runner.ts`, bó thành `dist/runners/runner.js`) chạy định kỳ ~15 phút kể cả khi đóng app (Android tối thiểu 15 phút, hệ thống có thể hoãn).
  Môi trường của nó chỉ có `fetch`, `CapacitorKV` và `CapacitorNotifications`; **không gọi được plugin tự viết `LvCalendar`**,
  nên nền chỉ lấy `/v1/events`, tính mốc nhắc bằng cùng module `src/reminders.ts` với app và **hẹn thêm thông báo**. Lịch hệ thống chỉ cập nhật khi mở app.
- Thông báo của nền và của app dùng hai bộ hẹn riêng, không hủy lẫn nhau. Để một mốc không nổ hai lần, mỗi bên ghi lại các mốc mình đã hẹn
  (`appRefs`, `bgRefs`, trong cùng kho SharedPreferences) và bên kia bỏ qua các mốc đó. Hệ quả: nền chỉ **thêm** mốc; việc bị sửa hoặc xóa
  sau khi nền đã hẹn thì mốc cũ vẫn nổ cho tới khi qua giờ.
- Công tắc **Đồng bộ nền** (mặc định bật), thời điểm nền chạy gần nhất và nút mở cài đặt pin nằm trong **Cài đặt**.
- background-runner đọc giờ hẹn bằng `SimpleDateFormat` không đặt múi giờ, nên app lưu độ lệch múi giờ của máy (`tzOffsetMin`) và runner cộng vào giờ hẹn.

## Giới hạn của bản demo

- Đồng bộ cần máy tính bật **và** `lic_proxy.py` đang mở. Thông báo đã hẹn rồi thì vẫn nổ khi máy tính tắt.
- Việc tạo trên máy tính chỉ hiện trên điện thoại sau khi mở app (chưa có đồng bộ nền).
- Máy tính và điện thoại có thể cùng nhắc một việc.
- Không có khóa: mọi thiết bị trong tailnet đều vào được app.
- Chỉ đồng bộ một chiều (LicSoLo -> lịch điện thoại). Không sửa việc đã lưu (xóa rồi tạo lại). Không hỗ trợ iOS.
