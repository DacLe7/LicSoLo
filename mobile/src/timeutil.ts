/** Giờ của server là giờ địa phương không kèm múi giờ ("2026-10-28T09:00:00"). Mọi phép tính ngày
 * đi qua các hàm này để không phụ thuộc múi giờ của điện thoại. */

const MIN = 60_000;
const DAY = 86_400_000;
export { MIN, DAY };

const p2 = (n: number) => String(n).padStart(2, "0");

/** "2026-10-28T09:00:00" -> các thành phần số. */
export function parts(naive: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(naive);
  if (!m) throw new Error("giờ không hợp lệ: " + naive);
  return { y: +m[1], mo: +m[2], d: +m[3], h: +(m[4] ?? 0), mi: +(m[5] ?? 0), s: +(m[6] ?? 0) };
}

/** Mili giây của một giờ "địa phương" nếu coi nó là UTC (chỉ dùng để cộng trừ ngày). */
export function asUtcMs(naive: string): number {
  const t = parts(naive);
  return Date.UTC(t.y, t.mo - 1, t.d, t.h, t.mi, t.s);
}

export function fromUtcMs(ms: number): string {
  const d = new Date(ms);
  return `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}T${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}`;
}

/** 00:00 của ngày chứa `naive`, cộng `days` ngày: dạng truyền cho GET /events?from=&to=. */
export function dayStart(naive: string, days = 0): string {
  const t = parts(naive);
  return fromUtcMs(Date.UTC(t.y, t.mo - 1, t.d) + days * DAY);
}

/** Độ lệch múi giờ ("+07:00" hoặc "Z") ở cuối một chuỗi ISO. */
export function offsetOf(iso: string): string {
  const m = /([+-]\d{2}:\d{2}|Z)$/.exec(iso);
  if (!m) throw new Error("thiếu độ lệch múi giờ: " + iso);
  return m[1];
}

/** yyyymmddHHMM của một giờ địa phương (dùng làm hậu tố ref, giống UID trong .ics của server). */
export function stamp(naive: string): string {
  const t = parts(naive);
  return `${t.y}${p2(t.mo)}${p2(t.d)}${p2(t.h)}${p2(t.mi)}`;
}
