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
| Sau một khoảng | "gọi điện cho mẹ 30 phút nữa", "trả sách 2 ngày nữa" |
| Ngày đã qua (ghi lại) | "hôm kia", "hôm qua", "bữa hổm", "3 ngày trước", "tuần trước" |
| Lặp mỗi ngày/tuần/tháng | "uống thuốc 7h tối mỗi ngày", "họp nhóm 9h thứ hai hằng tuần", "đóng tiền nhà ngày 5 mỗi tháng" |
| Hằng năm (dương lịch) | "sinh nhật mẹ 20/11 hằng năm", "kỷ niệm ngày cưới 2/9 mỗi năm" |
| Âm lịch hằng năm | "giỗ ông nội 15/8 âm lịch" |
| Âm lịch hằng tháng | "cúng rằm mỗi tháng", "ăn chay mùng 1 hàng tháng" |
| Nhắc trước | "đi đám cưới chủ nhật 11h trưa, nhắc tôi trước 1 ngày", thêm "báo trước 30 phút" vào cuối câu |

Mẹo:

- Không nói giờ thì app lưu thành việc **cả ngày**.
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

## 5. Xem, sửa, xóa việc

- Mục **Sắp tới** hiện các việc trong 7 ngày tới, chia theo ngày. Việc lặp có vạch màu riêng, việc âm lịch có màu khác.
- Nút **bút chì**: sửa việc đã lưu. Việc âm lịch giữ nguyên ngày âm, chỉ sửa được tên, giờ và nhắc trước.
- Nút **thùng rác**: xóa việc. Với việc lặp, xóa là xóa cả chuỗi.
- Việc lưu xa hơn 7 ngày không hiện trong Sắp tới, nhưng vẫn được nhắc đúng hẹn.

## 6. Nhắc việc

- Khi đến giờ (hoặc đến lúc nhắc trước), đầu trang hiện thông báo "Đến giờ: …" hoặc "Còn N ngày: …". Bấm **Đã biết** để tắt.
- Thông báo trong trang chỉ hiện khi app đang mở trong trình duyệt. Hãy để một thẻ app mở nếu bạn muốn được nhắc.
- Nếu máy tắt lúc đến giờ, lần mở sau app nhắc bù: việc một lần và ngày giỗ bị lỡ trong 7 ngày gần nhất; việc lặp mỗi ngày/tuần/tháng chỉ nhắc bù lần của hôm trước.
- Việc lưu với giờ đã qua không bị nhắc.

## 7. Sao lưu và khôi phục

**Gỡ app khỏi Pi Desktop sẽ xóa dữ liệu.** Hãy sao lưu trước khi gỡ, và nên sao lưu định kỳ.

1. Mở mục **Sao lưu và cụm từ đã học** ở cuối trang.
2. Bấm **Tải bản sao lưu**: trình duyệt tải về tệp `lichviet-saoluu.json`. Cất tệp này ở nơi an toàn.
3. Khôi phục: bấm **Khôi phục từ tệp** và chọn tệp sao lưu.

Khôi phục chỉ **gộp thêm**, không xóa việc đang có. Việc trùng (cùng tên, cùng giờ, cùng kiểu lặp) được bỏ qua, nên khôi phục hai lần cũng không bị nhân đôi. Tệp hỏng thì app từ chối cả tệp, không nhập nửa chừng.

## 8. Câu hỏi thường gặp

**Mở http://127.0.0.1:18763 không được?**
Kiểm tra app đang chạy trong Pi Desktop. Nếu lúc cài bạn chọn cổng khác thì đổi số cuối địa chỉ. Nếu app vừa cài, chờ thêm vài giây rồi tải lại trang.

**Trang báo "Mất kết nối với app, đang thử lại…"?**
App đã dừng hoặc đang khởi động lại. Trang tự nối lại khi app chạy trở lại. Nếu lâu không được, khởi động lại app trong Pi Desktop.

**App không chạy, log báo "Không dùng được database…"?**
Thư mục dữ liệu `./data` của app không ghi được (thiếu quyền, đầy ổ đĩa) hoặc tệp bị hỏng. Câu báo lỗi trong log nói rõ lý do. Giải phóng ổ đĩa hoặc sửa quyền thư mục rồi khởi động lại app.

**Bấm micro báo "Nhập bằng giọng nói chưa bật"?**
Vào Config của app, chọn "Nhập bằng giọng nói" (hoặc "Cả giọng nói và Trợ lý AI") rồi lưu.

**Bấm micro báo "Chưa được cấp quyền micro"?**
Bấm biểu tượng ổ khóa cạnh thanh địa chỉ trình duyệt, cho phép micro rồi tải lại trang.

**App không hiểu câu của tôi?**
App báo còn thiếu "việc cần làm" hoặc "ngày giờ". Nói rõ hơn, ví dụ "họp 3h chiều mai". Bật Trợ lý AI trong Config sẽ giúp hiểu những câu khó hơn.

**Sinh nhật có tự lặp hằng năm không?**
Có. Câu có chữ *sinh nhật*, *kỷ niệm* hoặc *thôi nôi* kèm ngày (không ghi năm) được đặt lặp hằng năm theo dương lịch, ví dụ "sinh nhật mẹ 20/11"; bản nháp có dòng nhắc để bạn biết, chỉ một lần thì bấm Sửa và chọn *Không lặp*. Việc khác muốn lặp hằng năm thì thêm "hằng năm" hoặc "mỗi năm", hoặc chọn *Mỗi năm* trong ô Lặp khi sửa. Sinh nhật 29/2: năm không nhuận nhắc vào 28/2. Sinh nhật âm lịch thì thêm "âm lịch": "sinh nhật bà 10/3 âm lịch".

**Dùng trên điện thoại được không?**
App chỉ mở được trên chính máy cài Pi Desktop (địa chỉ 127.0.0.1), để dữ liệu không lộ ra mạng.

**Dữ liệu có bị gửi lên mạng không?**
Không. Lịch, nhắc việc, giọng nói và Trợ lý AI đều chạy trên máy của bạn. Mạng chỉ cần khi tải mô hình lần đầu.
