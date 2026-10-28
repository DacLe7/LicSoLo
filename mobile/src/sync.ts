import type {
  CalendarDiff, CalendarItem, CalendarPort, ManagedEntry, NotifierPort, Occurrence, ReminderPoint,
  ServerInfo, SyncApi, SyncResult,
} from "./types";
import { DAY, MIN, dayStart, offsetOf, parts, stamp } from "./timeutil";

/* Đồng bộ một chiều LicSoLo -> lịch hệ thống + thông báo cục bộ. Không chạm vào điện thoại thật:
 * mọi thứ bên ngoài (HTTP, lịch, thông báo) đi qua cổng được truyền vào, nên kiểm thử bằng giả lập. */

export const PAST_DAYS = 7;
export const AHEAD_DAYS = 120;
export const LUNAR_AHEAD_DAYS = 400;
export const NOTIFY_WINDOW_DAYS = 30;
export const MAX_NOTIFICATIONS = 200;
export const DEFAULT_DURATION_MIN = 60;
export const ALL_DAY_REMIND_HOUR = 8;

/** Hash 53 bit (cyrb53), đủ để nhận ra nội dung việc đã đổi. */
export function hashText(s: string): string {
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16);
}

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

export function toCalendarItem(o: Occurrence, tz: string): CalendarItem {
  let startMs: number, endMs: number, zone: string;
  if (o.all_day) {
    // CalendarContract bắt buộc việc cả ngày là 00:00 UTC và EVENT_TIMEZONE = UTC
    const t = parts(o.occurrence);
    startMs = Date.UTC(t.y, t.mo - 1, t.d);
    endMs = startMs + DAY;
    zone = "UTC";
  } else {
    startMs = Date.parse(o.occurrence_iso);
    endMs = startMs + (o.duration_min || DEFAULT_DURATION_MIN) * MIN;
    zone = tz;
  }
  const notes = (o.notes ?? "").trim();
  return {
    ref: eventRef(o), title: o.title, startMs, endMs, allDay: o.all_day, tz: zone, notes,
    hash: hashText(JSON.stringify([o.title, startMs, endMs, o.all_day, notes])),
  };
}

/** So mong muốn với những gì đang có trong lịch của app: ref mới thì thêm, hash khác thì sửa, ref mất thì xóa. */
export function diffCalendar(desired: CalendarItem[], managed: ManagedEntry[]): CalendarDiff {
  const want = new Map(desired.map((d) => [d.ref, d]));
  const have = new Map<string, ManagedEntry>();
  const diff: CalendarDiff = { insert: [], update: [], delete: [] };
  for (const m of managed) {
    if (!want.has(m.ref) || have.has(m.ref)) diff.delete.push(m.eventId); // ref không còn, hoặc bị ghi trùng
    else have.set(m.ref, m);
  }
  for (const d of want.values()) {
    const m = have.get(d.ref);
    if (!m) diff.insert.push(d);
    else if (m.hash !== d.hash) diff.update.push({ ...d, eventId: m.eventId });
  }
  return diff;
}

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

export interface SyncDeps {
  api: SyncApi;
  calendar: CalendarPort;
  notifier: NotifierPort;
  now?: () => number;
}

const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
const empty: SyncResult = { ok: false, inserted: 0, updated: 0, deleted: 0, scheduled: 0, occurrences: [] };

export function createSync(deps: SyncDeps) {
  const now = deps.now ?? Date.now;
  let running: Promise<SyncResult> | null = null;

  async function once(): Promise<SyncResult> {
    let info: ServerInfo, occs: Occurrence[];
    try {
      info = await deps.api.info();
      occs = await fetchOccurrences(deps.api, info);
    } catch (e) {
      return { ...empty, error: msg(e) }; // mất mạng: giữ nguyên lịch và thông báo cũ
    }
    const res: SyncResult = { ...empty, ok: true, occurrences: occs };
    try {
      await deps.calendar.ensureCalendar();
      const desired = occs.map((o) => toCalendarItem(o, info.tz));
      const diff = diffCalendar(desired, await deps.calendar.listManaged());
      if (diff.insert.length || diff.update.length || diff.delete.length) await deps.calendar.applyDiff(diff);
      res.inserted = diff.insert.length;
      res.updated = diff.update.length;
      res.deleted = diff.delete.length;
    } catch (e) {
      res.ok = false;
      res.calendarError = msg(e);
    }
    try {
      const points = withIds(reminderPoints(occs, now()));
      await deps.notifier.cancelAll();
      if (points.length) await deps.notifier.schedule(points);
      res.scheduled = points.length;
    } catch (e) {
      res.ok = false;
      res.notifyError = msg(e);
    }
    return res;
  }

  /** Đang chạy thì trả lại chính lần chạy đó, không chạy chồng. */
  return function run(): Promise<SyncResult> {
    if (!running) running = once().finally(() => { running = null; });
    return running;
  };
}
