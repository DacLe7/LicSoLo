import { beforeEach, describe, expect, it, vi } from "vitest";
import { createSync } from "../src/sync";
import {
  choosePoints, fetchOccurrences, mergePending, parsePending, pendingOf, pointsFromUpcoming, reminderPointsFor,
  reportDeliveries, PENDING_KEEP_DAYS,
} from "../src/reminders";
import { DEVICE_ID_RE, makeDevicePort, newDeviceId } from "../src/device";
import type { KV } from "../src/device";
import { KEY } from "../src/config";
import { DAY } from "../src/timeutil";
import type {
  CalendarDiff, CalendarPort, ManagedEntry, NotifierPort, Occurrence, PendingDelivery, ReminderPoint,
  SyncApi, UpcomingReminder,
} from "../src/types";

const TZ = "Asia/Ho_Chi_Minh";
const OFF = "+07:00";
const NOW_LOCAL = "2026-10-28T10:00:00";
const NOW_MS = Date.parse(NOW_LOCAL + OFF);
const HOUR = 3_600_000;

function occ(p: Partial<Occurrence> & { id: number; occurrence: string }): Occurrence {
  return {
    title: "Việc " + p.id, occurrence_iso: p.occurrence + OFF, all_day: false, duration_min: null, repeat: null,
    remind_before_min: null, notes: null, ...p,
  };
}

function up(o: Partial<UpcomingReminder> & { event_id: number; occurrence: string }): UpcomingReminder {
  const fire = o.fire_at ?? o.occurrence;
  const suffix = o.kind === "prepare_7d" ? "#7d" : o.kind === "prepare_1d" ? "#1d" : "";
  const stamp = o.occurrence.replace(/[-:T]/g, "").slice(0, 12);
  return {
    title: "Việc " + o.event_id, key: o.occurrence + suffix, kind: "on_time", all_day: false, notes: null,
    fire_at: fire, fire_at_iso: fire + OFF, ref: `lv-${o.event_id}-${stamp}${suffix.replace("#", "-")}`, ...o,
  };
}

/* ---------- 2) yearly: cửa sổ lấy xa ---------- */
describe("việc lặp hằng năm dương lịch (yearly)", () => {
  it("lấy tới +400 ngày như giỗ; việc lặp khác thì không", async () => {
    const list = [
      occ({ id: 1, title: "Sinh nhật mẹ", occurrence: "2027-06-01T00:00:00", all_day: true, repeat: "yearly" }),
      occ({ id: 2, title: "Họp tháng", occurrence: "2027-06-01T09:00:00", repeat: "monthly" }),
    ];
    const api: SyncApi = {
      async info() { return { tz: TZ, now: NOW_LOCAL }; },
      async events(from, to) { return list.filter((o) => o.occurrence >= from && o.occurrence < to); },
    };
    const got = await fetchOccurrences(api, { tz: TZ, now: NOW_LOCAL });
    expect(got.map((o) => o.title)).toEqual(["Sinh nhật mẹ"]);
  });

  it("mốc nhắc: chỉ on_time, không có mốc trước", () => {
    const o = occ({ id: 1, occurrence: "2026-11-05T00:00:00", all_day: true, repeat: "yearly" });
    expect(reminderPointsFor(o).map((p) => p.ref)).toEqual(["lv-1-202611050000"]);
  });
});

/* ---------- 5) mốc từ /upcoming ---------- */
describe("pointsFromUpcoming", () => {
  it("đổi mốc server sang mốc hẹn: tiêu đề theo loại, body có giờ và ghi chú", () => {
    const items = [
      up({ event_id: 9, occurrence: "2026-11-10T00:00:00", all_day: true, kind: "prepare_7d", fire_at: "2026-11-03T08:00:00", title: "Giỗ ông" }),
      up({ event_id: 9, occurrence: "2026-11-10T00:00:00", all_day: true, kind: "prepare_1d", fire_at: "2026-11-09T08:00:00", title: "Giỗ ông" }),
      up({ event_id: 3, occurrence: "2026-10-29T09:00:00", title: "Họp", notes: "phòng 3" }),
    ];
    const p = pointsFromUpcoming(items, NOW_MS);
    expect(p.map((x) => x.ref)).toEqual(["lv-3-202610290900", "lv-9-202611100000-7d", "lv-9-202611100000-1d"]);
    expect(p.map((x) => x.title)).toEqual(["Họp", "Còn 7 ngày: Giỗ ông", "Ngày mai: Giỗ ông"]);
    expect(p[0].body).toBe("09:00 29/10 · phòng 3");
    expect(p[1].body).toBe("10/11 cả ngày");
    expect(p[1]).toMatchObject({ eventId: 9, key: "2026-11-10T00:00:00#7d", atMs: Date.parse("2026-11-03T08:00:00" + OFF) });
  });

  it("bỏ mốc đã qua, mốc xa hơn 30 ngày, trùng ref và mốc hỏng", () => {
    const items = [
      up({ event_id: 1, occurrence: "2026-10-28T10:00:00" }), // đúng bây giờ: bỏ
      up({ event_id: 2, occurrence: "2026-10-27T09:00:00" }), // đã qua
      up({ event_id: 3, occurrence: "2026-11-27T10:00:00" }), // đúng 30 ngày: giữ
      up({ event_id: 4, occurrence: "2026-11-27T10:01:00" }), // quá 30 ngày
      up({ event_id: 5, occurrence: "2026-10-30T09:00:00" }),
      up({ event_id: 5, occurrence: "2026-10-30T09:00:00" }), // trùng ref
      { ...up({ event_id: 6, occurrence: "2026-10-30T09:00:00" }), fire_at_iso: "hỏng" },
    ];
    expect(pointsFromUpcoming(items, NOW_MS).map((x) => x.eventId)).toEqual([5, 3]);
  });
});

/* ---------- 5) chọn nguồn mốc ---------- */
describe("choosePoints", () => {
  const occs = [occ({ id: 1, occurrence: "2026-10-29T09:00:00" })];
  const load = vi.fn(async () => occs);
  beforeEach(() => load.mockClear());

  it("server tốt: dùng mốc server, không tự tính", async () => {
    const upcoming = vi.fn(async (_d: number, _id: string) => [up({ event_id: 7, occurrence: "2026-10-30T08:00:00" })]);
    const r = await choosePoints({ upcoming }, "dev1", load, NOW_MS);
    expect(r.source).toBe("server");
    expect(r.points.map((p) => p.ref)).toEqual(["lv-7-202610300800"]);
    expect(upcoming).toHaveBeenCalledWith(30, "dev1");
    expect(load).not.toHaveBeenCalled();
  });

  it("endpoint lỗi: dự phòng tự tính từ việc", async () => {
    const upcoming = vi.fn(async (_d: number, _id: string): Promise<UpcomingReminder[]> => {
      throw Object.assign(new Error("Lỗi 500"), { status: 500 });
    });
    const r = await choosePoints({ upcoming }, "dev1", load, NOW_MS);
    expect(r.source).toBe("local");
    expect(r.points.map((p) => p.ref)).toEqual(["lv-1-202610290900"]);
  });

  it("server cũ (không có upcoming) hoặc chưa có device_id: tự tính, không gọi server", async () => {
    expect((await choosePoints({}, "dev1", load, NOW_MS)).source).toBe("local");
    const upcoming = vi.fn(async (_d: number, _id: string): Promise<UpcomingReminder[]> => []);
    expect((await choosePoints({ upcoming }, null, load, NOW_MS)).source).toBe("local");
    expect(upcoming).not.toHaveBeenCalled();
  });

  it("server báo chưa đăng ký: đăng ký lại rồi thử lại một lần", async () => {
    const upcoming = vi.fn(async (_d: number, id: string) => {
      if (id === "old") throw Object.assign(new Error("thiết bị chưa đăng ký (POST /v1/devices)"), { status: 400 });
      return [up({ event_id: 7, occurrence: "2026-10-30T08:00:00" })];
    });
    const r = await choosePoints({ upcoming }, "old", load, NOW_MS, async () => "new");
    expect(r.source).toBe("server");
    expect(upcoming.mock.calls.map((c) => c[1])).toEqual(["old", "new"]);
    // đăng ký lại không được: dự phòng
    const r2 = await choosePoints({ upcoming }, "old", load, NOW_MS, async () => null);
    expect(r2.source).toBe("local");
  });
});

/* ---------- 5) báo delivered ---------- */
describe("reportDeliveries", () => {
  const pd = (eventId: number, atMs: number, key = "k" + eventId): PendingDelivery => ({ eventId, key, atMs });

  it("báo mốc đã tới giờ, giữ mốc chưa tới", async () => {
    const delivered = vi.fn(async (_d: string, _e: number, _k: string) => undefined);
    const r = await reportDeliveries({ delivered }, "d", [pd(1, NOW_MS - 1000), pd(2, NOW_MS), pd(3, NOW_MS + 1000)], NOW_MS);
    expect(delivered.mock.calls).toEqual([["d", 1, "k1"], ["d", 2, "k2"]]);
    expect(r).toMatchObject({ reported: 2, failed: [], waiting: [pd(3, NOW_MS + 1000)] });
  });

  it("server lỗi: dừng, giữ phần còn lại để thử lần sau", async () => {
    const delivered = vi.fn(async (_d: string, id: number, _k: string) => { if (id === 2) throw new Error("Network error"); });
    const r = await reportDeliveries({ delivered }, "d", [pd(1, NOW_MS - 3000), pd(2, NOW_MS - 2000), pd(3, NOW_MS - 1000)], NOW_MS);
    expect(r.reported).toBe(1);
    expect(r.failed.map((p) => p.eventId)).toEqual([2, 3]);
    expect(delivered).toHaveBeenCalledTimes(2);
  });

  it(`bỏ mốc quá ${PENDING_KEEP_DAYS} ngày`, async () => {
    const delivered = vi.fn(async (_d: string, _e: number, _k: string) => undefined);
    const r = await reportDeliveries({ delivered }, "d", [pd(1, NOW_MS - (PENDING_KEEP_DAYS + 1) * DAY)], NOW_MS);
    expect(delivered).not.toHaveBeenCalled();
    expect(r).toMatchObject({ reported: 0, failed: [], waiting: [] });
  });

  it("không có device_id hoặc server cũ: không báo, không giữ", async () => {
    const delivered = vi.fn(async (_d: string, _e: number, _k: string) => undefined);
    expect((await reportDeliveries({ delivered }, null, [pd(1, NOW_MS - 1)], NOW_MS)).failed).toEqual([]);
    expect((await reportDeliveries({}, "d", [pd(1, NOW_MS - 1)], NOW_MS)).failed).toEqual([]);
    expect(delivered).not.toHaveBeenCalled();
  });

  it("pendingOf, mergePending, parsePending", () => {
    const pts: ReminderPoint[] = [
      { ref: "a", atMs: 1, title: "", body: "", eventId: 1, key: "k" }, { ref: "b", atMs: 2, title: "", body: "" },
    ];
    expect(pendingOf(pts)).toEqual([{ eventId: 1, key: "k", atMs: 1 }]);
    expect(mergePending([pd(1, 1, "k")], [pd(1, 5, "k"), pd(2, 6)])).toEqual([pd(1, 5, "k"), pd(2, 6)]);
    expect(parsePending(null)).toEqual([]);
    expect(parsePending("hỏng")).toEqual([]);
    expect(parsePending('[{"eventId":1,"key":"k","atMs":5},{"x":1},7]')).toEqual([{ eventId: 1, key: "k", atMs: 5 }]);
  });

  it("tự tính (dự phòng) cũng có eventId và key đúng dạng server", () => {
    const g = occ({ id: 9, occurrence: "2026-11-10T00:00:00", all_day: true, repeat: "lunar_yearly" });
    expect(reminderPointsFor(g).map((p) => [p.eventId, p.key])).toEqual([
      [9, "2026-11-10T00:00:00#7d"], [9, "2026-11-10T00:00:00#1d"], [9, "2026-11-10T00:00:00"],
    ]);
  });
});

/* ---------- device.ts ---------- */
describe("makeDevicePort", () => {
  const mkKv = (): KV & { m: Map<string, string> } => {
    const m = new Map<string, string>();
    return { m, async get(k) { return m.get(k) ?? null; }, async set(k, v) { m.set(k, v); } };
  };

  it("device_id: tạo một lần, hợp lệ với server, ổn định", async () => {
    const kv = mkKv();
    const a = await makeDevicePort(kv, () => "http://x").deviceId();
    expect(a).toMatch(DEVICE_ID_RE);
    expect(await makeDevicePort(kv, () => "http://x").deviceId()).toBe(a);
    expect(kv.m.get(KEY.deviceId)).toBe(a);
    expect(newDeviceId()).not.toBe(newDeviceId());
  });

  it("id lưu hỏng thì tạo lại", async () => {
    const kv = mkKv();
    kv.m.set(KEY.deviceId, "có dấu cách!");
    expect(await makeDevicePort(kv, () => "u").deviceId()).toMatch(DEVICE_ID_RE);
  });

  it("đăng ký gắn với URL server: đổi server thì đăng ký lại", async () => {
    const kv = mkKv();
    let url = "http://a.example/";
    const d = makeDevicePort(kv, () => url);
    expect(await d.isRegistered()).toBe(false);
    await d.setRegistered(true);
    expect(await d.isRegistered()).toBe(true);
    url = "http://a.example"; // khác dấu / cuối thì vẫn là cùng server
    expect(await d.isRegistered()).toBe(true);
    url = "http://b.example";
    expect(await d.isRegistered()).toBe(false);
    await d.setRegistered(false);
    expect(kv.m.get(KEY.deviceRegistered)).toBe("");
  });

  it("sổ chờ báo: app và runner nền dùng hai khóa riêng", async () => {
    const kv = mkKv();
    const app = makeDevicePort(kv, () => "u");
    const bg = makeDevicePort(kv, () => "u", KEY.bgPending);
    await app.savePending([{ eventId: 1, key: "k", atMs: 5 }]);
    expect(await bg.loadPending()).toEqual([]);
    expect(await app.loadPending()).toEqual([{ eventId: 1, key: "k", atMs: 5 }]);
  });
});

/* ---------- createSync có device ---------- */
class FakeCalendar implements CalendarPort {
  async ensureCalendar() {}
  async listManaged(): Promise<ManagedEntry[]> { return []; }
  async applyDiff(_d: CalendarDiff) {}
}
class FakeNotifier implements NotifierPort {
  pending: { ref: string; title: string }[] = [];
  async cancelAll() { this.pending = []; }
  async schedule(p: { ref: string; title: string }[]) { this.pending.push(...p); }
}

describe("createSync + thiết bị", () => {
  const setup = (over: Partial<SyncApi> = {}, list: Occurrence[] = [occ({ id: 1, occurrence: "2026-10-28T12:00:00" })]) => {
    const state = { now: NOW_MS, upcoming: [up({ event_id: 1, occurrence: "2026-10-28T12:00:00" })] as UpcomingReminder[] };
    const calls = { register: [] as unknown[][], upcoming: [] as unknown[][], delivered: [] as unknown[][] };
    const api: SyncApi = {
      async info() { return { tz: TZ, now: NOW_LOCAL }; },
      async events(from, to) { return list.filter((o) => o.occurrence >= from && o.occurrence < to); },
      async upcoming(d, id) { calls.upcoming.push([d, id]); return state.upcoming; },
      async registerDevice(id, platform) { calls.register.push([id, platform]); return {}; },
      async delivered(id, ev, key) { calls.delivered.push([id, ev, key]); return {}; },
      ...over,
    };
    const store = new Map<string, string>();
    const kv: KV = { async get(k) { return store.get(k) ?? null; }, async set(k, v) { store.set(k, v); } };
    const notifier = new FakeNotifier();
    const run = createSync({
      api, calendar: new FakeCalendar(), notifier, now: () => state.now, device: makeDevicePort(kv, () => "http://srv"),
    });
    return { state, calls, run, notifier, store };
  };

  it("đăng ký thiết bị một lần (android), lấy mốc từ /upcoming?days=30 với device_id", async () => {
    const t = setup();
    const r = await t.run();
    expect(r).toMatchObject({ ok: true, reminderSource: "server", scheduled: 1 });
    expect(t.calls.register).toHaveLength(1);
    expect(t.calls.register[0][1]).toBe("android");
    expect(t.calls.upcoming).toEqual([[30, t.calls.register[0][0]]]);
    await t.run();
    expect(t.calls.register).toHaveLength(1); // đã đăng ký: không gọi lại
    expect(t.calls.upcoming).toHaveLength(2);
  });

  it("mốc lấy từ server quyết định việc hẹn (mốc server đã bỏ thì app không tự thêm)", async () => {
    const t = setup();
    t.state.upcoming = []; // server nói không còn mốc nào (đã biết/đã hiện)
    const r = await t.run();
    expect(r.scheduled).toBe(0);
    expect(t.notifier.pending).toEqual([]);
  });

  it("upcoming lỗi: dùng quy tắc tự tính trong reminders.ts", async () => {
    const t = setup({ async upcoming() { throw new Error("Lỗi 500"); } });
    const r = await t.run();
    expect(r).toMatchObject({ ok: true, reminderSource: "local", scheduled: 1 });
    expect(t.notifier.pending.map((p) => p.ref)).toEqual(["lv-1-202610281200"]);
  });

  it("server cũ (đăng ký 404): tự tính, không gọi /upcoming, không gọi đăng ký lại trong 10 phút", async () => {
    let attempts = 0;
    const t = setup({ async registerDevice() { attempts++; throw Object.assign(new Error("không có đường dẫn này"), { status: 404 }); } });
    let r = await t.run();
    expect(r).toMatchObject({ ok: true, reminderSource: "local", scheduled: 1 });
    expect(t.calls.upcoming).toHaveLength(0);
    r = await t.run();
    expect(r.reminderSource).toBe("local");
    expect(attempts).toBe(1);
    t.state.now += 11 * 60_000;
    await t.run();
    expect(attempts).toBe(2);
  });

  it("không có API thiết bị (SyncApi tối thiểu, không DevicePort): vẫn chạy như bản cũ", async () => {
    const list = [occ({ id: 1, occurrence: "2026-10-28T12:00:00" })];
    const minimal: SyncApi = {
      async info() { return { tz: TZ, now: NOW_LOCAL }; },
      async events(from, to) { return list.filter((o) => o.occurrence >= from && o.occurrence < to); },
    };
    const run = createSync({ api: minimal, calendar: new FakeCalendar(), notifier: new FakeNotifier(), now: () => NOW_MS });
    expect(await run()).toMatchObject({ ok: true, reminderSource: "local", scheduled: 1 });
  });

  it("server báo chưa đăng ký (mất dữ liệu): đăng ký lại và thử lại", async () => {
    let known = false;
    const t = setup({
      async upcoming() {
        if (!known) throw Object.assign(new Error("thiết bị chưa đăng ký (POST /v1/devices)"), { status: 400 });
        return [up({ event_id: 1, occurrence: "2026-10-28T12:00:00" })];
      },
      async registerDevice() { known = true; return {}; },
    });
    t.store.set(KEY.deviceId, "android-abc");
    t.store.set(KEY.deviceRegistered, "http://srv"); // app tưởng đã đăng ký
    const r = await t.run();
    expect(r.reminderSource).toBe("server");
    expect(known).toBe(true);
  });

  it("sau khi mốc qua giờ: lần đồng bộ sau báo delivered đúng event_id và key", async () => {
    const t = setup();
    await t.run(); // hẹn mốc 12:00
    expect(t.calls.delivered).toEqual([]);
    t.state.now = NOW_MS + 3 * HOUR; // 13:00, mốc 12:00 đã qua
    t.state.upcoming = [];
    const r = await t.run();
    expect(r.delivered).toBe(1);
    const id = t.calls.register[0][0];
    expect(t.calls.delivered).toEqual([[id, 1, "2026-10-28T12:00:00"]]);
    await t.run();
    expect(t.calls.delivered).toHaveLength(1); // đã báo thì không báo lại
  });

  it("báo delivered lỗi: giữ lại và thử lần sau; lỗi không làm hỏng đồng bộ", async () => {
    let fail = true;
    const sent: unknown[][] = [];
    const t = setup({
      async delivered(id, ev, key) {
        if (fail) throw new Error("Network error");
        sent.push([id, ev, key]);
        return {};
      },
    });
    await t.run();
    t.state.now = NOW_MS + 3 * HOUR;
    t.state.upcoming = [];
    const r1 = await t.run();
    expect(r1).toMatchObject({ ok: true, delivered: 0 });
    fail = false;
    const r2 = await t.run();
    expect(r2.delivered).toBe(1);
    expect(sent).toHaveLength(1);
  });

  it("mốc không còn trong lần hẹn mới (việc bị sửa/xóa trước giờ) thì không báo delivered", async () => {
    const t = setup();
    await t.run(); // hẹn mốc 12:00
    t.state.now = NOW_MS + HOUR; // 11:00: server không còn mốc nào (việc bị xóa)
    t.state.upcoming = [];
    await t.run();
    t.state.now = NOW_MS + 3 * HOUR;
    const r = await t.run();
    expect(r.delivered).toBe(0);
    expect(t.calls.delivered).toEqual([]);
  });
});

/* ---------- api.ts ---------- */
const request = vi.fn();
vi.mock("@capacitor/core", () => ({ CapacitorHttp: { request: (o: unknown) => request(o) } }));

describe("Api (đường dẫn và nội dung gọi server)", () => {
  beforeEach(() => request.mockReset());
  const make = async () => {
    const { Api } = await import("../src/api");
    return new Api(() => "http://srv/");
  };

  it("update: PATCH /v1/events/<id> với tập con trường", async () => {
    request.mockResolvedValue({ status: 200, data: { id: 5, title: "Mới" } });
    const api = await make();
    expect(await api.update(5, { title: "Mới", start: "2026-11-01T09:00:00" })).toMatchObject({ id: 5 });
    expect(request.mock.calls[0][0]).toMatchObject({
      method: "PATCH", url: "http://srv/v1/events/5", data: { title: "Mới", start: "2026-11-01T09:00:00" },
    });
  });

  it("update: id không tồn tại (404) và dữ liệu sai (400) thành ApiError có thông báo", async () => {
    const api = await make();
    request.mockResolvedValue({ status: 404, data: { error: "không tìm thấy" } });
    await expect(api.update(9, { title: "x" })).rejects.toMatchObject({ status: 404, message: "không tìm thấy" });
    request.mockResolvedValue({ status: 400, data: { error: "trường không hợp lệ: id" } });
    await expect(api.update(9, {})).rejects.toMatchObject({ status: 400 });
  });

  it("upcoming: days=30, device_id và skip_acked=1", async () => {
    request.mockResolvedValue({ status: 200, data: [] });
    const api = await make();
    await api.upcoming(30, "android-1");
    expect(request.mock.calls[0][0]).toMatchObject({
      method: "GET", url: "http://srv/v1/reminders/upcoming?days=30&device_id=android-1&skip_acked=1",
    });
  });

  it("registerDevice và delivered", async () => {
    request.mockResolvedValue({ status: 200, data: {} });
    const api = await make();
    await api.registerDevice("android-1", "android");
    await api.delivered("android-1", 7, "2026-10-28T12:00:00#7d");
    expect(request.mock.calls[0][0]).toMatchObject({
      method: "POST", url: "http://srv/v1/devices", data: { device_id: "android-1", platform: "android" },
    });
    expect(request.mock.calls[1][0]).toMatchObject({
      method: "POST", url: "http://srv/v1/reminders/delivered",
      data: { device_id: "android-1", event_id: 7, key: "2026-10-28T12:00:00#7d" },
    });
  });
});
