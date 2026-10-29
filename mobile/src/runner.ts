import { DEFAULT_URL, KEY, RUNNER_EVENT } from "./config";
import {
  choosePoints, fetchOccurrences, mergePending, parsePending, parseRefMap, pendingOf, planBackground, reportDeliveries,
  runnerScheduleAt, withIds,
} from "./reminders";
import type { Occurrence, ServerInfo, SyncApi, UpcomingReminder } from "./types";

/* Runner nền (@capacitor/background-runner): chạy JS định kỳ ~15 phút kể cả khi app đóng.
 * Môi trường của nó không có DOM và không gọi được plugin Capacitor tự viết (LvCalendar), chỉ có
 * fetch, CapacitorKV và CapacitorNotifications. Vì vậy runner CHỈ lấy việc và hẹn thêm thông báo;
 * ghi lịch hệ thống vẫn chỉ làm khi mở app (sync.ts). Tính mốc nhắc dùng chung module với sync.ts. */

declare function addEventListener(
  name: string,
  cb: (resolve: (v?: unknown) => void, reject: (e?: unknown) => void, args: unknown) => void,
): void;
declare const CapacitorKV: {
  get(key: string): { value: string | null } | null;
  set(key: string, value: string): void;
};
declare const CapacitorNotifications: {
  schedule(n: { id: number; title: string; body: string; scheduleAt: string }[]): void;
};

const kv = (k: string): string | null => CapacitorKV.get(k)?.value ?? null;

async function getJson<T>(base: string, path: string): Promise<T> {
  const r = await fetch(base + "/v1" + path, { method: "GET", headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return (await r.json()) as T;
}

async function postJson(base: string, path: string, body: unknown): Promise<void> {
  const r = await fetch(base + "/v1" + path, {
    method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
}

async function run(): Promise<void> {
  if (kv(KEY.bgEnabled) === "0") return;
  const base = (kv(KEY.serverUrl) || DEFAULT_URL).trim().replace(/\/+$/, "");
  const api: SyncApi = {
    info: () => getJson<ServerInfo>(base, "/info"),
    events: (from: string, to: string) =>
      getJson<Occurrence[]>(base, `/events?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`),
    upcoming: (days: number, deviceId: string) => getJson<UpcomingReminder[]>(
      base, `/reminders/upcoming?days=${days}&device_id=${encodeURIComponent(deviceId)}&skip_acked=1`),
    delivered: (deviceId: string, eventId: number, key: string) =>
      postJson(base, "/reminders/delivered", { device_id: deviceId, event_id: eventId, key }),
  };
  // Runner không tự đăng ký thiết bị (việc của app): chỉ dùng device_id khi app đã đăng ký với đúng server này.
  const id = kv(KEY.deviceId);
  const deviceId = id && kv(KEY.deviceRegistered) === base ? id : null;
  try {
    const now = Date.now();
    const chosen = await choosePoints(api, deviceId, async () => fetchOccurrences(api, await api.info()), now);
    const plan = planBackground(chosen.points, parseRefMap(kv(KEY.appRefs)), parseRefMap(kv(KEY.bgRefs)), now);
    const off = Number(kv(KEY.tzOffsetMin) ?? 0) || 0;
    const items = withIds(plan.toSchedule).map((p) => ({
      id: p.id, title: p.title, body: p.body, scheduleAt: runnerScheduleAt(p.atMs, off),
    }));
    if (items.length) CapacitorNotifications.schedule(items);
    CapacitorKV.set(KEY.bgRefs, JSON.stringify(plan.bgRefs));
    // báo delivered cho mốc runner đã hẹn mà giờ nhắc đã qua; lỗi ở đây không làm hỏng việc hẹn
    try {
      const rep = await reportDeliveries(api, deviceId, parsePending(kv(KEY.bgPending)), now);
      CapacitorKV.set(KEY.bgPending, JSON.stringify(mergePending(rep.failed, rep.waiting, pendingOf(plan.toSchedule))));
    } catch { /* thử lại lần chạy sau */ }
    CapacitorKV.set(KEY.bgLastRun, String(now));
    CapacitorKV.set(KEY.bgLastError, "");
  } catch (e) {
    // mất mạng, máy tính tắt, proxy chưa mở: giữ nguyên những gì đã hẹn
    CapacitorKV.set(KEY.bgLastError, e instanceof Error ? e.message : String(e));
  }
}

addEventListener(RUNNER_EVENT, (resolve, reject) => {
  run().then(() => resolve(), (e) => reject(e));
});
