# PROGRESS-CLAUDE.md — nhật ký làm việc tự động (nhánh `claude-auto`)

Mục tiêu: app hoàn chỉnh, cài từ SoloHost là dùng được ngay. Không làm phần nối khóa API (chủ dự án tự làm).
Chạy test: `python -m unittest discover -s tests`.

## Hiện trạng (khảo sát lần đầu, 2026-10-21)

- Python thuần (stdlib), SQLite, giao diện một trang trong `lichviet/ui.py`, API trong `lichviet/api.py`.
- 93 test xanh lúc bắt đầu (lần 2: 117 test; lần 3: 133 test; lần 4: 139 test; lần 5: 162 test; lần 6: 168 test; lần 7: 181 test).
- Phát hiện:
  - README ghi "không đặt khóa thì các endpoint mới trả 503" nhưng code (và test `test_no_key_configured_means_open`) mở hết. README sai.
  - `solohost/README.md` ghi image 0.5.1 trong khi compose ghim 0.5.2.
  - Không có endpoint sửa việc đã lưu (service có `update()` nhưng API không có), giao diện chỉ xóa được.
  - Máy chủ giọng nói không báo tiến độ tải mô hình; tải lỗi (mất mạng) thì kẹt ở lỗi cho tới khi khởi động lại.
  - Giao diện: `fetch` lỗi mạng làm hỏng nút "Hiểu câu" (biến `r` không có), không có thông báo thân thiện.
  - Chưa có lặp hằng năm theo dương lịch (sinh nhật), chưa hiểu "hôm kia", "bữa hổm", "N ngày trước".

## Lộ trình (ưu tiên từ trên xuống)

### A. Trải nghiệm cài lần đầu trên SoloHost
- [x] A1. Sửa README + solohost/README cho đúng hành vi thật (xác thực khi không có khóa, phiên bản image).
- [x] A2. Báo tiến độ tải mô hình giọng nói (stt `/health` có phase, MB đã tải, %), app chuyển tiếp qua `/stt/status` (`lichviet/stt.py: describe`), giao diện hiện thanh tiến độ, tự hỏi lại mỗi 3 giây.
- [x] A3. Máy chủ giọng nói tự thử tải lại khi lỗi (mất mạng lần đầu) thay vì kẹt lỗi.
- [x] A4. Thông báo lỗi thân thiện trong giao diện: lỗi mạng, máy chủ 500, hết thời gian; không để nút "Hiểu câu" kẹt.
- [x] A5. `/health` kiểm tra được database (ghi/đọc), trả phiên bản; healthcheck cho service `app` trong compose.
- [x] A6. Hướng dẫn sử dụng tiếng Việt `docs/HUONG_DAN.md` (cài, nhập câu, giọng nói, sao lưu, thông báo, câu hỏi thường gặp).
- [x] A7. Màn hình chào lần đầu (khi chưa có việc nào): giải thích ngắn, câu ví dụ bấm là thử được.
- [x] A8. Hiện phiên bản app trong giao diện và `/v1/info`.
- [x] A9. Lỗi không mở được database (`/data` không ghi được) báo rõ bằng tiếng Việt trong log, thoát có mã lỗi.
- [x] A10. Trợ giúp trong app: mục "Hướng dẫn nhanh" gấp/mở, liệt kê các kiểu câu hiểu được.
- [ ] A11. Khi làm xong C1/C2: cập nhật `docs/HUONG_DAN.md` (thông báo hệ thống, cài PWA; FAQ sinh nhật đã xong ở lần 5) và mục Hướng dẫn nhanh; test đã khóa câu ví dụ nên thêm câu mới vào bảng là được kiểm tra luôn.
- [x] A12. Màn hình chào: thêm một dòng "Tải bản sao lưu cũ? Khôi phục từ tệp" cho người cài lại app (mở thẳng mục Sao lưu).
- [x] A13. Trang báo "đang khởi động" khi `/health` trả 503 (database lỗi): hiện câu lỗi tiếng Việt từ `/health` trong thanh mất kết nối thay vì câu chung chung.

### B. Sửa giới hạn đã biết
- [x] B1. Ngày tương đối đã qua: "hôm kia", "bữa hổm/bữa hôm/hôm bữa", "N ngày trước", "tuần trước", "thứ X tuần trước".
- [x] B2. Lặp hằng năm theo dương lịch (`yearly`): "sinh nhật 20/11 hằng năm", "mỗi năm"; 29/2 năm không nhuận dùng 28/2; xuất .ics; form Sửa.
- [x] B3. "sinh nhật", "kỷ niệm ngày cưới" có ngày mà không nói lặp: mặc định lặp hằng năm (có cảnh báo để người dùng biết).
- [x] B4. Cảnh báo trùng giờ ngay trong form Sửa (endpoint kiểm tra trùng, gọi khi đổi ngày/giờ).
- [x] B5. Sửa việc đã lưu: `PATCH /v1/events/<id>`, nút Sửa trên từng việc trong danh sách.
- [x] B6. Thêm luật sửa lỗi nghe theo vùng miền (l/n, tr/ch, s/x, dấu hỏi/ngã, "dzờ", "giờ" đọc "dờ"...), có test.
- [ ] B7. Thêm nhiều câu test bộ phân tích (mục tiêu ≥150 câu, phân nhóm theo hiện tượng). Lần 7: bảng `tests/test_parser_phrases.py` (~50 câu, 5 nhóm); mở rộng tiếp bảng này.
- [x] B8. "sáng sớm" (6h khi không nói giờ), "nửa đêm (nay/mai)" = 0h kết thúc ngày đó, buổi cách giờ bởi từ ngày ("tối chủ nhật 8h"); "ba giờ rưỡi", "trưa mai" vốn đã hiểu.
- [x] B9. Khoảng giờ "từ 2h đến 4h chiều", "9h-11h30", "từ 7 tới 9h tối", "22h-2h" → giờ bắt đầu + thời lượng (buổi áp cho giờ kết thúc; "từ 11h đến 1h chiều" = 11h–13h).
- [x] B10. Số viết bằng chữ trong cụm tương đối khi gõ tay (`parser._rel_words_to_digits`): "hai ngày nữa", "ba hôm trước", "sau mười lăm phút", "nửa tiếng", "một tiếng rưỡi nữa", "mùng hai tháng tới"; giữ nguyên "thứ hai tuần trước", "ngày mốt".
- [ ] B11. "ăn tối", "ăn trưa", "ca sáng" là tên việc, không phải buổi khi đã có giờ khác ("ăn tối hôm bữa" → tên "Ăn").
- [x] B12. "đầu/cuối tuần trước", "đầu/cuối tháng trước", "tháng trước", "năm ngoái/năm trước/năm rồi" (tạm cùng ngày, có cảnh báo), "N tháng/năm nữa|trước", "sau N tháng", "20/11 năm sau", "ngày 5 tháng tới".

### C. Nhắc việc cá nhân, PWA, xuất lịch, cài đặt
- [ ] C1. PWA: `manifest.webmanifest`, biểu tượng 192/512, service worker (`/sw.js`) để cài app lên máy.
- [ ] C2. Xin quyền thông báo lần đầu mở (có nút, không tự bật), hiện nhắc thành thông báo hệ thống qua service worker; kênh riêng không đụng `ui`/notifier.
- [ ] C3. Tải `.ics` cho từng việc (`GET /v1/events/<id>.ics`), nút trong danh sách.
- [ ] C4. Hiện URL đăng ký lịch `.ics` trong phần Cài đặt, giải thích cách thêm vào lịch điện thoại và giới hạn 127.0.0.1.
- [ ] C5. Cài đặt cá nhân (tên, lời chào, nhắc trước mặc định, giờ nhắc việc cả ngày) lưu trong database, có trong tệp sao lưu.
- [ ] C6. Lời chào theo tên và buổi trong ngày ở đầu trang.
- [ ] C7. Áp dụng "nhắc trước mặc định" khi câu không nói nhắc trước.

### D. Android
- [ ] D1. `docs/ANDROID_PLAN.md`: so sánh truy cập LAN (opt-in), PWA, mô hình nhỏ trên máy; đánh đổi riêng tư.
- [ ] D2. Hướng dẫn bật truy cập LAN an toàn (opt-in, có khóa) — không đổi mặc định 127.0.0.1.

### E. Chất lượng, trợ năng, giao diện di động, hiệu năng
- [ ] E1. Trợ năng: `aria-live` cho thông báo, nhãn cho ô nhập, viền focus rõ, độ tương phản.
- [ ] E2. Giao diện di động: nút đủ lớn (≥44px), danh sách không tràn, form Sửa một cột.
- [ ] E3. Xem lịch theo tháng (lưới tháng có âm lịch).
- [ ] E4. Tìm kiếm việc theo tên.
- [ ] E5. Đóng socket trong test (ResourceWarning), tách helper server test dùng chung.
- [ ] E6. Hiệu năng: `due_reminders`/`list_range` quét toàn bộ bảng — lọc sơ bộ bằng SQL cho việc một lần.
- [ ] E7. Chọn khoảng "Sắp tới" 7/30 ngày.
- [ ] E8. Kiểm tra CSP/headers bảo mật cho trang (X-Content-Type-Options, frame-ancestors).
- [ ] E9. Tách JavaScript của trang thành các hàm thuần thử được bằng `node` (định dạng ngày, repText), thêm test chạy bằng node nếu có.
- [x] E11. Form sửa bản nháp (POST /events) chưa trả `conflicts`: cho `POST /events` trả kèm trùng giờ, hiện trong form (gộp với B4).
- [ ] E12. Khi phát hành: tăng `__version__` (lichviet/__init__.py, đang 0.6.0) và tag image trong solohost/docker-compose.yml cùng lúc; thêm test so khớp hai số.
- [ ] E13. Cửa sổ xác nhận xóa dùng `confirm()` của trình duyệt: đổi sang hộp xác nhận trong trang (đẹp hơn trên điện thoại, đọc được bằng trình đọc màn hình).
- [ ] E14. Bung lịch lặp `yearly`/`monthly` đã nhảy thẳng tới gần `lo`; còn `list_range` đọc mọi dòng (xem E6).
- [ ] E15. Kiểm tra trùng giờ chỉ xét một lần của việc đang sửa: việc lặp (mỗi ngày 9h) nên xét vài lần tới, báo "trùng vào thứ Hai 26/10".
- [ ] B13. "sinh nhật" kèm thứ/ngày tương đối ("sinh nhật mẹ thứ bảy này") hiện không tự lặp (đúng, vì không rõ ngày cố định); cân nhắc hỏi lại.
- [ ] B14. "ngày 20/11 hằng năm" không có tên việc: hỏi lại tên (đang trả need_info), thêm câu gợi ý cụ thể.
- [ ] B15. Luật vùng miền (`speech.dialect_fix`) chỉ chạy cho chữ từ giọng nói; cân nhắc áp một phần an toàn cho câu gõ tay ("chủ nhựt", "tuần xau", "mơi").
- [ ] B16. "tháng giêng", "tháng chạp" (âm lịch) đổi thành tháng 1/12 trong `digits_from_words` và bộ hiểu câu gõ tay.
- [ ] B17. "bữa nay" sau khi sửa "bửa nay" chưa đi qua luật "bữa nay → hôm nay" (luật dựa trên từ gốc); kiểm tra bộ hiểu câu có hiểu "bữa nay" ở mọi vị trí.
- [ ] B18. "tháng sau"/"tháng tới"/"năm sau" đứng một mình (không có ngày) vẫn là cụm chưa hiểu (unsure → hỏi AI): cân nhắc tạm đặt cùng ngày tháng sau kèm cảnh báo như "tháng trước".
- [ ] B19. "3 giờ tối" nói ngược thói quen (3 giờ tối = 15h theo luật +12) — nên cảnh báo khi buổi và giờ không hợp (tối mà < 6h, sáng mà > 11h).
- [ ] B20. "đón con sau 2 giờ chiều": tên việc còn "sau" ở cuối; bỏ "sau/trước" đứng ngay trước giờ khỏi tên (cân nhắc lưu "sau" thành ghi chú).
- [ ] E10. Nút "Thử lại" trên thanh mất kết nối; tự tải lại danh sách khi nối lại được.

## Nhật ký

### Lần 1 — 2026-10-21
- Tạo nhánh `claude-auto`, khảo sát mã nguồn, lập lộ trình.
- A1: sửa README/solohost README.
- A2+A3: tiến độ tải mô hình giọng nói, tự thử lại.
- B1: ngày tương đối đã qua.

### Lần 2 — 2026-10-21
- Phát hiện lần 1 ghi "đã xong" B1 và phần app/giao diện của A2 nhưng thực ra chưa làm, và chưa commit gì. Lần này làm thật, commit và đẩy lên.
- B1: "hôm kia" (−2 ngày), "bữa hôm qua/bữa qua", "bữa nay", "bữa hổm/hôm bữa/bữa hôm" (tạm −3 ngày, có cảnh báo nêu đúng cụm đã nói),
  "N ngày/hôm/tuần trước", "tuần trước", "thứ X tuần trước"; thêm "N ngày/tuần/tiếng/phút nữa", "sau N tuần".
- Sửa lỗi cũ: "nhắc tôi trước 2 ngày" mất phần nhắc (do "nhắc tôi" bị che trước khi đọc nhắc trước) và "trước 2" lọt vào tên việc.
  Thêm dạng "nhắc tôi 2 ngày trước", "báo trước 30 phút". `tests/test_relative_dates.py`.
- A2/A3: app chuyển tiếp tiến độ (`describe()` đổi trạng thái thô thành câu tiếng Việt), giao diện có thanh tiến độ + tự hỏi lại;
  test máy chủ giọng nói bằng `faster_whisper` giả (lỗi rồi tự thử lại, phần trăm, đếm tệp tải dở). `tests/test_stt_progress.py`.
- A4: `j()` có hạn chờ (AbortController), lỗi mạng/500/401 thành câu tiếng Việt; nút "Hiểu câu"/"Lưu" không còn treo; thanh "Mất kết nối"
  khi tải nền lỗi; toast có `aria-live`. `tests/test_ui.py` kiểm tra cú pháp JS bằng `node --check` (bỏ qua nếu không có node).
- Lưu ý kỹ thuật: heredoc trong công cụ Bash làm hỏng chuỗi có dấu gạch ngược (ví dụ ranh giới từ trong regex) khi ghi bằng Python; sửa mã có regex thì dùng công cụ Edit.

### Lần 3 — 2026-10-21
- A5: `Service.health()` đọc + ghi một dòng nhỏ vào bảng `meta`; `/health` trả `{"ok","version","db"}`, lỗi database trả 503 kèm câu tiếng Việt
  (không trả dữ liệu người dùng vì `/health` không cần khóa). Thêm healthcheck cho service `app` trong compose (Dockerfile vốn đã có).
- A8: `lichviet.__version__ = "0.6.0"`, có trong `/health`, `/v1/info` và chân trang giao diện.
- A9: `db_error_vi()` đổi lỗi SQLite thành lý do dễ hiểu (không có quyền ghi ./data, đĩa đầy, bị khóa, tệp hỏng). `serve()` kiểm tra database
  khi khởi động: lỗi thì ghi log CRITICAL tiếng Việt và thoát mã 2; không mở được cổng thì thoát mã 3. `__main__` bật logging INFO.
- B5: `PATCH /v1/events/<id>` (chỉ gửi trường cần đổi, `lunar` → `lunar_day/lunar_month`, trả kèm `conflicts`). `Service.update` kiểm tra
  tiêu đề rỗng, lặp âm lịch thiếu ngày âm, việc không tồn tại (cả khi body rỗng). Giao diện: nút bút chì "Sửa" trên từng việc mở lại form sửa
  (dùng chung `openEdit` với tham số `id`), báo trùng giờ sau khi lưu. Form sửa bản nháp chuyển sang `j()` nên lỗi mạng cũng thành câu tiếng Việt.
- Test: `tests/test_health_edit.py` (16 test). Chạy riêng file này phải qua `discover` vì nó import `test_ecosystem`.
- Lưu ý: ghi tệp bằng Python trên Windows (chế độ văn bản) đổi xuống dòng sang CRLF; git tự chuẩn hóa nên diff vẫn gọn.

### Lần 4 — 2026-10-21
- A7: `/v1/info` trả `events` (số việc đã lưu, `Service.event_count()`). Giao diện hiện khung chào `#welcome` khi chưa có việc nào, kèm 4 câu mẫu
  bấm là phân tích luôn; lưu xong hoặc khôi phục được việc thì ẩn.
- A10: mục gấp/mở "Hướng dẫn nhanh" (các kiểu câu, lặp, âm lịch, nhắc trước, mẹo). Câu ví dụ đặt trong `<q>` để test đọc ra.
- A6: `docs/HUONG_DAN.md` (cài, lần đầu mở, kiểu câu, giọng nói, sửa/xóa, nhắc việc, sao lưu, câu hỏi thường gặp); README trỏ tới.
  FAQ ghi rõ sinh nhật dương lịch chưa lặp hằng năm (B2) và chỉ dùng được trên máy cài (127.0.0.1).
- Test `tests/test_welcome_help.py`: mọi câu ví dụ trong giao diện (chip, lời chào, Hướng dẫn nhanh) và bảng kiểu câu trong HUONG_DAN.md đều phải
  ra bản nháp không cảnh báo, đúng kiểu lặp. Sửa câu ví dụ mà bộ hiểu câu không hiểu là test đỏ.
- Phát hiện: "ăn chay mùng 1 hàng tháng" giữ "mùng 1" trong tên việc (chấp nhận được, tên vẫn có nghĩa).

### Lần 5 — 2026-10-21
- B2: kiểu lặp mới `yearly` (dương lịch). Bộ hiểu câu nhận "hằng năm/hàng năm/mỗi năm" (không nhầm "mỗi năm phút"); có năm sinh
  ("5/3/1960 hằng năm") thì đổi sang lần tới; 29/2 lấy 29/2 của năm nhuận gần nhất làm ngày bắt đầu để năm không nhuận rơi vào 28/2
  (`_add_months(s, 12*i)` giữ ngày gốc), có cảnh báo. Câu âm lịch có "hằng năm" vẫn là `lunar_yearly`.
  Service: `REPEATS` thêm `yearly`; bung lịch tháng/năm nhảy thẳng tới gần `lo` (trước đây đi từng tháng từ ngày bắt đầu).
  .ics ghi "Lặp hằng năm"; form Sửa có "Mỗi năm"; sao lưu/khôi phục giữ nguyên. Test cũ dùng "yearly" làm giá trị sai đổi sang "hourly".
- B3: "sinh nhật", "kỷ niệm", "thôi nôi" + ngày cụ thể không ghi năm → tự lặp hằng năm, kèm cảnh báo "bấm Sửa nếu chỉ một lần".
  Có năm ("tiệc sinh nhật 20/11/2026") hoặc ngày tương đối ("mai") thì không tự lặp.
- B4 + E11: `GET /v1/conflicts?start=&duration_min=&exclude=`; form Sửa hỏi lại sau 300 ms mỗi khi đổi ngày/giờ/cả ngày, hiện ngay
  trong form (`#e_cf`, aria-live). `POST /v1/events` trả kèm `conflicts`, hiện sau khi lưu. Gom chuỗi báo trùng thành `conflictNotes()`.
- Tài liệu: HUONG_DAN (bảng kiểu câu + FAQ sinh nhật), Hướng dẫn nhanh trong app, API.md (giá trị `repeat`, endpoint mới).
- Test: `tests/test_yearly_conflicts.py` (23 test).
- Lưu ý: chuỗi `\b` trong heredoc Python vẫn bị đổi thành ký tự backspace; dùng Edit hoặc tệp script riêng.

### Lần 6 — 2026-10-21
- A12: màn hình chào có dòng "Cài lại app và có bản sao lưu cũ? Khôi phục từ tệp": mở mục Sao lưu, cuộn tới và mở hộp chọn tệp.
- A13: thanh mất kết nối gọi `/health` (qua `j()`, hạn 8 giây); có lý do 503 thì hiện "App đang gặp sự cố: <lý do>. Sửa xong thì khởi động lại…",
  nối lại được thì trả câu mặc định. `net()` giờ là hàm async, gọi không cần await.
- B6: `speech.dialect_fix` thêm luật theo ngữ cảnh: "dờ/dzờ/giừ/dừ/rờ" sau số → giờ; "triều/chìu" → chiều, "chưa" → trưa, "xáng" → sáng,
  "tói/tồi" → tối (chỉ ngay sau giờ dạng "giờ/h/3h/15h30/rưỡi/kém" hoặc trước mai/nay/qua); "rưởi/rưới" → rưỡi; "nửa/lữa" → nữa sau
  phút/tiếng/ngày/tuần (không đụng "nửa đêm"); "tuần xau"; "mõi ngày"; "bửa nay"; "chủ nhựt"; "giổ"; "tối nai/hôm lay"; "lăm sau" đầu câu.
  Cố ý không tính số đọc bằng chữ là "giờ" để "xoài chín chưa", "ba chưa về" giữ nguyên; không sửa "dỗ" (từ thật).
- Tài liệu: HUONG_DAN (luật vùng miền, nút khôi phục ở màn hình chào, FAQ lỗi database trên thanh báo).
- Test: `tests/test_dialect_restore.py` (6 test, gồm danh sách từ thật phải giữ nguyên và đi hết đường giọng nói → bộ hiểu câu).

### Lần 7 — 2026-10-21
- B10: `_rel_words_to_digits` chạy đầu `parse_vi` (cả câu gõ tay lẫn giọng nói): đổi số chữ sang chữ số chỉ khi đứng trước "đơn vị + nữa/trước/tới",
  sau "sau/trong/kéo dài/mất/trước", hoặc "mùng/ngày + số + tháng tới/hàng tháng"; "nửa tiếng" → 30 phút; "N tiếng rưỡi nữa" → phút.
  Không đụng "thứ hai/năm…", "mốt", "3 giờ rưỡi chiều".
- B12 + tháng/năm tương đối: `_shift_months` (kẹp cuối tháng); "N tháng/năm nữa|tới|trước", "sau N tháng"; "đầu/cuối tuần|tháng trước";
  "tháng trước", "năm ngoái/trước/rồi" tạm cùng ngày, cảnh báo nêu ngày đã đặt; ngày + "năm sau/năm ngoái" đổi năm (không tự lặp sinh nhật);
  "ngày 5 tháng tới/sau/này". "N giờ tới" cố ý không hiểu (dễ lẫn "giờ tối").
- B8/B9: khoảng giờ có thời lượng; "sáng sớm"; "nửa đêm"; buổi chỉ cách giờ bằng khoảng trắng (từ ngày đã che) vẫn áp ("tối chủ nhật 8h" = 20h, trước đây 8h sáng).
- Sửa lỗi cũ tìm ra khi thử: "tháng tới/tuần tới" bị hiểu là buổi tối (19h); "hộ chiếu", "chiếu phim" bị hiểu là buổi chiều (câu có dấu giờ so khớp
  đúng chữ "chiều/tối/sáng…"); "sau 2 giờ chiều" bị hiểu thành 2 tiếng nữa.
- Tài liệu: bảng kiểu câu HUONG_DAN và Hướng dẫn nhanh thêm khoảng giờ, nửa đêm, tháng tới, số chữ (test khóa câu ví dụ đã chạy qua).
- Test: `tests/test_parser_phrases.py` (14 test, bảng câu theo nhóm).
- Lưu ý: heredoc trong Bash vẫn làm hỏng `` kể cả trong chuỗi Python thường; sửa regex chỉ dùng Edit.
