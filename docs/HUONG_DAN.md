# Hướng dẫn sử dụng — Trợ lý thời gian của bạn

App lịch và nhắc việc bằng tiếng Việt, có âm lịch. App chạy ngay trên máy của bạn, dữ liệu không gửi đi đâu.

## 1. Cài đặt

1. Trong Pi Desktop, cài app bằng mã `datl071/ailich`.
2. Form cài đặt hiện ra. Nếu chỉ cần lịch và nhắc việc, giữ nguyên mặc định:
   - **Tính năng nâng cao:** "Tắt hết (khuyến nghị)". Đây là lựa chọn nhẹ nhất, lịch và nhắc việc vẫn dùng đầy đủ.
   - **Cổng truy cập app:** 18763. Chỉ đổi khi máy báo cổng này đang bị chương trình khác dùng.
3. Bấm cài. Khi app chạy xong, mở **http://127.0.0.1:18763** (đổi số cuối nếu bạn chọn cổng khác).

Muốn bật thêm sau này thì vào Config của app trong Pi Desktop, đổi "Tính năng nâng cao" rồi lưu:

| Lựa chọn | Dùng để | Cần thêm |
|---|---|---|
| Nhập bằng giọng nói | Nói thay vì gõ | Lần đầu tải mô hình khoảng 1,6 GB (cần mạng), khoảng 4 GB RAM |
| Trợ lý AI | Hiểu những câu khó mà bộ hiểu câu sẵn có chưa hiểu | RAM tùy mức mô hình (3 GB trở lên) |
| Cả giọng nói và Trợ lý AI | Cả hai | Cộng cả hai mức trên |

## 2. Lần đầu mở app

Lần đầu mở, app chưa có việc nào nên hiện lời chào kèm vài câu mẫu. Bấm một câu mẫu là app hiểu thử ngay, bạn xem bản nháp rồi bấm **Lưu** hoặc **Bỏ qua**. Lưu việc đầu tiên xong thì lời chào tự ẩn.

Ở cuối trang có mục **Hướng dẫn nhanh** liệt kê các kiểu câu app hiểu được.

## 3. Thêm việc

Gõ vào ô "Nói hoặc gõ việc cần nhớ…" rồi bấm mũi tên hoặc phím Enter. App luôn đưa ra bản nháp trước để bạn kiểm tra:

- **Lưu:** lưu vào lịch.
- **Sửa:** sửa tên, ngày, giờ, lặp, nhắc trước rồi mới lưu.
- **Bỏ qua:** không lưu gì.

Nếu việc mới trùng giờ với việc đã có, bản nháp báo "Trùng giờ với …". Nếu ngày giờ đã qua, bản nháp nhắc bạn kiểm tra lại.

### Các kiểu câu app hiểu

| Muốn | Ví dụ |
|---|---|
| Giờ cụ thể | "họp 3h chiều mai", "đón con 4h rưỡi chiều nay", "họp 3h kém 15 chiều mai" |
| Thứ trong tuần | "đi chợ 8h sáng thứ bảy", "đi khám thứ năm tuần sau 9h" |
| Ngày tháng | "nộp báo cáo 17h ngày 25/10" |
| Sau một khoảng | "gọi điện cho mẹ 30 phút nữa", "trả sách 2 ngày nữa", "tắt bếp mười lăm phút nữa", "tái khám 3 tháng nữa" |
| Khoảng giờ (tự tính thời lượng) | "họp từ 2h đến 4h chiều mai", "học tiếng Anh 7h-9h tối thứ sáu" |
| Nửa đêm, sáng sớm | "xem bóng nửa đêm nay" (0 giờ đêm nay); nói *sáng sớm* mà không kèm giờ thì tạm đặt 6 giờ |
| Tháng, năm tới | "đi chùa ngày 5 tháng tới", "họp lớp 20/11 năm sau" |
| Ngày đã qua (ghi lại) | "hôm kia", "hôm qua", "bữa hổm", "3 ngày trước", "ba hôm trước", "tuần trước", "đầu tháng trước", "tháng trước", "năm ngoái" |
| Lặp mỗi ngày/tuần/tháng | "uống thuốc 7h tối mỗi ngày", "mỗi sáng 7h uống thuốc", "họp nhóm 9h thứ hai hằng tuần", "mỗi chiều thứ sáu 5h đá bóng", "đóng tiền nhà ngày 5 mỗi tháng" |
| Hằng năm (dương lịch) | "sinh nhật mẹ 20/11 hằng năm", "kỷ niệm ngày cưới 2/9 mỗi năm" |
| Âm lịch hằng năm | "giỗ ông nội 15/8 âm lịch" |
| Âm lịch hằng tháng | "cúng rằm mỗi tháng", "ăn chay mùng 1 hàng tháng" |
| Nhắc trước | "đi đám cưới chủ nhật 11h trưa, nhắc tôi trước 1 ngày", thêm "báo trước 30 phút" vào cuối câu |

Mẹo:

- Không nói giờ thì app lưu thành việc **cả ngày**.
- Gõ không dấu ("hop 3h chieu mai") hay gõ tắt giờ ("9g sáng", "7g30 tối", "9 rưỡi sáng") app vẫn hiểu. Riêng "gói 4g", "sim 5g" được giữ nguyên là tên việc. Tên tháng âm lịch gõ không dấu cũng hiểu: "gio ong mung 8 thang chap", "di chua mung 1 thang gieng". Muốn ghi năm âm lịch thì đặt sau chữ "âm lịch": "giỗ ông 8/12 âm lịch 2026".
  "ram tháng 7" (thiếu dấu) được hiểu là rằm tháng 7 âm lịch; nếu câu có dấu ở chỗ khác, app hiểu là rằm và hiện một dòng nhắc để bạn kiểm tra.
- Giờ nói ngược thói quen của buổi ("3 giờ tối", "15h sáng", "9h chiều") vẫn được đặt theo luật (15:00, 15:00, 21:00) nhưng bản nháp có dòng nhắc kiểm tra lại. "12h tối nay" là nửa đêm (0:00 sáng hôm sau).
- Mỗi câu một việc. Muốn nhắc cả mùng 1 và rằm thì tạo hai việc.
- "Bữa hổm" là nói chung chung, app tạm hiểu là 3 ngày trước và báo cho bạn biết để sửa lại nếu cần.
- App học cách nói của bạn: khi bạn xác nhận một câu mà Trợ lý AI giúp hiểu, lần sau nói giống vậy app tự hiểu, không cần hỏi AI nữa.

## 4. Nhập bằng giọng nói

Chỉ có khi đã bật "Nhập bằng giọng nói" trong Config.

1. Bấm nút micro cạnh ô nhập. Trình duyệt hỏi quyền dùng micro, bấm **Cho phép**.
2. Nói câu cần nhớ, rồi bấm micro lần nữa khi nói xong (tối đa 20 giây).
3. Chữ nhận được điền vào ô và được hiểu như khi gõ tay.

Lần đầu sau khi bật, app tải mô hình giọng nói (khoảng 1,6 GB). Dưới ô nhập có thanh tiến độ (phần trăm, số MB). Trong lúc đó bạn cứ gõ tay bình thường. Nếu mất mạng giữa chừng, app tự thử tải lại sau khoảng một phút, không cần khởi động lại.

Nếu máy nghe sai một chữ, bạn sửa chữ đó trong ô rồi bấm mũi tên. App ghi nhớ cặp "nghe sai → sửa đúng"; khi bạn sửa cùng một lỗi đủ 2 lần, các lần sau app tự sửa.

App cũng tự sửa sẵn một số chữ hay bị nghe lệch theo giọng vùng miền, nhưng chỉ khi đứng cạnh giờ hoặc ngày nên không đụng tới từ thật: "ba dờ triều mai" thành "3 giờ chiều mai", "12 giờ chưa" thành "12 giờ trưa", "6 giờ xáng", "4 giờ rưởi", "30 phút nửa" (nữa), "tuần xau", "tối nai", "mõi ngày", "chủ nhựt", "giổ ông".

## 5. Xem, sửa, xóa việc

- Mục **Sắp tới** hiện các việc trong 7 ngày tới, chia theo ngày. Việc lặp có vạch màu riêng, việc âm lịch có màu khác.
- Nút **bút chì**: sửa việc đã lưu. Việc âm lịch giữ nguyên ngày âm, chỉ sửa được tên, giờ và nhắc trước.
- Nút **thùng rác**: xóa việc. App hỏi lại trong một hộp nhỏ (mặc định chọn *Hủy*; bấm *Esc* hoặc bấm ra ngoài cũng là hủy). Với việc lặp, xóa là xóa cả chuỗi. Xóa nhầm? Ngay sau khi xóa có thanh **Đã xóa … · Hoàn tác** trong khoảng 10 giây: bấm *Hoàn tác* để lấy lại việc đó.
- Nút **mũi tên tải xuống**: tải việc đó thành tệp `.ics`. Mở tệp (hoặc gửi sang điện thoại rồi mở) để thêm việc vào Lịch Google, Lịch iPhone, Outlook. Việc lặp mỗi ngày/tuần/tháng/năm được thêm thành chuỗi lặp; việc âm lịch được thêm 10 lần tới (ứng dụng lịch không hiểu âm lịch).
- Việc lưu xa hơn 7 ngày không hiện trong Sắp tới, nhưng vẫn được nhắc đúng hẹn.

## 6. Nhắc việc

- Khi đến giờ (hoặc đến lúc nhắc trước), đầu trang hiện thông báo "Đến giờ: …" hoặc "Còn N ngày: …". Bấm **Đã biết** để tắt.
- Thông báo trong trang chỉ hiện khi app đang mở trong trình duyệt. Hãy để một thẻ app mở nếu bạn muốn được nhắc.
- **Thông báo trên máy**: lần đầu mở app, đầu trang hỏi "Bật thông báo trên máy?". Bấm **Bật thông báo** rồi chọn *Cho phép* khi trình duyệt hỏi. Từ đó, tới giờ nhắc máy hiện thông báo ở góc màn hình kể cả khi bạn đang làm việc ở cửa sổ khác; bấm **Đã biết** ngay trên thông báo là xong. Bấm **Để sau** nếu chưa muốn; bật lại bất cứ lúc nào trong mục **Thông báo và cài app lên máy** ở cuối trang (có nút **Thử một thông báo**).
- Lỡ bấm *Chặn*: bấm biểu tượng ổ khóa cạnh địa chỉ trang, cho phép Thông báo rồi tải lại trang.
- Thông báo trên máy vẫn cần app đang mở (một thẻ trình duyệt, hoặc cửa sổ app đã cài, thu nhỏ cũng được).

### Cài app lên máy

Trong Chrome hoặc Edge, mục **Thông báo và cài app lên máy** có nút **Cài app lên máy** (hoặc bấm biểu tượng cài đặt ở cuối thanh địa chỉ). App sẽ có biểu tượng riêng trên màn hình nền/thanh tác vụ và mở trong cửa sổ riêng, gọn như một phần mềm. Dữ liệu vẫn nằm trong app ở Pi Desktop; nếu app trong Pi Desktop đang tắt, cửa sổ sẽ báo "App chưa chạy" kèm nút **Thử lại**.

### Đồng bộ sang ứng dụng lịch trên máy

Mục **Đồng bộ sang ứng dụng lịch khác** ở cuối trang cho một địa chỉ đăng ký lịch (bấm **Chép địa chỉ**). Dán vào Outlook (*Thêm lịch → Từ Internet*), Thunderbird hoặc Lịch của macOS **trên cùng máy** để ứng dụng đó tự cập nhật các việc mỗi giờ. Đồng bộ một chiều: sửa trong ứng dụng lịch không làm đổi việc trong app. Điện thoại và Google Lịch không đọc được địa chỉ này vì app chỉ mở trong máy (127.0.0.1); với điện thoại hãy dùng nút tải `.ics` cạnh từng việc.
- Nếu máy tắt lúc đến giờ, lần mở sau app nhắc bù: việc một lần và ngày giỗ bị lỡ trong 7 ngày gần nhất; việc lặp mỗi ngày/tuần/tháng chỉ nhắc bù lần của hôm trước.
- Việc lưu với giờ đã qua không bị nhắc.

### Cài đặt cá nhân

Mục **Cài đặt cá nhân** ở cuối trang:

- **Tên gọi**: app chào theo tên và theo buổi ở đầu trang ("Chào buổi sáng, Lan!") kèm số việc hôm nay. Bỏ dấu **Hiện lời chào** nếu không muốn.
- **Nhắc trước mặc định**: câu không nói "nhắc trước" thì app tự nhắc sớm chừng đó (bản nháp ghi rõ "theo Cài đặt cá nhân"). Câu có nói thì theo câu.
- **Giờ nhắc việc cả ngày**: việc không có giờ (sinh nhật, nộp thuế…) được nhắc lúc mấy giờ, mặc định 8:00 sáng.
- **Nhắc giỗ sớm**: giỗ và việc âm lịch hằng năm được nhắc thêm trước 7 ngày và 1 ngày để kịp chuẩn bị. Bỏ dấu chọn nếu chỉ muốn nhắc đúng ngày.

Cài đặt nằm trong tệp sao lưu. Khôi phục vào app mới cài thì lấy lại cài đặt cũ; app đã có cài đặt thì giữ nguyên cài đặt đang dùng.

## 7. Sao lưu và khôi phục

**Gỡ app khỏi Pi Desktop sẽ xóa dữ liệu.** Hãy sao lưu trước khi gỡ, và nên sao lưu định kỳ.

1. Mở mục **Sao lưu và cụm từ đã học** ở cuối trang.
2. Bấm **Tải bản sao lưu**: trình duyệt tải về tệp `lichviet-saoluu.json`. Cất tệp này ở nơi an toàn.
3. Khôi phục: bấm **Khôi phục từ tệp** và chọn tệp sao lưu. Mới cài lại app (chưa có việc nào) thì màn hình chào có sẵn nút **Khôi phục từ tệp**, bấm là mở thẳng hộp chọn tệp. Chọn tệp xong, app hỏi lại một lần (nêu tên tệp) rồi mới nhập; bấm **Hủy** nếu chọn nhầm tệp.

Tệp sao lưu gồm các việc, cụm từ đã học và Cài đặt cá nhân.

Khôi phục chỉ **gộp thêm**, không xóa việc đang có. Việc trùng (cùng tên, cùng giờ, cùng kiểu lặp) được bỏ qua, nên khôi phục hai lần cũng không bị nhân đôi. Tệp hỏng thì app từ chối cả tệp, không nhập nửa chừng.

## 8. Dùng thử trên điện thoại Android qua cáp USB

App chỉ mở trên máy tính (127.0.0.1). Cách an toàn nhất để thử trên điện thoại, kể cả micro và thông báo, là cho điện thoại "mượn" cổng của máy tính qua cáp USB. Không cần đổi cấu hình app, không mở cổng nào ra Wi-Fi. So sánh các cách khác xem [ANDROID_PLAN.md](ANDROID_PLAN.md).

1. **Bật gỡ lỗi USB trên điện thoại**: *Cài đặt → Thông tin điện thoại* → chạm 7 lần vào *Số hiệu bản tạo* (Build number) để mở *Tùy chọn nhà phát triển*. Vào *Cài đặt → Hệ thống → Tùy chọn nhà phát triển* → bật *Gỡ lỗi USB*. Tên mục có thể khác chút tùy hãng.
2. **Cài công cụ `adb` trên máy tính**: tải [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) (gói nhỏ, chỉ cần giải nén), mở cửa sổ lệnh trong thư mục `platform-tools`.
3. **Cắm cáp**, điện thoại hỏi *Cho phép gỡ lỗi USB?* → chọn *Cho phép* (có thể tích *Luôn cho phép từ máy tính này*). Kiểm tra bằng lệnh `adb devices`: phải thấy một dòng có chữ `device` (nếu là `unauthorized` thì mở khóa điện thoại và bấm Cho phép).
4. **Xem số cổng của app**: trên máy tính, địa chỉ app có dạng `http://127.0.0.1:18763`; số sau dấu hai chấm là cổng (mặc định 18763).
5. **Chuyển cổng**: chạy

   ```
   adb reverse tcp:18763 tcp:18763
   ```

   (thay `18763` bằng số cổng của bạn ở cả hai chỗ).
6. **Mở trên điện thoại**: trong Chrome gõ `http://localhost:18763`. Đây là `localhost` nên micro, thông báo và *Thêm vào màn hình chính* đều dùng được, và app không hỏi khóa.

Lưu ý:
- Rút cáp hoặc khởi động lại điện thoại/máy tính thì chạy lại lệnh ở bước 5. Muốn gỡ: `adb reverse --remove-all`.
- Thông báo chỉ tới khi app trên điện thoại đang mở và cáp đang cắm.
- Dùng xong có thể tắt *Gỡ lỗi USB* để an toàn hơn.

## 9. Câu hỏi thường gặp

**Mở http://127.0.0.1:18763 không được?**
Kiểm tra app đang chạy trong Pi Desktop. Nếu lúc cài bạn chọn cổng khác thì đổi số cuối địa chỉ. Nếu app vừa cài, chờ thêm vài giây rồi tải lại trang.

**Trang báo "Mất kết nối với app, đang thử lại…"?**
App đã dừng hoặc đang khởi động lại. Trang tự nối lại và tải lại danh sách khi app chạy trở lại; muốn thử ngay thì bấm **Thử lại** trên thanh báo. Nếu lâu không được, khởi động lại app trong Pi Desktop. Nếu thanh báo ghi "App đang gặp sự cố: Không dùng được database…" thì app vẫn chạy nhưng không ghi được dữ liệu: làm theo lý do ghi trong câu (giải phóng ổ đĩa, sửa quyền thư mục) rồi khởi động lại app.

**App không chạy, log báo "Không dùng được database…"?**
Thư mục dữ liệu `./data` của app không ghi được (thiếu quyền, đầy ổ đĩa) hoặc tệp bị hỏng. Câu báo lỗi trong log nói rõ lý do. Giải phóng ổ đĩa hoặc sửa quyền thư mục rồi khởi động lại app.

**Bấm micro báo "Nhập bằng giọng nói chưa bật"?**
Vào Config của app, chọn "Nhập bằng giọng nói" (hoặc "Cả giọng nói và Trợ lý AI") rồi lưu.

**Bấm micro báo "Chưa được cấp quyền micro"?**
Bấm biểu tượng ổ khóa cạnh thanh địa chỉ trình duyệt, cho phép micro rồi tải lại trang.

**Mở app bằng địa chỉ `http://192.168…` thì micro, thông báo, cài app đều tắt?**
Đúng vậy: trình duyệt chỉ cho các tính năng này trên trang `localhost` hoặc `https://`. App sẽ báo rõ khi bạn bấm micro và trong mục *Thông báo và cài app lên máy*. Gõ câu, xem lịch và nhắc trong trang vẫn dùng được. Muốn đủ tính năng trên điện thoại, dùng cáp USB theo mục 8.

**App không hiểu câu của tôi?**
App báo còn thiếu "việc cần làm" hoặc "ngày giờ". Nói rõ hơn, ví dụ "họp 3h chiều mai". Bật Trợ lý AI trong Config sẽ giúp hiểu những câu khó hơn.

**Sinh nhật có tự lặp hằng năm không?**
Có. Câu có chữ *sinh nhật*, *kỷ niệm* hoặc *thôi nôi* kèm ngày (không ghi năm) được đặt lặp hằng năm theo dương lịch, ví dụ "sinh nhật mẹ 20/11"; bản nháp có dòng nhắc để bạn biết, chỉ một lần thì bấm Sửa và chọn *Không lặp*. Việc khác muốn lặp hằng năm thì thêm "hằng năm" hoặc "mỗi năm", hoặc chọn *Mỗi năm* trong ô Lặp khi sửa. Sinh nhật 29/2: năm không nhuận nhắc vào 28/2. Sinh nhật âm lịch thì thêm "âm lịch": "sinh nhật bà 10/3 âm lịch".

**Dùng trên điện thoại được không?**
App chỉ mở được trên chính máy cài Pi Desktop (địa chỉ 127.0.0.1), để dữ liệu không lộ ra mạng. Muốn có việc trên lịch điện thoại, bấm nút tải `.ics` cạnh việc đó rồi gửi tệp sang điện thoại và mở. Muốn thử app (cả giọng nói) từ điện thoại Android: cắm cáp USB và dùng `adb reverse` theo mục 8 ở trên; đừng mở cổng app ra Wi-Fi.

**Trang hiện "Nhập khóa để mở lịch"?**
Bạn đang mở app từ một máy khác (điện thoại qua mạng nội bộ hoặc Tailscale) và người cài app đã đặt khóa bảo vệ. Nhập đúng khóa đó (giá trị `LICHVIET_API_KEY`) một lần, trình duyệt sẽ nhớ. Trên chính máy cài app hoặc qua cáp USB (`adb reverse`) thì không bị hỏi.

**Không thấy thông báo trên máy dù đã bật?**
Kiểm tra app còn mở (một thẻ hoặc cửa sổ app đã cài). Trên Windows, xem *Cài đặt → Hệ thống → Thông báo* đã cho phép Chrome/Edge chưa, và chế độ *Không làm phiền* có đang bật không.

**Dữ liệu có bị gửi lên mạng không?**
Không. Lịch, nhắc việc, giọng nói và Trợ lý AI đều chạy trên máy của bạn. Mạng chỉ cần khi tải mô hình lần đầu.
