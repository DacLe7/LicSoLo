import { App } from "@capacitor/app";
import { Network } from "@capacitor/network";
import "./style.css";
import { Api } from "./api";
import { KEY } from "./config";
import { DEFAULT_URL, LvSystem, calendarPort, devicePort, checkPerms, notifierPort, prefs, removeEverything, requestPerms, saveDeviceOffset, sharedRefs } from "./native";
import type { PermReport, PermState } from "./native";
import { createSync } from "./sync";
import type { NewEvent, ParseDraft, ParseResult, SyncResult } from "./types";
import { dayStart, parts } from "./timeutil";
import { Recorder, toBase64, toWav } from "./voice";

/* ---------- tiện ích ---------- */
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const esc = (s: unknown) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
const p2 = (n: number) => String(n).padStart(2, "0");
const WD = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
const REP: Record<string, string> = { daily: "mỗi ngày", weekly: "mỗi tuần", monthly: "mỗi tháng", lunar_yearly: "hằng năm" };

/** Các hàm giờ làm việc trên chuỗi "2026-10-28T09:00:00" của server, không qua múi giờ của điện thoại. */
const wdOf = (iso: string) => { const t = parts(iso); return WD[new Date(Date.UTC(t.y, t.mo - 1, t.d)).getUTCDay()]; };
const fmtD = (iso: string) => { const t = parts(iso); return `${p2(t.d)}/${p2(t.mo)}`; };
const fmtT = (iso: string) => { const t = parts(iso); return `${p2(t.h)}:${p2(t.mi)}`; };
const whenLong = (iso: string, allDay: boolean) => `${wdOf(iso)}, ${fmtD(iso)}${allDay ? " · cả ngày" : " · " + fmtT(iso)}`;
const repText = (rep: string | null, ld?: number | null, lm?: number | null) =>
  !rep ? "" : rep === "lunar_yearly" ? "âm lịch " + (ld && lm ? `${p2(ld)}/${p2(lm)}, ` : "") + "hằng năm" : REP[rep] ?? rep;

const svg = (d: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICO = {
  cal: svg('<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/>'),
  rep: svg('<path d="M17 2l4 4-4 4M3 11V9a3 3 0 013-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 01-3 3H3"/>'),
  bell: svg('<path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 004 0"/>'),
  x: svg('<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>'),
};

/* ---------- trạng thái ---------- */
let serverUrl = DEFAULT_URL;
let lastSync: number | null = null;
const api = new Api(() => serverUrl);
const runSync = createSync({ api, calendar: calendarPort, notifier: notifierPort, shared: sharedRefs, device: devicePort(() => serverUrl) });
const SYNC_EVERY_MS = 60_000;
let today = ""; // "2026-10-28" theo server

const fmtStamp = (ms: number) => {
  const d = new Date(ms);
  return `${p2(d.getHours())}:${p2(d.getMinutes())} ${p2(d.getDate())}/${p2(d.getMonth() + 1)}`;
};
const lastText = () => (lastSync ? "Lần đồng bộ cuối: " + fmtStamp(lastSync) : "Chưa đồng bộ lần nào");

function setSyncLine(text: string, bad = false) {
  const el = $("syncline");
  el.textContent = text;
  el.classList.toggle("bad", bad);
}

let syncing = false;
async function doSync(): Promise<SyncResult> {
  if (syncing) return runSync(); // trả lại lần đang chạy
  syncing = true;
  setSyncLine("Đang đồng bộ…");
  try {
    void saveDeviceOffset().catch(() => undefined);
    const r = await runSync();
    if (r.error) {
      setSyncLine("Chưa kết nối được máy tính. " + lastText(), true);
    } else {
      lastSync = Date.now();
      await prefs.set(KEY.lastSync, String(lastSync));
      const problems = [r.calendarError && "lịch: " + r.calendarError, r.notifyError && "thông báo: " + r.notifyError].filter(Boolean);
      setSyncLine(problems.length ? `Đồng bộ chưa trọn vẹn (${problems.join("; ")}). ${lastText()}` : `Đã đồng bộ ${r.occurrences.length} việc, hẹn ${r.scheduled} lần nhắc. ${lastText()}`, problems.length > 0);
      // chỉ vẽ lại khi đang xem Cài đặt và không ai đang gõ (đồng bộ định kỳ không được giật ô nhập)
      if (!$("tab-settings").hidden && document.activeElement?.tagName !== "INPUT") void renderSettings();
    }
    return r;
  } finally {
    syncing = false;
  }
}

/* ---------- thẻ "Trợ lý hiểu là" ---------- */
let voiceLast: string | null = null;
const toast = (m = "") => { $("toast").textContent = m; };

function show(html: string, cls = "draft") {
  const d = $("draft");
  d.className = html ? cls : "";
  d.innerHTML = html;
  d.hidden = !html;
}

function growQ() {
  const q = $<HTMLTextAreaElement>("q");
  q.style.height = "auto";
  q.style.height = Math.min(q.scrollHeight, 160) + "px";
}

function showSaved(ev: { start: string; all_day: boolean; duplicate?: boolean }) {
  $<HTMLTextAreaElement>("q").value = "";
  growQ();
  voiceLast = null;
  show(`<div class="saved">${ev.duplicate ? "Việc này đã có trong lịch, mình không lưu thêm." : "Đã lưu vào LicSoLo."} ${esc(fmtD(ev.start))}${ev.all_day ? " cả ngày" : " " + esc(fmtT(ev.start))}</div>`);
  void doSync().then(() => refreshList());
}

const okDate = (s: string) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return false;
  const x = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return x.getUTCMonth() === +m[2] - 1 && x.getUTCDate() === +m[3];
};

const REPOPT: [string, string][] = [["", "Không lặp"], ["daily", "Mỗi ngày"], ["weekly", "Mỗi tuần"], ["monthly", "Mỗi tháng"]];

function openEdit(d: ParseDraft, back: () => void) {
  const lunar = !!d.lunar;
  const st = d.start ?? "";
  const dateV = st.slice(0, 10), timeV = st.slice(11, 16);
  const opts = REPOPT.map(([v, l]) => `<option value="${v}"${(d.repeat ?? "") === v ? " selected" : ""}>${l}</option>`).join("");
  show(`<form class="edit" id="ef" novalidate><div class="who">Sửa việc trước khi lưu</div>
    <label class="fl">Tên việc<input id="e_t" type="text" maxlength="200" value="${esc(d.title)}"></label>
    <div class="erow">${lunar ? "" : `<label class="fl">Ngày<input id="e_d" type="date" value="${dateV}"></label>`}
    <label class="fl" id="e_hw">Giờ<input id="e_h" type="time" value="${timeV}"></label></div>
    <label class="ck"><input id="e_all" type="checkbox"${d.all_day ? " checked" : ""}> Cả ngày</label>
    ${lunar ? '<p class="ai">Việc theo âm lịch giữ nguyên ngày âm, nên chỉ sửa được tên, giờ và nhắc trước.</p>'
      : `<label class="fl">Lặp<select id="e_r">${opts}</select></label>`}
    <label class="fl">Nhắc trước (phút)<input id="e_m" type="number" min="0" max="10080" step="1" inputmode="numeric" value="${d.remind_before_min || ""}"></label>
    <div class="note" id="e_err" hidden></div>
    <div class="actions"><button class="btn" type="submit">Lưu</button><button class="btn ghost" type="button" id="e_no">Hủy</button></div></form>`);
  const f = $<HTMLFormElement>("ef"), err = $("e_err"), all = $<HTMLInputElement>("e_all");
  const btn = f.querySelector<HTMLButtonElement>("button[type=submit]")!;
  const fail = (m: string) => { err.textContent = m; err.hidden = false; };
  const toggleTime = () => { $("e_hw").hidden = all.checked; };
  all.onchange = toggleTime;
  toggleTime();
  $("e_no").onclick = back;
  f.onsubmit = async (e) => {
    e.preventDefault();
    err.hidden = true;
    const title = $<HTMLInputElement>("e_t").value.trim();
    if (!title) return fail("Tên việc không được để trống.");
    const allDay = all.checked;
    const date = lunar ? dateV : $<HTMLInputElement>("e_d").value;
    if (!okDate(date)) return fail("Ngày chưa hợp lệ.");
    const time = allDay ? "00:00" : $<HTMLInputElement>("e_h").value;
    if (!/^\d{2}:\d{2}$/.test(time)) return fail("Giờ chưa hợp lệ.");
    const mv = $<HTMLInputElement>("e_m").value.trim();
    let mins: number | null = null;
    if (mv !== "") {
      mins = Number(mv);
      if (!Number.isInteger(mins) || mins < 0 || mins > 10080) return fail("Nhắc trước phải là số phút từ 0 đến 10080.");
    }
    const body: NewEvent = {
      title, start: `${date}T${time}:00`, all_day: allDay, duration_min: d.duration_min || null,
      repeat: lunar ? d.repeat : $<HTMLSelectElement>("e_r").value || null, remind_before_min: mins, lunar: d.lunar,
    };
    btn.disabled = true;
    try {
      showSaved(await api.create(body));
    } catch (x) {
      btn.disabled = false;
      fail(x instanceof Error ? x.message : "Chưa lưu được, bạn thử lại.");
    }
  };
  $("e_t").focus();
}

function showCard(text: string, r: ParseResult) {
  const d = r.draft;
  if (r.status === "need_info") {
    const miss = (r.missing ?? []).map((m) => (m === "title" ? "việc cần làm" : "ngày giờ")).join(", ");
    show(`<div class="who">Trợ lý</div><div>Mình chưa hiểu đủ, còn thiếu <b>${miss}</b>. Bạn thử nói rõ hơn, ví dụ "họp 3h chiều mai".</div>`);
    return;
  }
  const conf = (r.conflicts ?? []).map((c) => `<div class="note">Trùng giờ với <b>${esc(c.title)}</b> (${esc(fmtD(c.occurrence))} ${esc(fmtT(c.occurrence))})</div>`).join("");
  const warn = d.warnings.map((w) => `<div class="note">${esc(w)}</div>`).join("");
  const rep = repText(d.repeat, d.lunar?.[0], d.lunar?.[1]);
  const facts = `<div class="fact">${ICO.cal}<span>${esc(whenLong(d.start!, d.all_day))}</span></div>`
    + (rep ? `<div class="fact">${ICO.rep}<span>${esc(rep)}</span></div>` : "")
    + (d.remind_before_min ? `<div class="fact">${ICO.bell}<span>Nhắc trước ${d.remind_before_min} phút</span></div>` : "");
  const tags = (d.used_ai ? '<span class="tag">AI hỗ trợ</span>' : "") + (d.memory ? '<span class="tag">theo cách nói đã nhớ</span>' : "");
  const card = `<div class="who">Trợ lý hiểu là</div><p class="dt">${esc(d.title)}</p><div class="facts">${facts}</div>${tags ? `<div class="tags">${tags}</div>` : ""}${conf}${warn}
    <div class="actions"><button class="btn" id="ok">Lưu</button><button class="btn ghost" id="edit">Sửa</button><button class="btn ghost" id="no">Bỏ qua</button></div>`;
  const bind = () => {
    $("no").onclick = () => show("");
    $("edit").onclick = () => openEdit(d, () => { show(card); bind(); });
    $("ok").onclick = async () => {
      $<HTMLButtonElement>("ok").disabled = true;
      try {
        const r2 = await api.parse(text, true);
        if (!r2.event) throw new Error("Chưa lưu được, bạn thử lại.");
        showSaved(r2.event);
      } catch (e) {
        show(`<div class="note">${esc(e instanceof Error ? e.message : "Chưa lưu được, bạn thử lại.")}</div>`);
      }
    };
  };
  show(card);
  bind();
}

async function understand() {
  const text = $<HTMLTextAreaElement>("q").value.trim();
  if (!text) return;
  if (voiceLast && text !== voiceLast) {
    api.learn(voiceLast, text).catch(() => undefined);
    voiceLast = null;
  }
  toast("");
  const go = $<HTMLButtonElement>("go");
  go.disabled = true;
  try {
    showCard(text, await api.parse(text));
  } catch (e) {
    toast("Chưa kết nối được máy tính: " + (e instanceof Error ? e.message : e));
  } finally {
    go.disabled = false;
  }
}

/* ---------- giọng nói ---------- */
const recorder = new Recorder();
async function toggleMic() {
  if (recorder.on) { recorder.stop(); return; }
  if (!Recorder.supported()) { toast("Cửa sổ này không hỗ trợ ghi âm."); return; }
  try {
    const st = await api.sttStatus();
    if (!st.enabled) { toast('Nhập bằng giọng nói chưa bật trên máy tính. Vào Config của app, chọn "Nhập bằng giọng nói" rồi lưu.'); return; }
    if (!st.ready) { toast("Mô hình giọng nói đang tải (lần đầu mất vài phút). Bạn gõ tạm nhé."); return; }
  } catch {
    toast("Chưa kết nối được máy tính. Bạn gõ tạm nhé.");
    return;
  }
  $("mic").classList.add("mic-on");
  toast("Đang nghe… bấm mic lần nữa khi nói xong.");
  let blob: Blob | null;
  try {
    blob = await recorder.start();
  } catch (e) {
    $("mic").classList.remove("mic-on");
    toast((e as DOMException).name === "NotFoundError" ? "Chưa thấy micro trên máy này." : "Chưa được cấp quyền micro. Vào Cài đặt > quyền của app để bật.");
    return;
  }
  $("mic").classList.remove("mic-on");
  if (!blob) { toast("Không nghe thấy gì."); return; }
  toast("Đang chuyển thành chữ…");
  try {
    const x = await api.stt(toBase64(await toWav(blob)));
    if (!x.text) { toast("Không nghe rõ, bạn nói lại giúp mình nhé."); return; }
    toast("");
    voiceLast = x.text;
    $<HTMLTextAreaElement>("q").value = x.text;
    growQ();
    void understand();
  } catch (e) {
    toast(e instanceof Error && e.message ? e.message : "Nhận giọng nói gặp lỗi.");
  }
}

/* ---------- Sắp tới ---------- */
async function refreshList() {
  const el = $("list");
  try {
    const info = await api.info();
    today = info.now.slice(0, 10);
    const ev = await api.events(dayStart(info.now), dayStart(info.now, 7));
    if (!ev.length) { el.innerHTML = '<div class="empty">Chưa có việc nào trong 7 ngày tới.</div>'; return; }
    let html = "", cur = "";
    for (const e of ev) {
      const k = e.occurrence.slice(0, 10);
      if (k !== cur) {
        cur = k;
        const diff = Math.round((Date.parse(k) - Date.parse(today)) / 864e5);
        const base = `${wdOf(k)}, ${fmtD(k)}`;
        html += `<div class="day${diff === 0 ? " today" : ""}">${diff === 0 ? `Hôm nay <small>${base}</small>` : diff === 1 ? `Ngày mai <small>${base}</small>` : base}</div>`;
      }
      const rep = repText(e.repeat, e.lunar_day, e.lunar_month);
      html += `<div class="ev"><div class="time${e.all_day ? " all" : ""}">${e.all_day ? "Cả ngày" : fmtT(e.occurrence)}</div>`
        + `<div class="bar${e.repeat === "lunar_yearly" ? " lunar" : e.repeat ? " rep" : ""}"></div>`
        + `<div class="body"><b>${esc(e.title)}</b>${rep ? `<span class="t">${esc(rep)}</span>` : ""}</div>`
        + `<button class="del" aria-label="Xóa" data-id="${e.id}" data-rep="${e.repeat ?? ""}">${ICO.x}</button></div>`;
    }
    el.innerHTML = html;
    el.querySelectorAll<HTMLButtonElement>(".del").forEach((b) => {
      b.onclick = async () => {
        if (!confirm(b.dataset.rep ? "Xóa toàn bộ chuỗi lịch lặp này?" : "Xóa việc này?")) return;
        try {
          await api.remove(Number(b.dataset.id));
        } catch (e) {
          el.insertAdjacentHTML("afterbegin", `<div class="note">${esc(e instanceof Error ? e.message : "Chưa xóa được")}</div>`);
          return;
        }
        await doSync();
        void refreshList();
      };
    });
  } catch {
    el.innerHTML = `<div class="empty">Chưa kết nối được máy tính. ${esc(lastText())}</div>`;
  }
}

/* ---------- Cài đặt ---------- */
const PERM_LABEL: Record<PermState, string> = { granted: "Đã cấp", denied: "Bị từ chối", prompt: "Chưa cấp", unknown: "Không rõ" };
const pill = (s: PermState) => `<span class="pill ${s === "granted" ? "granted" : "other"}">${PERM_LABEL[s]}</span>`;

async function renderSettings() {
  const perms = await checkPerms();
  const bgOn = (await prefs.get(KEY.bgEnabled)) !== "0";
  const lastBg = Number(await prefs.get(KEY.bgLastRun)) || 0;
  const bgErr = (await prefs.get(KEY.bgLastError)) || "";
  const bgText = (lastBg ? "Lần đồng bộ nền gần nhất: " + fmtStamp(lastBg) : "Chưa có lần đồng bộ nền nào") + (bgErr ? ` (lần cuối lỗi: ${bgErr})` : "");
  $("tab-settings").innerHTML = `<div class="set">
    <div class="card"><h3>Máy chủ LicSoLo</h3>
      <input id="s_url" type="url" inputmode="url" autocapitalize="off" value="${esc(serverUrl)}">
      <div class="actions"><button class="btn" id="s_save">Lưu địa chỉ</button><button class="btn ghost" id="s_sync">Đồng bộ ngay</button></div>
      <p id="s_msg">${esc(lastText())}</p></div>
    <div class="card"><h3>Quyền của app</h3>
      <div class="row"><span>Lịch</span>${pill(perms.calendar)}</div>
      <div class="row"><span>Thông báo</span>${pill(perms.notifications)}</div>
      <div class="row"><span>Báo thức chính xác</span>${pill(perms.exactAlarm)}</div>
      <p>Micro được hỏi ở lần bấm nút mic đầu tiên.</p>
      <div class="actions"><button class="btn" id="s_req">Cấp quyền còn thiếu</button><button class="btn ghost" id="s_app">Mở cài đặt của app</button><button class="btn ghost" id="s_exact">Báo thức chính xác</button></div></div>
    <div class="card"><h3>Để thông báo nổ đúng giờ (HyperOS)</h3>
      <p>Làm cho <b>cả app này lẫn Tailscale</b>, nếu không hệ thống có thể tắt app khi khóa màn hình:</p>
      <ol><li>Bật <b>Tự khởi động</b>.</li><li>Pin: chọn <b>Không hạn chế</b>.</li><li>Đừng vuốt tắt app khỏi danh sách gần đây nếu không cần.</li></ol>
      <div class="actions"><button class="btn ghost" id="s_auto">Mở Tự khởi động</button><button class="btn ghost" id="s_bat">Mở cài đặt pin</button></div></div>
    <div class="card"><h3>Đồng bộ nền</h3>
      <label class="row"><span>Mỗi 15 phút, kể cả khi đóng app</span><input type="checkbox" id="s_bg"${bgOn ? " checked" : ""}></label>
      <p>${esc(bgText)}</p>
      <p>Chạy nền chỉ <b>hẹn thêm thông báo</b> cho việc mới. Lịch hệ thống chỉ được cập nhật khi bạn mở app. Hệ thống (nhất là HyperOS) có thể hoãn hoặc chặn việc chạy nền nếu pin bị hạn chế.</p>
      <div class="actions"><button class="btn ghost" id="s_bat2">Mở cài đặt pin</button></div></div>
    <div class="card"><h3>Lịch trên điện thoại</h3>
      <p>Việc của LicSoLo hiện trong lịch hệ thống, ở lịch "Trợ lý thời gian" (chỉ đọc; muốn sửa thì xóa và tạo lại trong app).</p>
      <div class="actions"><button class="btn warn" id="s_wipe">Xóa lịch khỏi điện thoại</button></div></div></div>`;
  const msg = (t: string) => { $("s_msg").textContent = t; };
  $("s_save").onclick = async () => {
    serverUrl = $<HTMLInputElement>("s_url").value.trim() || DEFAULT_URL;
    await prefs.set(KEY.serverUrl, serverUrl);
    msg("Đã lưu. Bấm Đồng bộ ngay để thử.");
  };
  $("s_sync").onclick = async () => {
    msg("Đang đồng bộ…");
    const r = await doSync();
    msg(r.error ? "Chưa kết nối được máy tính: " + r.error : lastText());
  };
  $("s_req").onclick = async () => {
    await requestPerms({ calendar: perms.calendar !== "granted", notifications: perms.notifications !== "granted" });
    await renderSettings();
  };
  $("s_app").onclick = () => void LvSystem.openAppSettings();
  $("s_exact").onclick = () => void LvSystem.openExactAlarmSettings();
  $("s_auto").onclick = () => void LvSystem.openAutostart();
  $("s_bat").onclick = () => void LvSystem.openBatterySettings();
  $("s_bat2").onclick = () => void LvSystem.openBatterySettings();
  $<HTMLInputElement>("s_bg").onchange = (e) => { void prefs.set(KEY.bgEnabled, (e.target as HTMLInputElement).checked ? "1" : "0"); };
  $("s_wipe").onclick = async () => {
    if (!confirm("Xóa lịch \"Trợ lý thời gian\" khỏi điện thoại và hủy mọi thông báo đã hẹn? Việc trong LicSoLo vẫn còn nguyên.")) return;
    try { await removeEverything(); msg("Đã xóa lịch và hủy thông báo."); } catch (e) { msg("Chưa xóa được: " + (e instanceof Error ? e.message : e)); }
  };
}

/* ---------- lần chạy đầu: xin quyền, mỗi quyền một dòng giải thích ---------- */
async function onboardIfNeeded() {
  if ((await prefs.get(KEY.onboarded)) === "1") return;
  const box = $("onboard");
  box.hidden = false;
  box.innerHTML = `<h1>Chào bạn</h1><p>App cần vài quyền để làm đúng việc của nó:</p>
    <div class="item"><b>Lịch</b><span>Để ghi việc của LicSoLo vào lịch điện thoại.</span></div>
    <div class="item"><b>Thông báo</b><span>Để nhắc bạn đúng giờ, kể cả khi khóa màn hình.</span></div>
    <div class="item"><b>Báo thức chính xác</b><span>Để thông báo nổ đúng phút, không bị trễ do hệ thống tiết kiệm pin.</span></div>
    <div class="item"><b>Micro</b><span>Để bạn nói việc cần nhớ thay vì gõ. Hệ thống sẽ hỏi khi bạn bấm nút mic lần đầu.</span></div>
    <div class="actions"><button class="btn" id="ob_go">Cấp quyền</button><button class="btn ghost" id="ob_skip">Để sau</button></div>`;
  const finish = async () => { await prefs.set(KEY.onboarded, "1"); box.hidden = true; void doSync().then(() => refreshList()); };
  $("ob_skip").onclick = () => void finish();
  $("ob_go").onclick = async () => {
    const perms: PermReport = await requestPerms({ calendar: true, notifications: true });
    if (perms.exactAlarm !== "granted" && perms.exactAlarm !== "unknown") await LvSystem.openExactAlarmSettings();
    await finish();
  };
}

/* ---------- đồng bộ định kỳ khi app đang mở ---------- */
let loop: ReturnType<typeof setInterval> | undefined;
function startLoop() {
  stopLoop();
  loop = setInterval(() => { void doSync(); }, SYNC_EVERY_MS);
}
function stopLoop() {
  if (loop !== undefined) clearInterval(loop);
  loop = undefined;
}

/* ---------- khởi động ---------- */
function bindUi() {
  $("go").onclick = () => void understand();
  $("mic").onclick = () => void toggleMic();
  const q = $<HTMLTextAreaElement>("q");
  q.addEventListener("input", growQ);
  q.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void understand(); } });
  document.querySelectorAll<HTMLButtonElement>("#nav button").forEach((b) => {
    b.onclick = () => {
      document.querySelectorAll<HTMLButtonElement>("#nav button").forEach((x) => x.classList.toggle("on", x === b));
      for (const t of ["main", "upcoming", "settings"]) $("tab-" + t).hidden = t !== b.dataset.tab;
      if (b.dataset.tab === "upcoming") void refreshList();
      if (b.dataset.tab === "settings") void renderSettings();
    };
  });
  void App.addListener("appStateChange", (s) => {
    if (s.isActive) { void doSync().then(() => refreshList()); startLoop(); } else stopLoop();
  });
  // mạng nối lại thì đồng bộ ngay (app đang mở)
  void Network.addListener("networkStatusChange", (st) => { if (st.connected) void doSync().then(() => refreshList()); });
  startLoop();
}

async function boot() {
  bindUi();
  serverUrl = (await prefs.get(KEY.serverUrl)) || DEFAULT_URL;
  const ls = await prefs.get(KEY.lastSync);
  lastSync = ls ? Number(ls) : null;
  setSyncLine(lastText());
  await onboardIfNeeded();
  if ((await prefs.get(KEY.onboarded)) === "1") void doSync().then(() => refreshList());
}

void boot();
