import { DEFAULT_URL, KEY, RUNNER_EVENT } from "./config";
import { fetchOccurrences, parseRefMap, planBackground, reminderPoints, runnerScheduleAt, withIds } from "./reminders";
import type { Occurrence, ServerInfo } from "./types";

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

async function run(): Promise<void> {
  if (kv(KEY.bgEnabled) === "0") return;
  const base = (kv(KEY.serverUrl) || DEFAULT_URL).trim().replace(/\/+$/, "");
  const api = {
    info: () => getJson<ServerInfo>(base, "/info"),
    events: (from: string, to: string) =>
      getJson<Occurrence[]>(base, `/events?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`),
  };
  try {
    const now = Date.now();
    const occs = await fetchOccurrences(api, await api.info());
    const plan = planBackground(
      reminderPoints(occs, now), parseRefMap(kv(KEY.appRefs)), parseRefMap(kv(KEY.bgRefs)), now,
    );
    const off = Number(kv(KEY.tzOffsetMin) ?? 0) || 0;
    const items = withIds(plan.toSchedule).map((p) => ({
      id: p.id, title: p.title, body: p.body, scheduleAt: runnerScheduleAt(p.atMs, off),
    }));
    if (items.length) CapacitorNotifications.schedule(items);
    CapacitorKV.set(KEY.bgRefs, JSON.stringify(plan.bgRefs));
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
