import type { Occurrence, ReminderPoint, ServerInfo, SyncApi } from "./types";
import { DAY, MIN, dayStart, offsetOf, parts, stamp } from "./timeutil";

/* Phần dùng chung giữa app (sync.ts) và runner nền (runner.ts): lấy việc từ server và tính mốc nhắc.
 * Không import gì của Capacitor, để bó được thành một tệp JS chạy trong background-runner. */

export const PAST_DAYS = 7;
export const AHEAD_DAYS = 120;
export const LUNAR_AHEAD_DAYS = 400;
export const NOTIFY_WINDOW_DAYS = 30;
export const MAX_NOTIFICATIONS = 200;
export const ALL_DAY_REMIND_HOUR = 8;

/** id thông báo: số nguyên dương 31 bit, ổn định theo ref (FNV-1a). */
export function notificationId(ref: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < ref.length; i++) {
    h ^= ref.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) & 0x7fffffff;
}

/** Cùng dạng với UID trong .ics của server: lv-<id>-<yyyymmddHHMM>. */
export const eventRef = (o: Occurrence) => `lv-${o.id}-${stamp(o.occurrence)}`;

const pad = (n: number) => String(n).padStart(2, "0");

function whenText(o: Occurrence): string {
  const t = parts(o.occurrence);
  const date = `${pad(t.d)}/${pad(t.mo)}`;
  return o.all_day ? `${date} cả ngày` : `${pad(t.h)}:${pad(t.mi)} ${date}`;
}

/** Mốc nhắc của một lần xảy ra. Chép quy tắc service._stages / service._fire_points:
 * mốc gốc là giờ diễn ra (việc cả ngày: 08:00 hôm đó); việc thường nhắc trước remind_before_min;
 * giỗ (lunar_yearly) nhắc thêm trước 7 ngày và 1 ngày.
 * Quy tắc này đang trùng với server; khi tích hợp hệ sinh thái thì chuyển sang GET /v1/reminders/upcoming. */
export function reminderPointsFor(o: Occurrence): ReminderPoint[] {
  const base = o.all_day
    ? Date.parse(`${o.occurrence.slice(0, 10)}T${pad(ALL_DAY_REMIND_HOUR)}:00:00${offsetOf(o.occurrence_iso)}`)
    : Date.parse(o.occurrence_iso);
  const ref = eventRef(o);
  const onTime = { suffix: "", delta: (o.remind_before_min || 0) * MIN, title: o.title };
  const stages = o.repeat === "lunar_yearly"
    ? [
      { suffix: "-7d", delta: 7 * DAY, title: "Còn 7 ngày: " + o.title },
      { suffix: "-1d", delta: DAY, title: "Ngày mai: " + o.title },
      onTime,
    ]
    : [onTime];
  const body = [whenText(o), (o.notes ?? "").trim().slice(0, 200)].filter(Boolean).join(" · ");
  return stages.map((s) => ({ ref: ref + s.suffix, atMs: base - s.delta, title: s.title, body }));
}

/** Các mốc sẽ hẹn: chưa qua giờ, trong 30 ngày tới, lấy tối đa 200 mốc gần nhất. */
export function reminderPoints(occs: Occurrence[], nowMs: number): ReminderPoint[] {
  const end = nowMs + NOTIFY_WINDOW_DAYS * DAY;
  const seen = new Set<string>();
  const out: ReminderPoint[] = [];
  for (const o of occs) {
    for (const r of reminderPointsFor(o)) {
      if (r.atMs <= nowMs || r.atMs > end || seen.has(r.ref)) continue;
      seen.add(r.ref);
      out.push(r);
    }
  }
  out.sort((a, b) => a.atMs - b.atMs || (a.ref < b.ref ? -1 : 1));
  return out.slice(0, MAX_NOTIFICATIONS);
}

/** Gán id thông báo; nếu hai ref trùng id (xác suất cực nhỏ) thì dịch sang số kế tiếp. */
export function withIds(points: ReminderPoint[]): (ReminderPoint & { id: number })[] {
  const used = new Set<number>();
  return points.map((p) => {
    let id = notificationId(p.ref);
    while (used.has(id)) id = (id + 1) & 0x7fffffff;
    used.add(id);
    return { ...p, id };
  });
}

/** Mọi việc trong [hôm nay-7, hôm nay+120]; riêng giỗ (lunar_yearly) lấy tới hôm nay+400 để luôn hiện trước trong lịch. */
export async function fetchOccurrences(api: SyncApi, info: ServerInfo): Promise<Occurrence[]> {
  const lo = dayStart(info.now, -PAST_DAYS);
  // "to" của server là mốc loại trừ: +1 ngày để lấy trọn ngày cuối
  const [near, far] = await Promise.all([
    api.events(lo, dayStart(info.now, AHEAD_DAYS + 1)),
    api.events(lo, dayStart(info.now, LUNAR_AHEAD_DAYS + 1)),
  ]);
  const byRef = new Map<string, Occurrence>();
  for (const o of near) byRef.set(eventRef(o), o);
  for (const o of far) if (o.repeat === "lunar_yearly") byRef.set(eventRef(o), o);
  return [...byRef.values()].sort((a, b) => (a.occurrence < b.occurrence ? -1 : a.occurrence > b.occurrence ? 1 : a.id - b.id));
}

/* ---------- chia việc giữa app và runner nền ----------
 * background-runner hẹn thông báo bằng bộ hẹn riêng của nó và app không hủy được các thông báo đó (và ngược lại).
 * Để một mốc không nổ hai lần, mỗi bên ghi lại "ref -> giờ hẹn" những mốc mình đã hẹn (app: appRefs, runner: bgRefs)
 * và bên kia bỏ qua các mốc đó. Hệ quả: runner chỉ THÊM mốc mới; việc bị sửa hoặc xóa sau khi runner đã hẹn
 * thì mốc cũ vẫn nổ, cho tới khi nó qua giờ. */
export type RefMap = Record<string, number>;

/** Mốc nào đã nằm trong `taken` với đúng giờ hẹn đó thì bỏ. */
export function withoutTaken<T extends ReminderPoint>(points: T[], taken: RefMap): T[] {
  return points.filter((p) => taken[p.ref] !== p.atMs);
}

/** Bỏ các mốc đã qua giờ khỏi bản ghi (để bản ghi không phình ra mãi). */
export function pruneRefs(refs: RefMap, nowMs: number): RefMap {
  const out: RefMap = {};
  for (const k of Object.keys(refs)) if (refs[k] > nowMs) out[k] = refs[k];
  return out;
}

export function refMapOf(points: ReminderPoint[]): RefMap {
  const out: RefMap = {};
  for (const p of points) out[p.ref] = p.atMs;
  return out;
}

export function parseRefMap(raw: string | null | undefined): RefMap {
  if (!raw) return {};
  try {
    const v = JSON.parse(raw);
    return v && typeof v === "object" && !Array.isArray(v) ? (v as RefMap) : {};
  } catch {
    return {};
  }
}

/** Runner: các mốc cần hẹn thêm = mốc hiện có trừ những mốc app hoặc chính nó đã hẹn. */
export function planBackground(points: ReminderPoint[], appRefs: RefMap, bgRefs: RefMap, nowMs: number) {
  const mine = pruneRefs(bgRefs, nowMs);
  const toSchedule = withoutTaken(withoutTaken(points, appRefs), mine);
  return { toSchedule, bgRefs: { ...mine, ...refMapOf(toSchedule) } };
}

/** Giờ hẹn gửi cho background-runner. Runner đọc chuỗi này bằng SimpleDateFormat không đặt múi giờ
 * (đọc theo múi giờ của máy, bỏ qua chữ Z), nên phải cộng độ lệch múi giờ của máy để ra đúng thời điểm. */
export function runnerScheduleAt(atMs: number, deviceOffsetMin: number): string {
  return new Date(atMs + deviceOffsetMin * MIN).toISOString();
}
