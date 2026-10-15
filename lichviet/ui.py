PAGE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trợ lý thời gian</title>
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
.btn{border:0;border-radius:12px;padding:10px 22px;font-family:inherit;font-weight:600;font-size:15px;cursor:pointer;background:var(--tx);color:var(--bg)}
.btn.ghost{background:transparent;color:var(--mut);border:1px solid var(--line);font-weight:500}
.btn:disabled{opacity:.5}
/* ---- nhắc ---- */
.banner svg{width:20px;height:20px;flex:none}.banner{display:flex;align-items:center;gap:12px;background:var(--warnbg);color:var(--warn);border-radius:16px;padding:12px 14px;margin:14px 0 0}
.banner .x{flex:1}.banner button{border:1px solid currentColor;background:transparent;color:inherit;border-radius:10px;padding:6px 12px;font-family:inherit;font-weight:600;font-size:13px;cursor:pointer}
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
.del:hover{background:var(--warnbg);color:var(--warn);opacity:1}
.del svg{width:17px;height:17px}
.empty{color:var(--mut);text-align:center;padding:26px 0}
details.more{margin-top:22px;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:4px 18px;box-shadow:var(--sh)}
details.more summary{cursor:pointer;padding:14px 0;font-weight:700;font-size:15px}
details.more .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:6px 0 14px}
details.more p{color:var(--mut);font-size:13px;margin:0 0 10px}
.ph{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:14px}
.ph .x{flex:1;min-width:0;overflow-wrap:anywhere}.ph small{color:var(--mut)}
.mic-on{background:var(--warn)!important;color:#fff!important}
@media(max-width:480px){.hero{padding:18px}.big{font-size:52px}.lunar .l2{font-size:18px}.composer{margin-left:4px;margin-right:4px}}
</style></head><body><main>
<section class="hero"><div class="big" id="dnum"></div><div><div class="wd" id="dwd"></div><div class="mo" id="dmo"></div></div>
<div class="lunar"><div class="l1">Âm lịch</div><div class="l2" id="lday">&nbsp;</div><div class="l3" id="lyear"></div></div></section>
<div class="composer">
<textarea id="q" rows="1" placeholder="Nói hoặc gõ việc cần nhớ…"></textarea>
<button class="ib" id="mic" type="button" title="Nói" aria-label="Nói"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v4"/></svg></button>
<button class="ib" id="go" type="button" title="Hiểu câu này (Enter)" aria-label="Hiểu câu này"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
</div>
<div class="chips" id="chips"></div>
<div class="toast" id="toast"></div>
<div id="due"></div>
<div id="draft" hidden></div>
<div class="sec"><h2>Sắp tới</h2><span>7 ngày</span></div>
<div id="list"></div>
<details class="more" id="more"><summary>Sao lưu và cụm từ đã học</summary>
<p>Gỡ app khỏi Pi Desktop sẽ xóa dữ liệu. Hãy tải bản sao lưu trước khi gỡ, rồi khôi phục sau khi cài lại.</p>
<div class="row"><a class="btn" id="bk" href="/export" download="lichviet-saoluu.json" style="text-decoration:none">Tải bản sao lưu</a>
<label class="btn ghost" style="cursor:pointer">Khôi phục từ tệp<input type="file" id="rs" accept="application/json,.json" hidden></label><span id="bkmsg" style="font-size:13px;color:var(--mut)"></span></div>
<p>Cụm từ app đã học từ các lần bạn xác nhận. Xóa cụm nào thì app sẽ hỏi AI lại như lần đầu.</p>
<div id="phl"></div></details>
</main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const j=async(u,o)=>{const r=await fetch(u,o);return r.json()};
const p=n=>String(n).padStart(2,'0');
const WD=['Chủ nhật','Thứ hai','Thứ ba','Thứ tư','Thứ năm','Thứ sáu','Thứ bảy'];
const fmtD=iso=>{const d=new Date(iso);return p(d.getDate())+'/'+p(d.getMonth()+1)+(d.getFullYear()!==new Date().getFullYear()?'/'+d.getFullYear():'')};
const fmtT=iso=>{const d=new Date(iso);return p(d.getHours())+':'+p(d.getMinutes())};
const fmt=iso=>fmtD(iso)+' '+fmtT(iso);
const when=(iso,allDay)=>allDay?fmtD(iso)+' cả ngày':fmt(iso);
const whenLong=(iso,allDay)=>{const d=new Date(iso);return WD[d.getDay()]+', '+fmtD(iso)+(allDay?' · cả ngày':' · '+fmtT(iso))};
const local=d=>d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'T00:00:00';
const REP={daily:'mỗi ngày',weekly:'mỗi tuần',monthly:'mỗi tháng',lunar_yearly:'hằng năm'};
const repText=(rep,ld,lm)=>!rep?'':rep==='lunar_yearly'?' · âm lịch '+(ld&&lm?p(ld)+'/'+p(lm)+', ':'')+'hằng năm':' · '+(REP[rep]||rep);
const svg=d=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+d+'</svg>';
const ICO={cal:svg('<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/>'),
 rep:svg('<path d="M17 2l4 4-4 4M3 11V9a3 3 0 013-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 01-3 3H3"/>'),
 bell:svg('<path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 004 0"/>'),
 x:svg('<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>')};
function toast(m){$('toast').textContent=m||'';}
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
    let st={};try{st=await j('/stt/status');}catch(e){}
    if(!st.enabled){toast('Nhập bằng giọng nói chưa bật. Vào Config của app, chọn "Nhập bằng giọng nói" rồi lưu.');return;}
    if(!st.ready){toast('Mô hình giọng nói đang tải (lần đầu mất vài phút). Bạn gõ tạm nhé.');return;}
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
      const r=await fetch('/stt',{method:'POST',body:wav,headers:{'Content-Type':'audio/wav'}});
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
/* ---- ô nhập ---- */
const grow=()=>{const q=$('q');q.style.height='auto';q.style.height=Math.min(q.scrollHeight,160)+'px';};
$('q').addEventListener('input',grow);
$('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('go').click();}});
const SAMPLES=['họp với anh Nam 3h chiều mai','uống thuốc 7h tối mỗi ngày','giỗ ông nội 15/8 âm lịch','đi khám thứ năm tuần sau 9h'];
$('chips').innerHTML=SAMPLES.map(s=>'<button type="button" class="chip">'+esc(s)+'</button>').join('');
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{$('q').value=c.textContent;grow();$('q').focus();});
/* ---- lịch ---- */
function dayHead(key){
  const d=new Date(key+'T00:00:00'),t=TODAY?new Date(TODAY+'T00:00:00'):new Date();t.setHours(0,0,0,0);
  const diff=Math.round((d-t)/864e5),base=WD[d.getDay()]+', '+p(d.getDate())+'/'+p(d.getMonth()+1);
  return '<div class="day'+(diff===0?' today':'')+'">'+(diff===0?'Hôm nay <small>'+base+'</small>':diff===1?'Ngày mai <small>'+base+'</small>':base)+'</div>';
}
async function refresh(){
  if(!TODAY){try{TODAY=(await j('/today')).date}catch(e){}}
  const a=TODAY?new Date(TODAY+'T00:00:00'):new Date(),b=new Date(a);b.setDate(b.getDate()+7);
  const ev=await j('/events?from='+local(a)+'&to='+local(b));
  if(!ev.length){$('list').innerHTML='<div class="empty">Chưa có việc nào trong 7 ngày tới.</div>';return;}
  ev.sort((x,y)=>x.occurrence<y.occurrence?-1:1);
  let html='',cur='';
  ev.forEach(e=>{
    const k=e.occurrence.slice(0,10);
    if(k!==cur){cur=k;html+=dayHead(k);}
    const rep=repText(e.repeat,e.lunar_day,e.lunar_month).replace(/^ · /,'');
    html+='<div class="ev"><div class="time'+(e.all_day?' all':'')+'">'+(e.all_day?'Cả ngày':fmtT(e.occurrence))+'</div>'
      +'<div class="bar'+(e.repeat==='lunar_yearly'?' lunar':e.repeat?' rep':'')+'"></div>'
      +'<div class="body"><b>'+esc(e.title)+'</b>'+(rep?'<span class="t">'+esc(rep)+'</span>':'')+'</div>'
      +'<button class="del" title="Xóa" aria-label="Xóa" data-id="'+e.id+'" data-rep="'+(e.repeat||'')+'">'+ICO.x+'</button></div>';
  });
  $('list').innerHTML=html;
  document.querySelectorAll('#list .del').forEach(btn=>btn.onclick=async()=>{
    if(!confirm(btn.dataset.rep?'Xóa toàn bộ chuỗi lịch lặp này?':'Xóa lịch này?'))return;
    await fetch('/events/'+btn.dataset.id,{method:'DELETE'});refresh();});
}
async function due(){
  const d=await j('/reminders/due');
  const soon=x=>x.kind&&x.kind!=='on_time';
  $('due').innerHTML=d.map(x=>'<div class="banner">'+ICO.bell+'<div class="x">'+(soon(x)?'Còn '+x.days_left+' ngày: ':'Đến giờ: ')+'<b>'+esc(x.title)+'</b> · '+when(x.occurrence,x.all_day)+'</div><button data-e="'+x.event_id+'" data-o="'+esc(x.key||x.occurrence)+'">Đã biết</button></div>').join('');
  document.querySelectorAll('#due button').forEach(btn=>btn.onclick=async()=>{
    await fetch('/reminders/fired',{method:'POST',body:JSON.stringify({event_id:+btn.dataset.e,occurrence:btn.dataset.o})});due();});
}
/* ---- hiểu câu + lưu ---- */
function show(html,cls){const d=$('draft');d.className=html?(cls||'draft'):'';d.innerHTML=html;d.hidden=!html;}
$('go').onclick=async()=>{
  const text=$('q').value.trim();if(!text)return;
  if(Voice.last&&text!==Voice.last){fetch('/stt/learn',{method:'POST',body:JSON.stringify({heard:Voice.last,fixed:text})}).catch(()=>{});Voice.last=null;}
  toast('');$('go').disabled=true;$('go').classList.add('busy');
  let r;try{r=await j('/parse',{method:'POST',body:JSON.stringify({text})});}
  finally{$('go').disabled=false;$('go').classList.remove('busy');}
  const d=r.draft;
  if(r.status==='need_info'){
    show('<div class="who">Trợ lý</div><div>Mình chưa hiểu đủ, còn thiếu <b>'+r.missing.map(m=>m==='title'?'việc cần làm':'ngày giờ').join(', ')+'</b>. Bạn thử nói rõ hơn, ví dụ "họp 3h chiều mai".</div>');return;}
  const conf=(r.conflicts||[]).map(c=>'<div class="note">Trùng giờ với <b>'+esc(c.title)+'</b> ('+fmt(c.occurrence)+')</div>').join('');
  const warn=(d.warnings||[]).map(w=>'<div class="note">'+esc(w)+'</div>').join('');
  const AIL={ok:'AI đã trả lời',error:'AI lỗi',not_better:'AI trả lời nhưng chưa giúp được',off:'AI tắt',busy:'AI đang bận',paused:'AI tạm nghỉ'};
  const ainote=d.ai?'<div class="ai">'+esc(AIL[d.ai.status]||d.ai.status)+(d.ai.detail?' · '+esc(d.ai.detail):'')+(d.ai.raw&&d.ai.status!=='ok'?' · '+esc(d.ai.raw):'')+'</div>':'';
  const rep=repText(d.repeat,d.lunar&&d.lunar[0],d.lunar&&d.lunar[1]).replace(/^ · /,'');
  const facts='<div class="fact">'+ICO.cal+'<span>'+whenLong(d.start,d.all_day)+'</span></div>'
    +(rep?'<div class="fact">'+ICO.rep+'<span>'+esc(rep)+'</span></div>':'')
    +(d.remind_before_min?'<div class="fact">'+ICO.bell+'<span>Nhắc trước '+d.remind_before_min+' phút</span></div>':'');
  const tags=(d.used_ai?'<span class="tag">AI hỗ trợ</span>':'')+(d.memory?'<span class="tag">theo cách nói đã nhớ</span>':'');
  show('<div class="who">Trợ lý hiểu là</div><p class="dt">'+esc(d.title)+'</p><div class="facts">'+facts+'</div>'+(tags?'<div class="tags">'+tags+'</div>':'')+conf+warn+ainote
    +'<div class="actions"><button class="btn" id="ok">Lưu</button><button class="btn ghost" id="no">Bỏ qua</button></div>');
  $('no').onclick=()=>show('');
  $('ok').onclick=async()=>{
    $('ok').disabled=true;
    const r2=await j('/parse',{method:'POST',body:JSON.stringify({text,save:true})});
    const ev=r2.event;
    if(!ev){show('<div class="note">Chưa lưu được, bạn thử lại.</div>');return;}
    const far=(new Date(ev.start)-new Date())>7*864e5;
    $('q').value='';grow();Voice.last=null;
    show('<div class="saved">'+(ev.duplicate?'Việc này đã có trong lịch, mình không lưu thêm.':'Đã lưu.')+(far?' Lần tới vào '+when(ev.start,ev.all_day)+', xa hơn 7 ngày nên chưa hiện trong danh sách bên dưới.':'')+'</div>','draft');
    refresh();due();};
};
refresh();due();setInterval(due,30000);

/* ---- sao lưu và cụm từ đã học ---- */
async function phr(){
  const l=await j('/phrases');
  $('phl').innerHTML=l.length?l.map(x=>'<div class="ph"><div class="x"><b>'+esc(x.src)+'</b> → '+esc(x.dst)+'<br><small>xác nhận '+x.hits+' lần, đã dùng '+x.uses+' lần'+(x.hits>=2?'':' (chưa đủ để áp dụng)')+'</small></div><button class="del" title="Quên cụm này" aria-label="Quên" data-s="'+esc(x.src)+'">'+ICO.x+'</button></div>').join(''):'<p>Chưa có cụm nào.</p>';
  document.querySelectorAll('#phl .del').forEach(b=>b.onclick=async()=>{await fetch('/phrases/'+encodeURIComponent(b.dataset.s),{method:'DELETE'});phr();});
}
$('more').addEventListener('toggle',()=>{if($('more').open)phr();});
$('rs').onchange=async e=>{
  const f=e.target.files[0];if(!f)return;
  try{const r=await fetch('/import',{method:'POST',body:await f.text()});const x=await r.json();
    $('bkmsg').textContent=r.ok?('Đã nhập '+x.added+' việc, bỏ qua '+x.skipped+' việc trùng, '+x.phrases+' cụm từ.'):(x.error||'Không nhập được');
    refresh();phr();}catch(err){$('bkmsg').textContent='Tệp không đọc được.';}
  e.target.value='';};
</script></body></html>"""
