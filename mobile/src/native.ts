import { registerPlugin } from "@capacitor/core";
import { LocalNotifications } from "@capacitor/local-notifications";
import { Preferences } from "@capacitor/preferences";
import { DEFAULT_URL, KEY, RUNNER_LABEL } from "./config";
import { makeDevicePort } from "./device";
import { parseRefMap } from "./reminders";
import type { RefMap } from "./reminders";
import type { CalendarDiff, CalendarPort, ManagedEntry, NotifierPort, ReminderPoint } from "./types";

/* Lớp mỏng nối TypeScript với plugin Android. Logic nằm ở sync.ts; ở đây không có quyết định nào. */

interface LvCalendarPlugin {
  checkPermissions(): Promise<{ calendar: string }>;
  requestPermissions(): Promise<{ calendar: string }>;
  ensureCalendar(): Promise<{ calendarId: number }>;
  listManaged(): Promise<{ items: ManagedEntry[] }>;
  applyDiff(diff: CalendarDiff): Promise<void>;
  removeAll(): Promise<void>;
}

interface LvSystemPlugin {
  openAppSettings(): Promise<{ opened: boolean }>;
  openAutostart(): Promise<{ opened: boolean; direct: boolean }>;
  openBatterySettings(): Promise<{ opened: boolean }>;
  openExactAlarmSettings(): Promise<{ opened: boolean }>;
}

export const LvCalendar = registerPlugin<LvCalendarPlugin>("LvCalendar");
export const LvSystem = registerPlugin<LvSystemPlugin>("LvSystem");

export const calendarPort: CalendarPort = {
  async ensureCalendar() { await LvCalendar.ensureCalendar(); },
  async listManaged() { return (await LvCalendar.listManaged()).items; },
  async applyDiff(diff) { await LvCalendar.applyDiff(diff); },
};

const CHANNEL = "reminders";

export const notifierPort: NotifierPort = {
  async cancelAll() {
    const { notifications } = await LocalNotifications.getPending();
    if (notifications.length) await LocalNotifications.cancel({ notifications: notifications.map((n) => ({ id: n.id })) });
  },
  async schedule(points: (ReminderPoint & { id: number })[]) {
    await LocalNotifications.createChannel({
      id: CHANNEL, name: "Nhắc việc", description: "Nhắc việc đến giờ", importance: 5, visibility: 1, vibration: true,
    });
    await LocalNotifications.schedule({
      notifications: points.map((p) => ({
        id: p.id,
        title: p.title,
        body: p.body,
        channelId: CHANNEL,
        schedule: { at: new Date(p.atMs), allowWhileIdle: true },
        extra: { ref: p.ref },
      })),
    });
  },
};

export type PermState = "granted" | "denied" | "prompt" | "unknown";

export interface PermReport {
  calendar: PermState;
  notifications: PermState;
  exactAlarm: PermState;
}

const norm = (s: string | undefined): PermState =>
  s === "granted" ? "granted" : s === "denied" ? "denied" : s === "prompt" || s === "prompt-with-rationale" ? "prompt" : "unknown";

export async function checkPerms(): Promise<PermReport> {
  const [cal, notif, exact] = await Promise.allSettled([
    LvCalendar.checkPermissions(),
    LocalNotifications.checkPermissions(),
    LocalNotifications.checkExactNotificationSetting(),
  ]);
  return {
    calendar: cal.status === "fulfilled" ? norm(cal.value.calendar) : "unknown",
    notifications: notif.status === "fulfilled" ? norm(notif.value.display) : "unknown",
    exactAlarm: exact.status === "fulfilled" ? norm(exact.value.exact_alarm) : "unknown",
  };
}

/** Xin các quyền còn thiếu. Mic do WebView tự xin khi bấm nút mic lần đầu (BridgeWebChromeClient). */
export async function requestPerms(which: { calendar?: boolean; notifications?: boolean }): Promise<PermReport> {
  if (which.calendar) await LvCalendar.requestPermissions().catch(() => undefined);
  if (which.notifications) await LocalNotifications.requestPermissions().catch(() => undefined);
  return checkPerms();
}

export async function removeEverything(): Promise<void> {
  await LvCalendar.removeAll();
  await notifierPort.cancelAll();
}

export { DEFAULT_URL };

/** Kho cấu hình dùng chung với runner nền: Preferences ghi vào SharedPreferences tên RUNNER_LABEL,
 * đúng nơi CapacitorKV của runner đọc (xem config.ts). */
let configured: Promise<void> | null = null;
const ready = () => (configured ??= Preferences.configure({ group: RUNNER_LABEL }));

export const prefs = {
  async get(key: string): Promise<string | null> {
    await ready();
    return (await Preferences.get({ key })).value;
  },
  async set(key: string, value: string): Promise<void> {
    await ready();
    await Preferences.set({ key, value });
  },
};

/** Danh tính thiết bị với server (device.ts): device_id ổn định và sổ mốc chờ báo delivered, lưu trong kho chung. */
export const devicePort = (getUrl: () => string) => makeDevicePort(prefs, getUrl);

/** Cổng chia việc với runner nền (sync.ts). */
export const sharedRefs = {
  async bgRefs(): Promise<RefMap> {
    return parseRefMap(await prefs.get(KEY.bgRefs));
  },
  async saveAppRefs(refs: RefMap): Promise<void> {
    await prefs.set(KEY.appRefs, JSON.stringify(refs));
  },
};

/** Độ lệch múi giờ của máy (phút, đông UTC là dương) cho runner nền. */
export const saveDeviceOffset = () => prefs.set(KEY.tzOffsetMin, String(-new Date().getTimezoneOffset()));
