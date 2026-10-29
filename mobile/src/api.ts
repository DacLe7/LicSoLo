import { CapacitorHttp } from "@capacitor/core";
import type { NewEvent, Occurrence, ParseResult, ServerInfo, SyncApi, UpcomingReminder } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Gọi các endpoint /v1 của LicSoLo bản 0.5.2 (không cần khóa). Dùng CapacitorHttp nên không vướng CORS. */
export class Api implements SyncApi {
  constructor(private baseUrl: () => string) {}

  private async call<T>(method: string, path: string, opts: { data?: unknown; headers?: Record<string, string>; file?: boolean } = {}): Promise<T> {
    const url = this.baseUrl().trim().replace(/\/+$/, "") + "/v1" + path;
    const headers: Record<string, string> = { Accept: "application/json", ...(opts.headers ?? {}) };
    if (opts.data !== undefined && !opts.file) headers["Content-Type"] = "application/json";
    let r;
    try {
      r = await CapacitorHttp.request({
        url, method, headers, data: opts.data, dataType: opts.file ? "file" : undefined,
        responseType: "json", connectTimeout: 10_000, readTimeout: 60_000,
      });
    } catch (e) {
      throw new ApiError(0, e instanceof Error ? e.message : String(e));
    }
    let body: unknown = r.data;
    if (typeof body === "string") {
      try { body = JSON.parse(body); } catch { /* giữ nguyên chuỗi */ }
    }
    if (r.status >= 400) {
      const err = (body as { error?: string } | null)?.error;
      throw new ApiError(r.status, err || `Lỗi ${r.status}`);
    }
    return body as T;
  }

  info() { return this.call<ServerInfo>("GET", "/info"); }

  events(from: string, to: string) {
    return this.call<Occurrence[]>("GET", `/events?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  }

  parse(text: string, save = false) {
    return this.call<ParseResult>("POST", "/parse", { data: { text, save } });
  }

  create(ev: NewEvent) {
    return this.call<{ id: number; start: string; all_day: boolean; duplicate?: boolean }>("POST", "/events", { data: ev });
  }

  /** Sửa một phần việc đã lưu (PATCH /v1/events/<id>); server cũ chưa có thì trả 404/501. */
  update(id: number, patch: Partial<NewEvent> & { notes?: string | null }) {
    return this.call<{ id: number; title: string; start: string; all_day: boolean }>("PATCH", `/events/${id}`, { data: patch });
  }

  remove(id: number) { return this.call<unknown>("DELETE", `/events/${id}`); }

  /** Mốc nhắc sắp tới cho thiết bị này; bỏ các mốc đã "Đã biết"/fired và đã delivered trên thiết bị. */
  upcoming(days: number, deviceId: string) {
    return this.call<UpcomingReminder[]>(
      "GET", `/reminders/upcoming?days=${days}&device_id=${encodeURIComponent(deviceId)}&skip_acked=1`);
  }

  /** Đăng ký thiết bị (đăng ký lại = cập nhật, nên gọi nhiều lần vẫn được). */
  registerDevice(deviceId: string, platform: string, label?: string) {
    return this.call<unknown>("POST", "/devices", { data: { device_id: deviceId, platform, ...(label ? { label } : {}) } });
  }

  delivered(deviceId: string, eventId: number, key: string) {
    return this.call<unknown>("POST", "/reminders/delivered", { data: { device_id: deviceId, event_id: eventId, key } });
  }

  /** wavBase64: WAV 16 kHz mono 16 bit đã mã hóa base64 (CapacitorHttp gửi dataType "file" dưới dạng byte thô). */
  async stt(wavBase64: string) {
    return this.call<{ text: string }>("POST", "/stt", { data: wavBase64, file: true, headers: { "Content-Type": "audio/wav" } });
  }

  sttStatus() { return this.call<{ enabled: boolean; ready: boolean }>("GET", "/stt/status"); }

  learn(heard: string, fixed: string) { return this.call<unknown>("POST", "/stt/learn", { data: { heard, fixed } }); }
}
