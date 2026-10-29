import type {
  CalendarDiff, CalendarItem, CalendarPort, DevicePort, ManagedEntry, NotifierPort, Occurrence, PendingDelivery,
  ServerInfo, SyncApi, SyncResult,
} from "./types";
import { DAY, MIN, parts } from "./timeutil";
import {
  choosePoints, eventRef, fetchOccurrences, mergePending, pendingOf, pruneRefs, refMapOf, reportDeliveries, withIds,
  withoutTaken,
} from "./reminders";
import type { RefMap } from "./reminders";

/* Đồng bộ một chiều LicSoLo -> lịch hệ thống + thông báo cục bộ. Không chạm vào điện thoại thật:
 * mọi thứ bên ngoài (HTTP, lịch, thông báo) đi qua cổng được truyền vào, nên kiểm thử bằng giả lập. */

export const DEFAULT_DURATION_MIN = 60;

// mốc nhắc và việc lấy từ server nằm ở reminders.ts (dùng chung với runner nền)
export * from "./reminders";

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

export interface SyncDeps {
  api: SyncApi;
  calendar: CalendarPort;
  notifier: NotifierPort;
  now?: () => number;
  /** Danh tính thiết bị: có thì app đăng ký với server, lấy mốc từ /upcoming và báo delivered. Không có = như bản cũ. */
  device?: DevicePort;
  /** Chia việc với runner nền (xem reminders.ts). Không truyền thì app tự hẹn mọi mốc. */
  shared?: {
    bgRefs(): Promise<RefMap>;
    saveAppRefs(refs: RefMap): Promise<void>;
  };
}

const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
const REGISTER_RETRY_MS = 10 * MIN; // server cũ hoặc đã đủ 20 thiết bị: đừng gọi đăng ký mỗi phút

const empty: SyncResult = { ok: false, inserted: 0, updated: 0, deleted: 0, scheduled: 0, occurrences: [] };

export function createSync(deps: SyncDeps) {
  const now = deps.now ?? Date.now;
  let running: Promise<SyncResult> | null = null;
  let registerRetryAt = 0;

  /** device_id đã đăng ký với server, hoặc null (không có DevicePort, server cũ, đã đủ thiết bị): khi đó dùng quy tắc tự tính. */
  async function ensureDevice(force = false): Promise<string | null> {
    const dev = deps.device;
    if (!dev || !deps.api.registerDevice || (!force && now() < registerRetryAt)) return null;
    try {
      const id = await dev.deviceId();
      if (force || !(await dev.isRegistered())) {
        await deps.api.registerDevice(id, "android"); // idempotent: đã đăng ký rồi thì chỉ cập nhật
        await dev.setRegistered(true);
      }
      return id;
    } catch {
      registerRetryAt = now() + REGISTER_RETRY_MS;
      return null;
    }
  }

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
    const t = now();
    const deviceId = await ensureDevice();
    let scheduledNow: PendingDelivery[] = [];
    try {
      const chosen = await choosePoints(deps.api, deviceId, async () => occs, t, () => ensureDevice(true));
      let points = chosen.points;
      res.reminderSource = chosen.source;
      if (deps.shared) points = withoutTaken(points, pruneRefs(await deps.shared.bgRefs(), t)); // mốc runner nền đã hẹn
      const withId = withIds(points);
      await deps.notifier.cancelAll();
      if (withId.length) await deps.notifier.schedule(withId);
      if (deps.shared) await deps.shared.saveAppRefs(refMapOf(points));
      res.scheduled = withId.length;
      scheduledNow = pendingOf(points);
    } catch (e) {
      res.ok = false;
      res.notifyError = msg(e);
    }
    if (deps.device) {
      try {
        // mốc lần trước đã tới giờ thì báo delivered; mốc chưa tới giờ nằm trong lần hẹn mới (scheduledNow) nếu còn hiệu lực
        const rep = await reportDeliveries(deps.api, deviceId, await deps.device.loadPending(), t);
        await deps.device.savePending(mergePending(rep.failed, scheduledNow));
        res.delivered = rep.reported;
      } catch {
        /* báo delivered chỉ là phần thêm, không làm hỏng đồng bộ */
      }
    }
    return res;
  }

  /** Đang chạy thì trả lại chính lần chạy đó, không chạy chồng. */
  return function run(): Promise<SyncResult> {
    if (!running) running = once().finally(() => { running = null; });
    return running;
  };
}
