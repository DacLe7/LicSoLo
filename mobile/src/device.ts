import { KEY } from "./config";
import { parsePending } from "./reminders";
import type { DevicePort } from "./types";

/* Danh tính thiết bị với server: device_id ổn định (lưu trong kho chung) và sổ mốc chờ báo delivered.
 * Không import Capacitor: kho (prefs) được truyền vào nên kiểm thử được bằng kho giả. */

export interface KV {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

/** device_id hợp lệ với server: [A-Za-z0-9_-]{1,64}. */
export const DEVICE_ID_RE = /^[A-Za-z0-9_-]{1,64}$/;

export function newDeviceId(rand: () => number = Math.random): string {
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  const tail = c?.randomUUID ? c.randomUUID() : Array.from({ length: 24 }, () => Math.floor(rand() * 16).toString(16)).join("");
  return "android-" + tail;
}

const norm = (u: string) => u.trim().replace(/\/+$/, "");

/** `pendingKey`: app và runner nền mỗi bên giữ một sổ riêng (appPending / bgPending) nên không ghi đè nhau. */
export function makeDevicePort(kv: KV, getUrl: () => string, pendingKey: string = KEY.appPending): DevicePort {
  return {
    async deviceId() {
      const saved = await kv.get(KEY.deviceId);
      if (saved && DEVICE_ID_RE.test(saved)) return saved;
      const id = newDeviceId();
      await kv.set(KEY.deviceId, id);
      return id;
    },
    async isRegistered() {
      return (await kv.get(KEY.deviceRegistered)) === norm(getUrl()); // đổi server thì đăng ký lại
    },
    async setRegistered(v) {
      await kv.set(KEY.deviceRegistered, v ? norm(getUrl()) : "");
    },
    async loadPending() {
      return parsePending(await kv.get(pendingKey));
    },
    async savePending(p) {
      await kv.set(pendingKey, JSON.stringify(p));
    },
  };
}
