PAGE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trợ lý thời gian</title>
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#14231f">
<link rel="icon" href="/icon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/icon-192.png">
<style>
:root{--bg:#f3f1ec;--card:#fffdf9;--tx:#1d1b18;--mut:#78716c;--line:#e7e2d9;--acc:#c2410c;--acc2:#ea580c;--accsoft:#fff1e7;--ink:#14231f;--ink2:#1f3a33;--gold:#f5c26b;--warn:#9a3412;--warnbg:#ffedd5;--ok:#166534;--okbg:#e3f5e8;--sh:0 1px 2px rgba(28,25,23,.04),0 10px 30px -12px rgba(28,25,23,.18)}
@media(prefers-color-scheme:dark){:root{--bg:#121110;--card:#1c1a18;--tx:#f2eee8;--mut:#a8a29e;--line:#2e2a26;--acc:#fb923c;--acc2:#fdba74;--accsoft:#2d1d12;--ink:#0d1a17;--ink2:#17322b;--warn:#fdba74;--warnbg:#3a2412;--ok:#86efac;--okbg:#12291b;--sh:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:720px;margin:0 auto;padding:20px 16px 56px}
/* ---- tờ lịch hôm nay ---- */
.hero{border:1px solid rgba(255,255,255,.06);position:relative;overflow:hidden;border-radius:22px;padding:22px 24px 36px;color:#f8f4ec;background:radial-gradient(120% 140% at 100% 0%,var(--ink2) 0%,var(--ink) 60%);box-shadow:var(--sh);display:flex;align-items:center;gap:22px}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(245,194,107,.28),transparent 65%)}
.big{font:700 64px/1 Georgia,"Times New Roman",serif;color:var(--gold);letter-spacing:-2px}
.hero .wd{font-size:20px;font-weight:600}
.hero .mo{opacity:.75;font-size:14px}
.lunar{margin-left:auto;text-align:right;position:relative;z-index:1;padding-left:18px;border-left:1px solid rgba(255,255,255,.15)}
.lunar .l1{font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.6}
.lunar .l2{font:600 22px/1.2 Georgia,serif;color:var(--gold)}
.lunar .l3{font-size:13px;opacity:.75}
/* ---- ô nhập ---- */
.composer{margin-top:-14px;position:relative;z-index:2;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:10px 10px 10px 16px;box-shadow:var(--sh);display:flex;align-items:flex-end;gap:8px;margin-left:12px;margin-right:12px}
textarea{flex:1;border:0;outline:none;resize:none;background:transparent;color:var(--tx);font:inherit;font-size:16px;line-height:1.5;padding:8px 0;min-height:40px;max-height:160px}
textarea::placeholder{color:var(--mut)}
.ib{flex:none;width:44px;height:44px;border-radius:14px;border:0;display:grid;place-items:center;cursor:pointer;transition:transform .08s,filter .15s,background .15s}
.ib svg{width:20px;height:20px}
.ib:active{transform:scale(.95)}
#mic{background:var(--accsoft);color:var(--acc)}
#mic[data-soon]{opacity:.55}
#go{background:linear-gradient(135deg,var(--acc2),var(--acc));color:#fff}
#go:disabled{filter:grayscale(.5);opacity:.7;cursor:default}
#go.busy svg{animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.chips{display:flex;gap:8px;overflow-x:auto;padding:12px 12px 2px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;font-family:inherit;font-weight:500;font-size:13px;line-height:1;padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--tx);cursor:pointer}
.chip:hover{border-color:var(--acc);color:var(--acc)}
.toast{font-size:13px;color:var(--mut);padding:6px 14px 0}.toast:empty{display:none}
.vstat{margin:10px 12px 0;font-size:13px;color:var(--mut)}.vstat[hidden],.banner[hidden]{display:none}
.pbar{height:6px;border-radius:6px;background:var(--line);overflow:hidden;margin-top:6px}
.pbar i{display:block;height:100%;width:0;background:var(--acc);transition:width .4s}
.pbar.wait i{width:30%!important;animation:slide 1.4s ease-in-out infinite}
@keyframes slide{from{transform:translateX(-100%)}to{transform:translateX(340%)}}
/* ---- bản nháp ---- */
.draft{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:16px;padding:16px 18px;box-shadow:var(--sh);animation:up .25s ease}
@keyframes up{from{opacity:0;transform:translateY(6px)}}
.who{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--acc);font-weight:700;margin-bottom:6px}
.dt{font-size:20px;font-weight:700;margin:0 0 10px}
.facts{display:grid;gap:6px}
.fact{display:flex;align-items:center;gap:10px;font-size:14.5px}
.fact svg{width:18px;height:18px;color:var(--mut);flex:none}
.tags{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.tag{font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:var(--accsoft);color:var(--acc)}
.note{background:var(--warnbg);color:var(--warn);border-radius:12px;padding:9px 12px;margin-top:10px;font-size:14px}
.saved{background:var(--okbg);color:var(--ok);border-radius:12px;padding:10px 14px;font-size:14.5px}
.ai{font-size:12.5px;color:var(--mut);margin-top:10px}
.actions{display:flex;gap:8px;margin-top:14px}
.edit .fl{display:grid;gap:4px;font-size:13px;color:var(--mut);margin-top:10px}
.edit input,.edit select{font:inherit;font-size:16px;color:var(--tx);background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:9px 12px;width:100%;min-width:0}
.edit .erow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.edit .ck{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:14.5px}
.edit .ck input{width:18px;height:18px;margin:0}
.edit .ai{margin:10px 0 0}
.edit [hidden]{display:none!important}
@media(max-width:480px){.edit .erow{grid-template-columns:1fr}}
.btn{border:0;border-radius:12px;padding:10px 22px;font-family:inherit;font-weight:600;font-size:15px;cursor:pointer;background:var(--tx);color:var(--bg)}
.btn.ghost{background:transparent;color:var(--mut);border:1px solid var(--line);font-weight:500}
.btn:disabled{opacity:.5}
.btn.danger{background:#b91c1c;color:#fff}
dialog.ask{border:1px solid var(--line);border-radius:18px;padding:0;background:var(--card);color:var(--tx);box-shadow:var(--sh);width:min(92vw,400px)}
dialog.ask::backdrop{background:rgba(20,18,16,.45)}
dialog.ask form{padding:20px 20px 16px}
dialog.ask h2{font-size:17px;margin:0 0 6px;overflow-wrap:anywhere}
dialog.ask p{margin:0;color:var(--mut);font-size:14px}
dialog.ask .actions{justify-content:flex-end}
dialog.ask .btn{min-height:44px}
/* ---- nhắc ---- */
.banner svg{width:20px;height:20px;flex:none}.banner{display:flex;align-items:center;gap:12px;background:var(--warnbg);color:var(--warn);border-radius:16px;padding:12px 14px;margin:14px 0 0}
.banner .x{flex:1}.banner.ntf{flex-wrap:wrap;background:var(--accsoft);color:var(--tx)}.banner.ntf button{min-height:40px}.banner button{border:1px solid currentColor;background:transparent;color:inherit;border-radius:10px;padding:6px 12px;font-family:inherit;font-weight:600;font-size:13px;cursor:pointer}
/* ---- lịch ---- */
.sec{display:flex;align-items:baseline;justify-content:space-between;margin:28px 4px 8px}
.sec h2{font-weight:700;font-size:18px;line-height:1.2;margin:0}
.sec span{font-size:13px;color:var(--mut)}
#list{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:6px 18px;box-shadow:var(--sh)}
.day{display:flex;align-items:baseline;gap:8px;padding:14px 0 6px;font-weight:700;font-size:14px}
.day small{color:var(--mut);font-weight:500}
.day.today{color:var(--acc)}
.ev{display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid var(--line)}
.ev:last-child{border-bottom:0}
.time{flex:none;width:58px;font-family:inherit;font-weight:700;font-size:15px;font-variant-numeric:tabular-nums}
.time.all{font-size:12px;color:var(--mut);font-weight:600}
.bar{flex:none;width:4px;align-self:stretch;border-radius:4px;background:var(--acc)}
.bar.lunar{background:var(--gold)}.bar.rep{background:#0d9488}
.ev .body{flex:1;min-width:0}.ev b{display:block;font-weight:600;overflow-wrap:anywhere}
.ev .t{color:var(--mut);font-size:13px}
.del{flex:none;border:0;background:transparent;color:var(--mut);cursor:pointer;width:34px;height:34px;border-radius:10px;display:grid;place-items:center;opacity:.6}
.del.ed:hover,.del.dl:hover{background:var(--line);color:var(--tx)}
.del:hover{background:var(--warnbg);color:var(--warn);opacity:1}
.del svg{width:17px;height:17px}
.empty{color:var(--mut);text-align:center;padding:26px 0}
details.more{margin-top:22px;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:4px 18px;box-shadow:var(--sh)}
details.more summary{cursor:pointer;padding:14px 0;font-weight:700;font-size:15px}
details.more .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:6px 0 14px}
details.more p{color:var(--mut);font-size:13px;margin:0 0 10px}
details.more ul{margin:0 0 14px;padding-left:20px;font-size:14px}details.more li{margin:3px 0}details.more h3{font-size:14px;margin:12px 0 4px}
.welcome{margin-top:18px;background:var(--accsoft);border:1px solid var(--line);border-radius:20px;padding:16px 18px}
.welcome h2{font-size:17px;margin:0 0 6px}.welcome p{margin:0 0 10px;font-size:14px}
.welcome .wrs{margin:12px 0 0;font-size:13px;color:var(--mut)}.lnk{background:none;border:0;padding:4px 2px;font:inherit;color:var(--acc);text-decoration:underline;cursor:pointer;min-height:32px}
.welcome .tries{display:flex;flex-wrap:wrap;gap:8px}.welcome .chip{background:var(--card)}
.ph{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:14px}
.ph .x{flex:1;min-width:0;overflow-wrap:anywhere}.ph small{color:var(--mut)}
.greet{margin:0 6px 12px;font-size:17px;font-weight:600}.greet small{display:block;font-size:13px;font-weight:400;color:var(--mut)}.greet[hidden]{display:none}
details.more .fl{display:grid;gap:4px;font-size:13px;color:var(--mut);margin:0 0 10px}
details.more .fl input,details.more .fl select{font:inherit;font-size:16px;color:var(--tx);background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:9px 12px;width:100%;min-width:0;min-height:44px}
details.more .ck{display:flex;align-items:center;gap:8px;margin:0 0 10px;font-size:14.5px}details.more .ck input{width:20px;height:20px;margin:0}
.foot{text-align:center;color:var(--mut);font-size:12px;padding:18px 0 6px}
.mic-on{background:var(--warn)!important;color:#fff!important}
@media(max-width:480px){.hero{padding:18px}.big{font-size:52px}.lunar .l2{font-size:18px}.composer{margin-left:4px;margin-right:4px}}
</style></head><body><main>
<p class="greet" id="greet" hidden aria-live="polite"></p>
<section class="hero"><div class="big" id="dnum"></div><div><div class="wd" id="dwd"></div><div class="mo" id="dmo"></div></div>
<div class="lunar"><div class="l1">Âm lịch</div><div class="l2" id="lday">&nbsp;</div><div class="l3" id="lyear"></div></div></section>
<div class="composer">
<textarea id="q" rows="1" placeholder="Nói hoặc gõ việc cần nhớ…"></textarea>
<button class="ib" id="mic" type="button" title="Nói" aria-label="Nói"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v4"/></svg></button>
<button class="ib" id="go" type="button" title="Hiểu câu này (Enter)" aria-label="Hiểu câu này"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
</div>
<div class="chips" id="chips"></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="vstat" id="vstat" hidden role="status" aria-live="polite"><div class="vt" id="vtxt"></div><div class="pbar"><i id="vbar"></i></div></div>
<section class="banner ntf" id="keybar" hidden aria-labelledby="keyh"><div class="x"><b id="keyh">Nhập khóa để mở lịch</b><br>Bạn đang mở app từ máy khác trong mạng. Chủ máy đã đặt khóa bảo vệ (LICHVIET_API_KEY), hãy nhập khóa đó. Trình duyệt này sẽ nhớ khóa, trên chính máy cài app thì không cần.<div id="keymsg" role="alert"></div></div>
<form id="keyf" class="row"><input id="keyin" type="password" autocomplete="current-password" aria-label="Khóa của app" placeholder="Khóa của app"><button type="submit">Mở khóa</button></form></section>
<div class="banner" id="net" hidden role="alert">⚠<div class="x" id="nettxt">Mất kết nối với app, đang thử lại… Nếu lâu không được, kiểm tra app trong Pi Desktop.</div><button type="button" id="netre">Thử lại</button></div>
<div class="banner ntf" id="undo" hidden role="status"><div class="x" id="undotxt"></div><button type="button" id="undobtn">Hoàn tác</button></div>
<section class="banner ntf" id="ntf" hidden aria-labelledby="ntfh"><div class="x"><b id="ntfh">Bật thông báo trên máy?</b><br>Tới giờ nhắc, máy sẽ hiện thông báo kể cả khi bạn đang mở cửa sổ khác. Trình duyệt sẽ hỏi bạn cho phép.</div>
<button type="button" id="ntfok">Bật thông báo</button><button type="button" id="ntfno">Để sau</button></section>
<div id="due"></div>
<div id="draft" hidden></div>
<section class="welcome" id="welcome" hidden aria-labelledby="wh"><h2 id="wh">Chào bạn, mình là trợ lý thời gian</h2>
<p>Bạn cứ gõ hoặc nói việc cần nhớ như nói với người nhà, có ngày giờ là được. Mình hiểu cả âm lịch và sẽ nhắc khi tới giờ. Mình luôn hỏi lại trước khi lưu.</p>
<p>Bấm thử một câu dưới đây:</p><div class="tries" id="tries"></div>
<p class="wrs">Cài lại app và có bản sao lưu cũ? <button class="lnk" id="wrs" type="button">Khôi phục từ tệp</button></p></section>
<div class="sec"><h2>Sắp tới</h2><span>7 ngày</span></div>
<div id="list"></div>
<details class="more" id="help"><summary>Hướng dẫn nhanh</summary>
<p>Gõ hoặc nói một câu có việc cần làm và thời gian, bấm mũi tên (hoặc Enter). Trợ lý đưa ra bản nháp để bạn Lưu, Sửa hoặc Bỏ qua.</p>
<h3>Giờ và ngày</h3><ul><li><q>họp 3h chiều mai</q>, <q>đón con 4h rưỡi chiều nay</q>, <q>họp 3h kém 15 chiều mai</q></li>
<li><q>đi chợ 8h sáng thứ bảy</q>, <q>đi khám thứ năm tuần sau 9h</q>, <q>nộp báo cáo 17h ngày 25/10</q></li>
<li><q>gọi điện cho mẹ 30 phút nữa</q>, <q>trả sách 2 ngày nữa</q>, <q>tái khám 3 tháng nữa</q>. Không nói giờ thì lưu thành việc cả ngày.</li>
<li><q>họp từ 2h đến 4h chiều mai</q> (tự tính thời lượng), <q>xem bóng nửa đêm nay</q>, <q>đi chùa ngày 5 tháng tới</q></li></ul>
<h3>Lặp lại</h3><ul><li><q>uống thuốc 7h tối mỗi ngày</q>, <q>họp nhóm 9h thứ hai hằng tuần</q>, <q>đóng tiền nhà ngày 5 mỗi tháng</q></li>
<li><q>sinh nhật mẹ 20/11 hằng năm</q> (dương lịch). Nói <i>sinh nhật</i> hay <i>kỷ niệm</i> kèm ngày thì tự lặp hằng năm.</li></ul>
<h3>Âm lịch</h3><ul><li><q>giỗ ông nội 15/8 âm lịch</q> (lặp hằng năm theo âm lịch)</li><li><q>cúng rằm mỗi tháng</q>, <q>ăn chay mùng 1 hàng tháng</q></li></ul>
<h3>Nhắc trước</h3><ul><li><q>đi đám cưới chủ nhật 11h trưa, nhắc tôi trước 1 ngày</q>, hoặc thêm <i>báo trước 30 phút</i> vào cuối câu</li></ul>
<h3>Mẹo</h3><ul><li>Mỗi câu một việc. Muốn nhắc cả <i>mùng 1 và rằm</i> thì tạo thành hai việc.</li>
<li>Nút bút chì để sửa, nút thùng rác để xóa, nút mũi tên để tải việc về lịch điện thoại (.ics).</li>
<li>Thông báo nhắc hiện ở đầu trang khi app đang mở. Bấm <i>Đã biết</i> để tắt. Bật <i>thông báo trên máy</i> để được nhắc cả khi đang ở cửa sổ khác.</li>
<li>Muốn lúc nào cũng được nhắc sớm (ví dụ 15 phút), hoặc đổi giờ nhắc việc cả ngày: mở <i>Cài đặt cá nhân</i> ở cuối trang.</li>
<li>Tải bản sao lưu thường xuyên, nhất là trước khi gỡ app.</li></ul></details>
<details class="more" id="me"><summary>Cài đặt cá nhân</summary>
<p>Lưu trong app trên máy này và có trong tệp sao lưu.</p>
<form id="mef" novalidate>
<label class="fl">Tên gọi của bạn (để chào hỏi)<input id="me_name" type="text" maxlength="40" autocomplete="nickname" placeholder="Ví dụ: Lan"></label>
<label class="ck"><input id="me_greet" type="checkbox" checked> Hiện lời chào ở đầu trang</label>
<label class="fl">Nhắc trước mặc định (khi câu không nói nhắc trước)<select id="me_rm">
<option value="0">Không, nhắc đúng giờ</option><option value="5">5 phút</option><option value="10">10 phút</option><option value="15">15 phút</option><option value="30">30 phút</option><option value="60">1 tiếng</option><option value="120">2 tiếng</option><option value="1440">1 ngày</option></select></label>
<label class="fl">Giờ nhắc việc cả ngày (việc không có giờ)<select id="me_ad"></select></label>
<div class="row"><button class="btn" type="submit">Lưu cài đặt</button><span id="memsg" role="status" aria-live="polite" style="font-size:13px;color:var(--mut)"></span></div>
</form></details>
<details class="more" id="set"><summary>Thông báo và cài app lên máy</summary>
<p id="ntfst" aria-live="polite"></p>
<div class="row"><button class="btn" type="button" id="ntfbtn" hidden>Bật thông báo</button><button class="btn ghost" type="button" id="ntftest" hidden>Thử một thông báo</button></div>
<p>Thông báo chỉ hiện khi app đang mở trong trình duyệt hoặc đã cài lên máy (có thể thu nhỏ cửa sổ). Tắt hẳn trình duyệt thì nhắc sẽ hiện ở đầu trang lần mở sau.</p>
<p id="instx">Cài app lên máy để mở nhanh như một phần mềm riêng: trong Chrome hoặc Edge, bấm biểu tượng cài đặt ở cuối thanh địa chỉ.</p>
<div class="row"><button class="btn" type="button" id="inst" hidden>Cài app lên máy</button></div>
<p>Nút tải lịch cạnh mỗi việc cho tệp .ics: mở tệp đó để thêm việc vào lịch của điện thoại hoặc Outlook.</p></details>
<details class="more" id="feed"><summary>Đồng bộ sang ứng dụng lịch khác</summary>
<p>Ứng dụng lịch trên <b>chính máy này</b> (Outlook, Thunderbird, Lịch của macOS) có thể đăng ký địa chỉ dưới đây để tự cập nhật mọi việc mỗi giờ. Trong Outlook: <i>Thêm lịch → Từ Internet</i>, dán địa chỉ.</p>
<div class="row"><input id="feedurl" readonly aria-label="Địa chỉ đăng ký lịch" style="flex:1;min-width:0;font:inherit;font-size:14px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--tx)">
<button class="btn ghost" type="button" id="feedcp">Chép địa chỉ</button></div>
<p id="feednote" class="note" hidden></p>
<p>Điện thoại và Google Lịch <b>không</b> đọc được địa chỉ này vì app chỉ mở trên máy tính của bạn (127.0.0.1), không ra mạng ngoài. Với điện thoại, dùng nút tải lịch cạnh từng việc rồi gửi tệp .ics sang máy.</p></details>
<details class="more" id="more"><summary>Sao lưu và cụm từ đã học</summary>
<p>Gỡ app khỏi Pi Desktop sẽ xóa dữ liệu. Hãy tải bản sao lưu trước khi gỡ, rồi khôi phục sau khi cài lại.</p>
<div class="row"><a class="btn" id="bk" href="/export" download="lichviet-saoluu.json" style="text-decoration:none">Tải bản sao lưu</a>
<label class="btn ghost" style="cursor:pointer">Khôi phục từ tệp<input type="file" id="rs" accept="application/json,.json" hidden></label><span id="bkmsg" style="font-size:13px;color:var(--mut)"></span></div>
<p>Cụm từ app đã học từ các lần bạn xác nhận. Xóa cụm nào thì app sẽ hỏi AI lại như lần đầu.</p>
<div id="phl"></div></details>
<footer class="foot" id="ver"></footer>
<dialog class="ask" id="ask" aria-labelledby="ask_t" aria-describedby="ask_d"><form method="dialog"><h2 id="ask_t"></h2><p id="ask_d"></p>
<div class="actions"><button class="btn ghost" value="" id="ask_no">Hủy</button><button class="btn danger" value="ok" id="ask_ok">Đồng ý</button></div></form></dialog>
</main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
/* Gọi API. Lỗi mạng, hết thời gian, mã lỗi đều thành Error có câu tiếng Việt dễ hiểu (e.message), không bao giờ treo nút. */
const NET='Không nối được với app. Kiểm tra app còn đang chạy trong Pi Desktop rồi thử lại.';
/* Mở app từ máy khác trong mạng (địa chỉ thêm qua LICHVIET_ALLOWED_HOSTS) khi chủ máy đã đặt khóa: trang phải gửi khóa.
   Khóa chỉ lưu trong trình duyệt này; trên chính máy cài app thì không cần. */
const KEY={get(){try{return localStorage.getItem('lv_key')||'';}catch(e){return '';}},
  set(v){try{v?localStorage.setItem('lv_key',v):localStorage.removeItem('lv_key');}catch(e){}},
  h(o){const k=KEY.get();return k?{...((o&&o.headers)||{}),'X-Lacviet-Key':k}:((o&&o.headers)||{});},
  ask(){const b=$('keybar');if(!b||!b.hidden)return;b.hidden=false;$('keymsg').textContent=KEY.get()?'Khóa đã lưu không đúng hoặc đã đổi. Nhập lại khóa mới.':'';$('keyin').focus();}};
const j=async(u,o,ms)=>{
  const ac=new AbortController(),t=setTimeout(()=>ac.abort(),ms||60000);let r;
  try{r=await fetch(u,{...(o||{}),headers:KEY.h(o),signal:ac.signal});}
  catch(e){throw new Error(e.name==='AbortError'?'App phản hồi quá lâu, bạn thử lại sau ít phút.':NET);}
  finally{clearTimeout(t);}
  let x=null;try{x=await r.json();}catch(e){}
  if(r.status===401)KEY.ask();
  if(!r.ok||x===null){const er=new Error((x&&x.error)?x.error.charAt(0).toUpperCase()+x.error.slice(1):r.status>=500?'App gặp lỗi bên trong, bạn thử lại sau ít phút.':r.status===401?'App đang bật khóa API, giao diện chưa được cấp quyền.':'Yêu cầu chưa hợp lệ (mã '+r.status+').');er.status=r.status;er.data=x;throw er;}
  return x;};
/* Báo mất kết nối khi các lần tải nền (danh sách, nhắc việc) thất bại; tự ẩn khi nối lại được. */
const NETMSG='Mất kết nối với app, đang thử lại… Nếu lâu không được, kiểm tra app trong Pi Desktop.';
/* App vẫn chạy nhưng database lỗi thì /health trả 503 kèm lý do tiếng Việt: hiện đúng lý do đó thay vì câu chung chung. */
/* Nối lại được sau khi mất kết nối thì tự tải lại danh sách (refresh/due gọi net(true) lúc thanh đã ẩn nên không lặp). */
const net=async ok=>{const b=$('net');if(!b)return;const was=!b.hidden;b.hidden=ok;if(ok){$('nettxt').textContent=NETMSG;if(was){refresh();due();}return;}
  let m=NETMSG;try{await j('/health',null,8000);}catch(e){const x=e.data;if(x&&!x.ok&&x.error)m='App đang gặp sự cố: '+String(x.error).replace(/\.?$/,'.')+' Sửa xong thì khởi động lại app trong Pi Desktop.';}
  if(!b.hidden)$('nettxt').textContent=m;};
(async()=>{try{const x=await j('/info');$('ver').textContent='Lịch Việt phiên bản '+x.version;if(typeof x.events==='number')welcome(x.events);}catch(e){}})();
const p=n=>String(n).padStart(2,'0');
const WD=['Chủ nhật','Thứ hai','Thứ ba','Thứ tư','Thứ năm','Thứ sáu','Thứ bảy'];
const fmtD=iso=>{const d=new Date(iso);return p(d.getDate())+'/'+p(d.getMonth()+1)+(d.getFullYear()!==new Date().getFullYear()?'/'+d.getFullYear():'')};
const fmtT=iso=>{const d=new Date(iso);return p(d.getHours())+':'+p(d.getMinutes())};
const fmt=iso=>fmtD(iso)+' '+fmtT(iso);
const when=(iso,allDay)=>allDay?fmtD(iso)+' cả ngày':fmt(iso);
const whenLong=(iso,allDay)=>{const d=new Date(iso);return WD[d.getDay()]+', '+fmtD(iso)+(allDay?' · cả ngày':' · '+fmtT(iso))};
const local=d=>d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'T00:00:00';
const REP={daily:'mỗi ngày',weekly:'mỗi tuần',monthly:'mỗi tháng',yearly:'mỗi năm',lunar_yearly:'hằng năm'};
const repText=(rep,ld,lm)=>!rep?'':rep==='lunar_yearly'?' · âm lịch '+(ld&&lm?p(ld)+'/'+p(lm)+', ':'')+'hằng năm':rep==='lunar_monthly'?' · âm lịch ngày '+(ld||'')+' hằng tháng':' · '+(REP[rep]||rep);
const svg=d=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+d+'</svg>';
const ICO={cal:svg('<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/>'),
 rep:svg('<path d="M17 2l4 4-4 4M3 11V9a3 3 0 013-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 01-3 3H3"/>'),
 bell:svg('<path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 004 0"/>'),
 x:svg('<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>'),
 dl:svg('<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>'),
 pen:svg('<path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"/>')};
function toast(m){$('toast').textContent=m||'';}
/* ---- cài đặt cá nhân và lời chào ---- */
const mins=m=>m%1440===0?m/1440+' ngày':m%60===0?m/60+' tiếng':m+' phút';
const greetText=(h,name,n)=>{
  const b=h<4||h>=22?'':h<11?'Chào buổi sáng':h<14?'Chào buổi trưa':h<18?'Chào buổi chiều':'Chào buổi tối';
  const hi=b?b+(name?', '+name:'')+'!':'Khuya rồi, '+(name?name+' ':'')+'nghỉ sớm nhé.';
  const sub=n==null?'':n?'Hôm nay có '+n+' việc trong lịch.':'Hôm nay chưa có việc nào trong lịch.';
  return [hi,sub];};
let ME={name:'',greeting:true,default_remind_min:0,all_day_hour:8},TODAYN=null;
const greet=()=>{const g=$('greet');if(!ME.greeting){g.hidden=true;return;}
  const [a,b]=greetText(new Date().getHours(),ME.name,TODAYN);g.innerHTML=esc(a)+(b?'<small>'+esc(b)+'</small>':'');g.hidden=false;};
(()=>{const s=$('me_ad');for(let h=0;h<24;h++)s.add(new Option(p(h)+':00'+(h===8?' (mặc định)':''),String(h)));})();
const fillMe=()=>{$('me_name').value=ME.name||'';$('me_greet').checked=!!ME.greeting;
  const rm=$('me_rm'),v=String(ME.default_remind_min||0);
  if(![...rm.options].some(o=>o.value===v))rm.add(new Option(mins(+v),v));rm.value=v;$('me_ad').value=String(ME.all_day_hour);};
const loadMe=async()=>{try{ME=await j('/settings');}catch(e){}fillMe();greet();};
$('mef').onsubmit=async ev=>{ev.preventDefault();
  const b={name:$('me_name').value.trim(),greeting:$('me_greet').checked,default_remind_min:+$('me_rm').value,all_day_hour:+$('me_ad').value};
  const btn=$('mef').querySelector('button[type=submit]');btn.disabled=true;
  try{ME=await j('/settings',{method:'PATCH',body:JSON.stringify(b)});$('memsg').textContent='Đã lưu cài đặt.';fillMe();greet();}
  catch(e){$('memsg').textContent=e.message;}finally{btn.disabled=false;}};
setInterval(greet,600000);   // đổi lời chào theo buổi khi để trang mở lâu
loadMe();
/* ---- đầu trang: hôm nay ---- */
let TODAY=null;   // ngày hôm nay theo máy chủ (múi giờ người dùng), không theo đồng hồ trình duyệt
(async()=>{let t=new Date();
  try{const x=await j('/today');TODAY=x.date;t=new Date(x.date+'T00:00:00');}catch(e){}
  $('dnum').textContent=p(t.getDate());$('dwd').textContent=WD[t.getDay()];$('dmo').textContent='Tháng '+(t.getMonth()+1)+', '+t.getFullYear();
  try{const x=await j('/today');$('lday').textContent=p(x.lunar_day)+'/'+p(x.lunar_month);$('lyear').textContent='Năm '+x.year_name+(x.leap?' · tháng nhuận':'');}catch(e){}})();
/* ---- giọng nói: chừa sẵn chỗ. Sau này chỉ cần thay Voice.start() bằng bộ nhận giọng thật,
   gọi Voice.onText(câu) khi có kết quả: câu sẽ được điền vào ô và phân tích như gõ tay. ---- */
/* Ghi âm -> WAV 16 kHz mono -> /stt (whisper chạy cục bộ) -> chữ điền vào ô, phân tích như gõ tay. */
const Voice={rec:null,chunks:[],stream:null,on:false,timer:null,
  async start(){
    if(this.on){this.stop();return;}
    let st={};try{st=await j('/stt/status');}catch(e){toast(e.message);return;}
    if(!st.enabled){toast('Nhập bằng giọng nói chưa bật. Vào Config của app, chọn "Nhập bằng giọng nói" rồi lưu.');return;}
    if(!st.ready){toast('Giọng nói chưa sẵn sàng, bạn gõ tạm nhé. Tiến độ hiện ngay bên dưới.');VStat.show(st);VStat.poll();return;}
    if(window.isSecureContext===false){toast(INSECURE);return;}
    if(!navigator.mediaDevices||!window.MediaRecorder){toast('Cửa sổ này không hỗ trợ ghi âm.');return;}
    try{this.stream=await navigator.mediaDevices.getUserMedia({audio:true});}
    catch(e){toast(e.name==='NotFoundError'?'Chưa thấy micro trên máy này.':'Chưa được cấp quyền micro.');return;}
    this.chunks=[];const r=this.rec=new MediaRecorder(this.stream);
    r.ondataavailable=e=>{if(e.data.size)this.chunks.push(e.data);};
    r.onstop=()=>this.done();
    r.start();this.on=true;$('mic').classList.add('mic-on');
    toast('Đang nghe… bấm mic lần nữa khi nói xong.');
    this.timer=setTimeout(()=>this.stop(),20000);
  },
  stop(){clearTimeout(this.timer);if(this.rec&&this.rec.state!=='inactive')this.rec.stop();},
  async done(){
    this.on=false;$('mic').classList.remove('mic-on');
    this.stream.getTracks().forEach(t=>t.stop());
    const blob=new Blob(this.chunks,{type:this.rec.mimeType});
    if(blob.size<2000){toast('Không nghe thấy gì.');return;}
    toast('Đang chuyển thành chữ…');
    try{
      const wav=await Voice.toWav(blob);
      const r=await fetch('/stt',{method:'POST',body:wav,headers:KEY.h({headers:{'Content-Type':'audio/wav'}})});
      const x=await r.json();
      if(!r.ok){toast(x.error||'Nhận giọng nói gặp lỗi.');return;}
      if(!x.text){toast('Không nghe rõ, bạn nói lại giúp mình nhé.');return;}
      toast('');this.onText(x.text);
    }catch(e){toast('Nhận giọng nói gặp lỗi.');}
  },
  async toWav(blob){
    const ac=new (window.AudioContext||window.webkitAudioContext)();
    const buf=await ac.decodeAudioData(await blob.arrayBuffer());ac.close();
    const n=Math.max(1,Math.ceil(buf.duration*16000));
    const oc=new OfflineAudioContext(1,n,16000),src=oc.createBufferSource();
    src.buffer=buf;src.connect(oc.destination);src.start();
    const pcm=(await oc.startRendering()).getChannelData(0);
    const out=new DataView(new ArrayBuffer(44+pcm.length*2));
    const w=(o,t)=>{for(let i=0;i<t.length;i++)out.setUint8(o+i,t.charCodeAt(i));};
    w(0,'RIFF');out.setUint32(4,36+pcm.length*2,true);w(8,'WAVEfmt ');out.setUint32(16,16,true);
    out.setUint16(20,1,true);out.setUint16(22,1,true);out.setUint32(24,16000,true);out.setUint32(28,32000,true);
    out.setUint16(32,2,true);out.setUint16(34,16,true);w(36,'data');out.setUint32(40,pcm.length*2,true);
    for(let i=0;i<pcm.length;i++){const v=Math.max(-1,Math.min(1,pcm[i]));out.setInt16(44+i*2,v<0?v*32768:v*32767,true);}
    return out.buffer;
  },
  last:null,
  onText(text){this.last=text;$('q').value=text;grow();$('go').click();}};
$('mic').onclick=()=>Voice.start();
/* Tiến độ tải mô hình giọng nói lần đầu: hiện thanh tiến độ, hỏi lại mỗi 3 giây tới khi sẵn sàng. */
const VStat={timer:null,
  show(st){
    const box=$('vstat'),bar=$('vbar');
    if(!st.enabled){box.hidden=true;return;}
    if(st.ready){$('vtxt').textContent='Giọng nói đã sẵn sàng, bấm mic để nói.';bar.parentNode.classList.remove('wait');bar.style.width='100%';
      box.hidden=false;setTimeout(()=>{box.hidden=true;},5000);return;}
    $('vtxt').textContent='Giọng nói: '+(st.detail||'đang chuẩn bị');
    const known=typeof st.percent==='number'&&st.phase==='downloading';
    bar.parentNode.classList.toggle('wait',!known);bar.style.width=known?st.percent+'%':'';
    box.hidden=false;},
  poll(){if(this.timer)return;
    const tick=async()=>{let st;try{st=await j('/stt/status',null,8000);}catch(e){this.timer=setTimeout(tick,5000);return;}
      this.show(st);this.timer=st.enabled&&!st.ready?setTimeout(tick,3000):null;};
    this.timer=setTimeout(tick,3000);}};
(async()=>{try{const st=await j('/stt/status',null,8000);if(st.enabled&&!st.ready){VStat.show(st);VStat.poll();}}catch(e){}})();
/* ---- ô nhập ---- */
const grow=()=>{const q=$('q');q.style.height='auto';q.style.height=Math.min(q.scrollHeight,160)+'px';};
$('q').addEventListener('input',grow);
$('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('go').click();}});
const SAMPLES=['họp với anh Nam 3h chiều mai','uống thuốc 7h tối mỗi ngày','giỗ ông nội 15/8 âm lịch','đi khám thứ năm tuần sau 9h'];
$('chips').innerHTML=SAMPLES.map(s=>'<button type="button" class="chip">'+esc(s)+'</button>').join('');
document.querySelectorAll('#chips .chip').forEach(c=>c.onclick=()=>{$('q').value=c.textContent;grow();$('q').focus();});
/* Lần đầu mở (chưa có việc nào): lời chào kèm câu mẫu, bấm là phân tích luôn. Ẩn khi đã có việc. */
const TRIES=['đi chợ 8h sáng thứ bảy','gọi điện cho mẹ 30 phút nữa','cúng rằm mỗi tháng','họp nhóm 9h thứ hai hằng tuần'];
$('tries').innerHTML=TRIES.map(s=>'<button type="button" class="chip">'+esc(s)+'</button>').join('');
document.querySelectorAll('#tries .chip').forEach(c=>c.onclick=()=>{$('q').value=c.textContent;grow();$('go').click();});
const welcome=n=>{$('welcome').hidden=n!==0;};
/* ---- lịch ---- */
function dayHead(key){
  const d=new Date(key+'T00:00:00'),t=TODAY?new Date(TODAY+'T00:00:00'):new Date();t.setHours(0,0,0,0);
  const diff=Math.round((d-t)/864e5),base=WD[d.getDay()]+', '+p(d.getDate())+'/'+p(d.getMonth()+1);
  return '<div class="day'+(diff===0?' today':'')+'">'+(diff===0?'Hôm nay <small>'+base+'</small>':diff===1?'Ngày mai <small>'+base+'</small>':base)+'</div>';
}
async function refresh(){
  if(!TODAY){try{TODAY=(await j('/today')).date}catch(e){}}
  const a=TODAY?new Date(TODAY+'T00:00:00'):new Date(),b=new Date(a);b.setDate(b.getDate()+7);
  let ev;try{ev=await j('/events?from='+local(a)+'&to='+local(b));net(true);}
  catch(e){net(false);if(!$('list').innerHTML)$('list').innerHTML='<div class="empty">Chưa tải được danh sách. '+esc(e.message)+'</div>';return;}
  TODAYN=ev.filter(e=>e.occurrence.slice(0,10)===TODAY).length;greet();
  if(!ev.length){$('list').innerHTML='<div class="empty">Chưa có việc nào trong 7 ngày tới.</div>';return;}
  ev.sort((x,y)=>x.occurrence<y.occurrence?-1:1);
  let html='',cur='';
  ev.forEach(e=>{
    const k=e.occurrence.slice(0,10);
    if(k!==cur){cur=k;html+=dayHead(k);}
    const rep=repText(e.repeat,e.lunar_day,e.lunar_month).replace(/^ · /,'');
    html+='<div class="ev"><div class="time'+(e.all_day?' all':'')+'">'+(e.all_day?'Cả ngày':fmtT(e.occurrence))+'</div>'
      +'<div class="bar'+((e.repeat==='lunar_yearly'||e.repeat==='lunar_monthly')?' lunar':e.repeat?' rep':'')+'"></div>'
      +'<div class="body"><b>'+esc(e.title)+'</b>'+(rep?'<span class="t">'+esc(rep)+'</span>':'')+'</div>'
      +'<a class="del dl" href="/events/'+e.id+'.ics" download title="Tải về lịch điện thoại (.ics)" aria-label="Tải '+esc(e.title)+' về lịch điện thoại">'+ICO.dl+'</a>'
      +'<button class="del ed" title="Sửa" aria-label="Sửa '+esc(e.title)+'" data-id="'+e.id+'">'+ICO.pen+'</button>'
      +'<button class="del" title="Xóa" aria-label="Xóa '+esc(e.title)+'" data-id="'+e.id+'" data-rep="'+(e.repeat||'')+'">'+ICO.x+'</button></div>';
  });
  $('list').innerHTML=html;
  document.querySelectorAll('#list .ed').forEach(btn=>btn.onclick=()=>{
    const e=ev.find(x=>x.id===+btn.dataset.id);if(!e)return;
    const lun=(e.repeat==='lunar_yearly'||e.repeat==='lunar_monthly')&&e.lunar_day?[e.lunar_day,e.lunar_month]:null;
    openEdit({title:e.title,start:e.start,all_day:!!e.all_day,repeat:e.repeat,remind_before_min:e.remind_before_min,
      duration_min:e.duration_min,lunar:lun},()=>show(''),e.id);
    $('draft').scrollIntoView({behavior:'smooth',block:'center'});});
  document.querySelectorAll('#list .del:not(.ed)').forEach(btn=>btn.onclick=async()=>{
    const e=ev.find(x=>x.id===+btn.dataset.id),name=e?e.title:'việc này';
    if(!await ask('Xóa “'+name+'”?',btn.dataset.rep?'Việc này lặp lại: xóa là xóa cả chuỗi, mọi lần tới đều mất.':'Xóa rồi thì không lấy lại được, trừ khi bạn có bản sao lưu.','Xóa'))return;
    try{await j('/events/'+btn.dataset.id,{method:'DELETE'});if(e)Undo.offer(e);else toast('Đã xóa “'+name+'”.');}catch(x){toast('Chưa xóa được: '+x.message);}refresh();});
}
/* Sau khi xóa: thanh "Đã xóa … · Hoàn tác" trong 10 giây; Hoàn tác tạo lại việc từ bản sao giữ ở trang (id mới). */
const undoBody=e=>{const b={title:e.title,start:e.start,all_day:!!e.all_day,repeat:e.repeat||null,
  remind_before_min:e.remind_before_min,duration_min:e.duration_min,notes:e.notes||null};
  if(e.lunar_day)b.lunar=[e.lunar_day,e.lunar_month];return b;};
const Undo={ev:null,t:0,
  offer(e){this.ev=e;$('undotxt').textContent='Đã xóa “'+e.title+'”.';$('undo').hidden=false;$('undobtn').disabled=false;
    clearTimeout(this.t);this.t=setTimeout(()=>this.hide(),10000);},
  hide(){this.ev=null;$('undo').hidden=true;},
  async go(){const e=this.ev;if(!e)return;$('undobtn').disabled=true;
    try{await j('/events',{method:'POST',body:JSON.stringify(undoBody(e))});this.hide();toast('Đã khôi phục “'+e.title+'”.');refresh();}
    catch(x){$('undobtn').disabled=false;toast('Chưa khôi phục được: '+x.message);}}};
$('undobtn').onclick=()=>Undo.go();
/* hộp xác nhận trong trang (thay hộp confirm của trình duyệt): Esc, bấm ra ngoài hoặc Hủy = không; mặc định chọn Hủy cho an toàn */
function ask(title,detail,okLabel){
  const d=$('ask');
  if(!d||typeof d.showModal!=='function')return Promise.resolve(confirm(title+(detail?' '+detail:'')));
  $('ask_t').textContent=title;$('ask_d').textContent=detail||'';$('ask_ok').textContent=okLabel||'Đồng ý';
  const back=document.activeElement;
  return new Promise(res=>{
    d.onclick=e=>{if(e.target===d)d.close('');};
    d.onclose=()=>{d.onclose=null;res(d.returnValue==='ok');if(back&&back.isConnected)back.focus();};
    d.returnValue='';d.showModal();$('ask_no').focus();});
}
async function due(){
  let d;try{d=await j('/reminders/due?channel=ui',null,20000);net(true);}catch(e){net(false);return;}
  const soon=x=>x.kind&&x.kind!=='on_time';
  Notif.push(d,soon);
  $('due').innerHTML=d.map(x=>'<div class="banner">'+ICO.bell+'<div class="x">'+(soon(x)?'Còn '+x.days_left+' ngày: ':'Đến giờ: ')+'<b>'+esc(x.title)+'</b> · '+when(x.occurrence,x.all_day)+'</div><button data-e="'+x.event_id+'" data-o="'+esc(x.key||x.occurrence)+'">Đã biết</button></div>').join('');
  document.querySelectorAll('#due button').forEach(btn=>btn.onclick=async()=>{
    btn.disabled=true;Notif.close(btn.dataset.e+'|'+btn.dataset.o);try{await j('/reminders/ack',{method:'POST',body:JSON.stringify({event_id:+btn.dataset.e,occurrence:btn.dataset.o})});}catch(e){toast(e.message);}due();});
}
/* ---- hiểu câu + lưu ---- */
const conflictNotes=l=>(l||[]).map(c=>'<div class="note">Trùng giờ với <b>'+esc(c.title)+'</b> ('+fmt(c.occurrence)+')</div>').join('');
function show(html,cls){const d=$('draft');d.className=html?(cls||'draft'):'';d.innerHTML=html;d.hidden=!html;}
function showSaved(ev){
  welcome(1);
  const far=(new Date(ev.start)-new Date())>7*864e5;
  show('<div class="saved">'+(ev.duplicate?'Việc này đã có trong lịch, mình không lưu thêm.':'Đã lưu.')+(far?' Lần tới vào '+when(ev.start,ev.all_day)+', xa hơn 7 ngày nên chưa hiện trong danh sách bên dưới.':'')+'</div>'+conflictNotes(ev.conflicts),'draft');
  refresh();due();}
/* ---- sửa bản nháp trước khi lưu: đi qua POST /events (cùng create() với Lưu, có kiểm tra trùng) ---- */
const okDate=s=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);if(!m)return false;const x=new Date(+m[1],+m[2]-1,+m[3]);return x.getMonth()===+m[2]-1&&x.getDate()===+m[3];};
const REPOPT=[['','Không lặp'],['daily','Mỗi ngày'],['weekly','Mỗi tuần'],['monthly','Mỗi tháng'],['yearly','Mỗi năm']];
const REMOPT=[5,10,15,30,60,120,1440,2880,10080];
function remOpts(v){   // chọn nhanh; giá trị lạ (ví dụ 45 phút từ câu nói) vẫn giữ thành một lựa chọn riêng
  v=v||0;const l=REMOPT.slice();if(v&&!l.includes(v))l.push(v);l.sort((a,b)=>a-b);
  return '<option value=""'+(v?'':' selected')+'>Không, nhắc đúng giờ</option>'
    +l.map(m=>'<option value="'+m+'"'+(m===v?' selected':'')+'>'+(m===10080?'1 tuần':mins(m))+'</option>').join('');
}
function openEdit(d,back,id){   // id: sửa việc đã lưu (PATCH); không có id: sửa bản nháp trước khi lưu (POST)
  const lunar=!!d.lunar,st=d.start||'',dateV=st.slice(0,10),timeV=st.slice(11,16);
  const opts=REPOPT.map(([v,l])=>'<option value="'+v+'"'+((d.repeat||'')===v?' selected':'')+'>'+l+'</option>').join('');
  show('<form class="edit" id="ef" novalidate><div class="who">'+(id?'Sửa việc đã lưu':'Sửa việc trước khi lưu')+'</div>'
    +'<label class="fl">Tên việc<input id="e_t" type="text" maxlength="200" value="'+esc(d.title)+'"></label>'
    +'<div class="erow">'+(lunar?'':'<label class="fl">Ngày<input id="e_d" type="date" value="'+dateV+'"></label>')
    +'<label class="fl" id="e_hw">Giờ<input id="e_h" type="time" value="'+timeV+'"></label></div>'
    +'<label class="ck"><input id="e_all" type="checkbox"'+(d.all_day?' checked':'')+'> Cả ngày</label>'
    +(lunar?'<p class="ai">Việc theo âm lịch giữ nguyên ngày âm, nên chỉ sửa được tên, giờ và nhắc trước.</p>'
      :'<label class="fl">Lặp<select id="e_r">'+opts+'</select></label>')
    +'<label class="fl">Nhắc trước<select id="e_m">'+remOpts(d.remind_before_min)+'</select></label>'
    +'<div id="e_cf" aria-live="polite"></div><div class="note" id="e_err" hidden></div>'
    +'<div class="actions"><button class="btn" type="submit">Lưu</button><button class="btn ghost" type="button" id="e_no">Hủy</button></div></form>');
  const f=$('ef'),err=$('e_err'),all=$('e_all'),btn=f.querySelector('button[type=submit]');
  const fail=m=>{err.textContent=m;err.hidden=false;};
  let cfT=0,cfN=0;
  const checkCf=()=>{clearTimeout(cfT);cfT=setTimeout(async()=>{   // báo trùng giờ ngay khi đổi ngày/giờ
    const box=$('e_cf');if(!box)return;
    const date=lunar?dateV:$('e_d').value,time=$('e_h').value,n=++cfN;
    if(all.checked||!okDate(date)||!/^\d{2}:\d{2}$/.test(time)){box.innerHTML='';return;}
    let l;try{l=await j('/conflicts?start='+date+'T'+time+':00'+(d.duration_min?'&duration_min='+d.duration_min:'')+(id?'&exclude='+id:''));}catch(x){return;}
    if(n===cfN)box.innerHTML=conflictNotes(l);},300);};
  all.onchange=()=>{$('e_hw').hidden=all.checked;checkCf();};all.onchange();
  $('e_h').oninput=checkCf;if(!lunar)$('e_d').oninput=checkCf;
  $('e_no').onclick=back;
  f.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();back();}};
  f.onsubmit=async e=>{
    e.preventDefault();err.hidden=true;
    const title=$('e_t').value.trim();
    if(!title)return fail('Tên việc không được để trống.');
    const allDay=all.checked,date=lunar?dateV:$('e_d').value;
    if(!okDate(date))return fail('Ngày chưa hợp lệ.');
    const time=allDay?'00:00':$('e_h').value;
    if(!/^\d{2}:\d{2}$/.test(time))return fail('Giờ chưa hợp lệ.');
    const mv=$('e_m').value,mins=mv===''?null:Number(mv);
    const body={title,start:date+'T'+time+':00',all_day:allDay,duration_min:d.duration_min||null,
      repeat:lunar?(d.repeat||null):($('e_r').value||null),remind_before_min:mins,lunar:d.lunar||null};
    btn.disabled=true;
    if(id){
      delete body.lunar;delete body.duration_min;if(lunar)delete body.repeat;
      let ev;try{ev=await j('/events/'+id,{method:'PATCH',body:JSON.stringify(body)});}
      catch(x){btn.disabled=false;return fail('Chưa lưu được: '+x.message);}
      const c=conflictNotes(ev.conflicts);
      show('<div class="saved">Đã lưu thay đổi.</div>'+c,'draft');refresh();due();return;
    }
    try{
      const ev=await j('/events',{method:'POST',body:JSON.stringify(body)});
      $('q').value='';grow();Voice.last=null;
      showSaved(ev);
    }catch(x){btn.disabled=false;fail('Chưa lưu được: '+x.message);}
  };
  $('e_t').focus();
}
$('go').onclick=async()=>{
  const text=$('q').value.trim();if(!text)return;
  if(Voice.last&&text!==Voice.last){fetch('/stt/learn',{method:'POST',headers:KEY.h(),body:JSON.stringify({heard:Voice.last,fixed:text})}).catch(()=>{});Voice.last=null;}
  toast('');$('go').disabled=true;$('go').classList.add('busy');
  let r;try{r=await j('/parse',{method:'POST',body:JSON.stringify({text})},90000);}
  catch(e){show('<div class="note">'+esc(e.message)+'</div>');return;}
  finally{$('go').disabled=false;$('go').classList.remove('busy');}
  const d=r.draft;
  if(r.status==='need_info'){
    show('<div class="who">Trợ lý</div><div>Mình chưa hiểu đủ, còn thiếu <b>'+r.missing.map(m=>m==='title'?'việc cần làm':'ngày giờ').join(', ')+'</b>. Bạn thử nói rõ hơn, ví dụ "họp 3h chiều mai".</div>');return;}
  const conf=conflictNotes(r.conflicts);
  const warn=(d.warnings||[]).map(w=>'<div class="note">'+esc(w)+'</div>').join('');
  const AIL={ok:'AI đã trả lời',error:'AI lỗi',not_better:'AI trả lời nhưng chưa giúp được',off:'AI tắt',busy:'AI đang bận',paused:'AI tạm nghỉ'};
  const ainote=d.ai?'<div class="ai">'+esc(AIL[d.ai.status]||d.ai.status)+(d.ai.detail?' · '+esc(d.ai.detail):'')+(d.ai.raw&&d.ai.status!=='ok'?' · '+esc(d.ai.raw):'')+'</div>':'';
  const rep=repText(d.repeat,d.lunar&&d.lunar[0],d.lunar&&d.lunar[1]).replace(/^ · /,'');
  const facts='<div class="fact">'+ICO.cal+'<span>'+whenLong(d.start,d.all_day)+'</span></div>'
    +(rep?'<div class="fact">'+ICO.rep+'<span>'+esc(rep)+'</span></div>':'')
    +(d.remind_before_min?'<div class="fact">'+ICO.bell+'<span>Nhắc trước '+mins(d.remind_before_min)+(d.remind_default?' (theo Cài đặt cá nhân)':'')+'</span></div>':'');
  const tags=(d.used_ai?'<span class="tag">AI hỗ trợ</span>':'')+(d.memory?'<span class="tag">theo cách nói đã nhớ</span>':'');
  const card='<div class="who">Trợ lý hiểu là</div><p class="dt">'+esc(d.title)+'</p><div class="facts">'+facts+'</div>'+(tags?'<div class="tags">'+tags+'</div>':'')+conf+warn+ainote
    +'<div class="actions"><button class="btn" id="ok">Lưu</button><button class="btn ghost" id="edit">Sửa</button><button class="btn ghost" id="no">Bỏ qua</button></div>';
  const bindCard=()=>{
  $('no').onclick=()=>show('');
  $('edit').onclick=()=>openEdit(d,()=>{show(card);bindCard();});
  $('ok').onclick=async()=>{
    $('ok').disabled=true;
    let r2;try{r2=await j('/parse',{method:'POST',body:JSON.stringify({text,save:true})},90000);}
    catch(e){$('ok').disabled=false;toast('Chưa lưu được: '+e.message);return;}
    const ev=r2.event;
    if(!ev){show('<div class="note">Chưa lưu được, bạn thử lại.</div>');return;}
    $('q').value='';grow();Voice.last=null;
    showSaved(ev);};
  };
  show(card);bindCard();
};
/* ---- thông báo hệ thống (tùy chọn): chỉ xin quyền khi người dùng bấm, nhắc hiện thành thông báo của máy ---- */
/* Trang mở qua http bằng địa chỉ IP (không phải localhost) không phải "trang an toàn": trình duyệt tắt micro, thông báo, cài app. */
const INSECURE='Bạn đang mở app qua địa chỉ mạng (http://…), không phải localhost, nên trình duyệt tắt micro, thông báo trên máy và cài app. Lịch và nhắc trong trang vẫn dùng bình thường. Muốn có đủ các tính năng này trên điện thoại, mở bằng localhost qua cáp USB (Hướng dẫn sử dụng, mục 8).';
const store={get:k=>{try{return localStorage.getItem(k);}catch(e){return null;}},set:(k,v)=>{try{localStorage.setItem(k,v);}catch(e){}}};
const Notif={reg:null,
  can(){return 'Notification' in window&&window.isSecureContext;},
  ok(){return this.can()&&Notification.permission==='granted';},
  async init(){
    if('serviceWorker' in navigator&&window.isSecureContext){
      try{this.reg=await navigator.serviceWorker.register('/sw.js');}catch(e){}
      navigator.serviceWorker.addEventListener('message',e=>{if(e.data==='due')due();
        else if(e.data&&e.data.ack)j('/reminders/ack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(e.data.ack)}).then(due).catch(()=>{});});}
    this.ui();},
  ui(){
    const st=this.can()?Notification.permission:'none';
    $('ntf').hidden=st!=='default'||store.get('lv_ntf_later')==='1';
    $('ntfbtn').hidden=st!=='default';$('ntftest').hidden=st!=='granted';
    $('ntfst').textContent=st==='granted'?'Thông báo trên máy đang bật.':st==='denied'?'Trình duyệt đang chặn thông báo của app. Muốn bật lại, bấm biểu tượng ổ khóa cạnh địa chỉ trang, chọn cho phép Thông báo rồi tải lại trang.'
      :st==='default'?'Thông báo trên máy chưa bật. Nhắc việc vẫn hiện ở đầu trang khi app đang mở.':window.isSecureContext===false?INSECURE:'Cửa sổ này không hỗ trợ thông báo của máy. Nhắc việc vẫn hiện ở đầu trang.';
    if(window.isSecureContext===false)$('instx').textContent='Cài app lên máy chỉ có khi mở bằng localhost (xem phần Thông báo ở trên).';},
  async ask(){
    try{await Notification.requestPermission();}catch(e){}
    this.ui();
    if(this.ok()){toast('Đã bật thông báo. Tới giờ nhắc, máy sẽ hiện thông báo.');due();}
    else if(this.can()&&Notification.permission==='denied')toast('Bạn đã chặn thông báo. Nhắc việc vẫn hiện ở đầu trang khi app đang mở.');},
  seen(){try{return JSON.parse(store.get('lv_ntf_seen')||'[]');}catch(e){return [];}},
  show(title,opt){
    if(this.reg&&this.reg.showNotification)return this.reg.showNotification(title,opt).catch(()=>{});
    try{delete opt.actions;const n=new Notification(title,opt);n.onclick=()=>{window.focus();n.close();};}catch(e){}},
  push(list,soon){   // mỗi lần nhắc chỉ hiện một lần trên máy này (nhớ trong localStorage)
    if(!this.ok()||!list.length)return;
    const seen=this.seen();let ch=false;
    list.forEach(x=>{const k=x.event_id+'|'+(x.key||x.occurrence);if(seen.includes(k))return;seen.push(k);ch=true;
      this.show((soon(x)?'Còn '+x.days_left+' ngày: ':'Đến giờ: ')+x.title,
        {body:when(x.occurrence,x.all_day)+(x.notes?' · '+x.notes:''),tag:'lv-'+k,icon:'/icon-192.png',lang:'vi',requireInteraction:true,
         data:{event_id:x.event_id,key:x.key||x.occurrence},actions:[{action:'ack',title:'Đã biết'}]});});
    if(ch)store.set('lv_ntf_seen',JSON.stringify(seen.slice(-300)));},
  async close(k){   // bấm Đã biết trong trang thì gỡ thông báo tương ứng trên máy
    if(!this.reg||!this.reg.getNotifications)return;
    try{(await this.reg.getNotifications({tag:'lv-'+k})).forEach(n=>n.close());}catch(e){}}};
$('ntfok').onclick=$('ntfbtn').onclick=()=>Notif.ask();
$('netre').onclick=()=>{$('nettxt').textContent='Đang thử kết nối lại…';refresh();due();};
window.addEventListener('online',()=>{refresh();due();});
$('ntfno').onclick=()=>{store.set('lv_ntf_later','1');Notif.ui();toast('Bạn có thể bật sau trong mục "Thông báo và cài app lên máy" ở cuối trang.');};
$('ntftest').onclick=()=>Notif.show('Thử thông báo',{body:'Thông báo của trợ lý thời gian hiện như thế này.',tag:'lv-test',icon:'/icon-192.png',lang:'vi'});
/* Cài app lên máy (PWA): Chrome/Edge báo có thể cài thì hiện nút. */
let instEv=null;
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();instEv=e;$('inst').hidden=false;});
$('inst').onclick=async()=>{if(!instEv)return;instEv.prompt();try{await instEv.userChoice;}catch(e){}instEv=null;$('inst').hidden=true;};
window.addEventListener('appinstalled',()=>{$('inst').hidden=true;$('instx').textContent='App đã được cài lên máy.';});
Notif.init();
refresh();due();setInterval(due,30000);

/* ---- sao lưu và cụm từ đã học ---- */
async function phr(){
  let l;try{l=await j('/phrases');}catch(e){$('phl').innerHTML='<p>'+esc(e.message)+'</p>';return;}
  $('phl').innerHTML=l.length?l.map(x=>'<div class="ph"><div class="x"><b>'+esc(x.src)+'</b> → '+esc(x.dst)+'<br><small>xác nhận '+x.hits+' lần, đã dùng '+x.uses+' lần'+(x.hits>=2?'':' (chưa đủ để áp dụng)')+'</small></div><button class="del" title="Quên cụm này" aria-label="Quên" data-s="'+esc(x.src)+'">'+ICO.x+'</button></div>').join(''):'<p>Chưa có cụm nào.</p>';
  document.querySelectorAll('#phl .del').forEach(b=>b.onclick=async()=>{try{await j('/phrases/'+encodeURIComponent(b.dataset.s),{method:'DELETE'});}catch(e){toast(e.message);}phr();});
}
/* Màn hình chào: người cài lại app mở thẳng mục Sao lưu và chọn tệp. */
$('wrs').onclick=()=>{const m=$('more');m.open=true;m.scrollIntoView({behavior:'smooth',block:'start'});$('rs').click();};
$('more').addEventListener('toggle',()=>{if($('more').open)phr();});
/* Đăng ký lịch .ics cho ứng dụng lịch trên cùng máy */
$('feed').addEventListener('toggle',async()=>{
  if(!$('feed').open)return;
  try{const f=await j('/calendar/feed');$('feedurl').value=location.origin+f.path;
    $('feednote').hidden=!f.note;$('feednote').textContent=f.note||'';}
  catch(e){$('feedurl').value='';$('feednote').hidden=false;$('feednote').textContent=e.message;}
});
$('feedcp').onclick=async()=>{
  const v=$('feedurl').value;if(!v)return;
  try{await navigator.clipboard.writeText(v);toast('Đã chép địa chỉ đăng ký lịch.');}
  catch(e){$('feedurl').select();toast('Hãy bấm Ctrl+C để chép địa chỉ đang chọn.');}
};
$('rs').onchange=async e=>{
  const f=e.target.files[0];if(!f)return;
  try{const r=await fetch('/import',{method:'POST',headers:KEY.h(),body:await f.text()});const x=await r.json();
    $('bkmsg').textContent=r.ok?('Đã nhập '+x.added+' việc, bỏ qua '+x.skipped+' việc trùng, '+x.phrases+' cụm từ.'):(x.error||'Không nhập được');
    if(r.ok&&x.added)welcome(1);
    if(r.ok&&x.settings){$('bkmsg').textContent+=' Đã lấy lại cài đặt cá nhân.';loadMe();}
    refresh();phr();}catch(err){$('bkmsg').textContent='Tệp không đọc được.';}
  e.target.value='';};
/* Nhập khóa khi mở từ máy khác: thử bằng /info, đúng thì tải lại trang, sai thì báo và quên khóa. */
$('keyf').onsubmit=async e=>{
  e.preventDefault();const v=$('keyin').value.trim();if(!v)return;
  KEY.set(v);$('keymsg').textContent='Đang kiểm tra khóa…';
  try{await j('/info',null,15000);location.reload();}
  catch(er){if(er.status===401){KEY.set('');$('keymsg').textContent='Khóa không đúng. Bạn hỏi lại người cài app (giá trị LICHVIET_API_KEY).';}
    else $('keymsg').textContent=er.message;}};
/* Liên kết tải tệp (sao lưu, .ics) không tự gửi được khóa: khi có khóa thì tải bằng fetch rồi lưu tệp. */
document.addEventListener('click',async e=>{
  const a=e.target.closest&&e.target.closest('a[download]');
  if(!a||!KEY.get()||a.href.startsWith('blob:'))return;
  e.preventDefault();
  try{const r=await fetch(a.getAttribute('href'),{headers:KEY.h()});
    if(r.status===401){KEY.ask();return;}
    if(!r.ok)throw new Error();
    const u=URL.createObjectURL(await r.blob()),t=document.createElement('a');
    t.href=u;t.download=a.getAttribute('download')||(a.getAttribute('href').endsWith('.ics')?'lich.ics':'tep');
    document.body.appendChild(t);t.click();t.remove();setTimeout(()=>URL.revokeObjectURL(u),10000);}
  catch(er){toast('Không tải được tệp, bạn thử lại.');}});
</script></body></html>"""
