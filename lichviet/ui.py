PAGE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trợ lý thời gian</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1a2230;--mut:#6b7686;--pri:#0f766e;--bd:#e3e7ed;--warn:#b45309}
@media(prefers-color-scheme:dark){:root{--bg:#10151c;--card:#18202b;--tx:#e8edf3;--mut:#93a0b1;--pri:#2dd4bf;--bd:#27313f;--warn:#fbbf24}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:720px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:8px 0 14px}h2{font-size:15px;margin:0 0 8px;color:var(--mut);font-weight:600}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px;margin-bottom:14px}
textarea{width:100%;min-height:64px;padding:10px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--tx);font:inherit;resize:vertical}
button{border:0;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer;background:var(--pri);color:#fff}
button:disabled{opacity:.5;cursor:default}
button.ghost{background:transparent;color:var(--mut);border:1px solid var(--bd)}
.row{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.ev{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid var(--bd)}
.ev:first-child{border-top:0}.t{color:var(--mut);font-size:13px}.warn{color:var(--warn)}
.banner{background:#fef3c7;color:#78350f;border-radius:10px;padding:10px 14px;margin-bottom:14px}
.empty{color:var(--mut)}
</style></head><body><main>
<h1>Trợ lý thời gian</h1>
<div id="due"></div>
<div class="card"><h2>Gõ việc cần nhớ</h2>
<textarea id="q" placeholder="Ví dụ: họp với anh Nam 3h chiều mai, nhắc trước 10 phút"></textarea>
<div class="row"><button id="go">Hiểu câu này</button></div><div id="draft"></div></div>
<div class="card"><h2>Lịch 7 ngày tới</h2><div id="list"></div></div>
</main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const j=async(u,o)=>{const r=await fetch(u,o);return r.json()};
const p=n=>String(n).padStart(2,'0');
const fmtD=iso=>{const d=new Date(iso);return p(d.getDate())+'/'+p(d.getMonth()+1)+(d.getFullYear()!==new Date().getFullYear()?'/'+d.getFullYear():'')};
const fmtT=iso=>{const d=new Date(iso);return p(d.getHours())+':'+p(d.getMinutes())};
const fmt=iso=>fmtD(iso)+' '+fmtT(iso);
const when=(iso,allDay)=>allDay?fmtD(iso)+' cả ngày':fmt(iso);
const local=d=>d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'T00:00:00';
const REP={daily:'mỗi ngày',weekly:'mỗi tuần',monthly:'mỗi tháng',lunar_yearly:'hằng năm'};
const repText=(rep,ld,lm)=>!rep?'':rep==='lunar_yearly'?' · âm lịch '+(ld&&lm?p(ld)+'/'+p(lm)+', ':'')+'hằng năm':' · '+(REP[rep]||rep);
async function refresh(){
  const a=new Date(),b=new Date();b.setDate(b.getDate()+7);
  const ev=await j('/events?from='+local(a)+'&to='+local(b));
  $('list').innerHTML=ev.length?ev.map(e=>'<div class="ev"><div><b>'+esc(e.title)+'</b><div class="t">'+when(e.occurrence,e.all_day)+repText(e.repeat,e.lunar_day,e.lunar_month)+'</div></div><button class="ghost" data-id="'+e.id+'" data-rep="'+(e.repeat||'')+'">Xóa</button></div>').join(''):'<div class="empty">Chưa có lịch nào.</div>';
  document.querySelectorAll('#list button').forEach(btn=>btn.onclick=async()=>{
    if(!confirm(btn.dataset.rep?'Xóa toàn bộ chuỗi lịch lặp này?':'Xóa lịch này?'))return;
    await fetch('/events/'+btn.dataset.id,{method:'DELETE'});refresh();});
}
async function due(){
  const d=await j('/reminders/due');
  const soon=x=>x.kind&&x.kind!=='on_time';
  $('due').innerHTML=d.map(x=>'<div class="banner">'+(soon(x)?'Sắp tới (còn '+x.days_left+' ngày): ':'Nhắc: ')+'<b>'+esc(x.title)+'</b> '+(soon(x)?'ngày ':'lúc ')+when(x.occurrence,x.all_day)+' <button class="ghost" data-e="'+x.event_id+'" data-o="'+esc(x.key||x.occurrence)+'">Đã biết</button></div>').join('');
  document.querySelectorAll('#due button').forEach(btn=>btn.onclick=async()=>{
    await fetch('/reminders/fired',{method:'POST',body:JSON.stringify({event_id:+btn.dataset.e,occurrence:btn.dataset.o})});due();});
}
$('go').onclick=async()=>{
  const text=$('q').value.trim();if(!text)return;
  const r=await j('/parse',{method:'POST',body:JSON.stringify({text})});const d=r.draft;
  if(r.status==='need_info'){
    $('draft').innerHTML='<p class="warn">Mình chưa hiểu đủ. Thiếu: '+r.missing.map(m=>m==='title'?'việc cần làm':'ngày giờ').join(', ')+'. Bạn thử viết rõ hơn, ví dụ "họp 3h chiều mai".</p>';return;}
  const conf=(r.conflicts||[]).map(c=>'<p class="warn">Trùng với: '+esc(c.title)+' ('+fmt(c.occurrence)+')</p>').join('');
  const warn=(d.warnings||[]).map(w=>'<p class="warn">'+esc(w)+'</p>').join('');
  const AIL={ok:'AI đã trả lời',error:'AI lỗi',not_better:'AI trả lời nhưng chưa giúp được',off:'AI tắt',busy:'AI đang bận',paused:'AI tạm nghỉ'};
  const ainote=d.ai?'<p class="t">'+esc(AIL[d.ai.status]||d.ai.status)+(d.ai.detail?' · '+esc(d.ai.detail):'')+(d.ai.raw&&d.ai.status!=='ok'?' · '+esc(d.ai.raw):'')+'</p>':'';
  $('draft').innerHTML='<p style="margin:10px 0 4px"><b>'+esc(d.title)+'</b></p><div class="t">'+when(d.start,d.all_day)+repText(d.repeat,d.lunar&&d.lunar[0],d.lunar&&d.lunar[1])+(d.remind_before_min?' · nhắc trước '+d.remind_before_min+' phút':'')+(d.used_ai?' · (AI hỗ trợ)':'')+(d.memory?' · (theo cách nói đã nhớ)':'')+'</div>'+conf+warn+ainote+'<div class="row"><button id="ok">Lưu</button><button class="ghost" id="no">Bỏ qua</button></div>';
  $('no').onclick=()=>{$('draft').innerHTML=''};
  $('ok').onclick=async()=>{
    $('ok').disabled=true;
    const r2=await j('/parse',{method:'POST',body:JSON.stringify({text,save:true})});
    const ev=r2.event;
    if(!ev){$('draft').innerHTML='<p class="warn">Chưa lưu được, bạn thử lại.</p>';return;}
    const far=(new Date(ev.start)-new Date())>7*864e5;
    $('q').value='';
    $('draft').innerHTML='<p class="t">'+(ev.duplicate?'Việc này đã có trong lịch, mình không lưu thêm.':'Đã lưu.')+(far?' Lần tới vào '+when(ev.start,ev.all_day)+', xa hơn 7 ngày nên chưa hiện trong danh sách bên dưới.':'')+'</p>';
    refresh();due();};
};
refresh();due();setInterval(due,30000);
</script></body></html>"""