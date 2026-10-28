import { describe, expect, it } from "vitest";
import {
  createSync, diffCalendar, eventRef, hashText, notificationId, reminderPoints, toCalendarItem, withIds,
  MAX_NOTIFICATIONS,
} from "../src/sync";
import type {
  CalendarDiff, CalendarItem, CalendarPort, ManagedEntry, NotifierPort, Occurrence, ReminderPoint, SyncApi,
} from "../src/types";
import { DAY, MIN } from "../src/timeutil";

const TZ = "Asia/Ho_Chi_Minh";
const OFF = "+07:00";
const NOW_LOCAL = "2026-10-28T10:00:00";
const NOW_MS = Date.parse("2026-10-28T10:00:00" + OFF);

function occ(p: Partial<Occurrence> & { id: number; occurrence: string }): Occurrence {
  return {
    title: "Việc " + p.id, occurrence_iso: p.occurrence + OFF, all_day: false, duration_min: null, repeat: null,
    remind_before_min: null, notes: null, ...p,
  };
}

class FakeCalendar implements CalendarPort {
  store = new Map<number, CalendarItem>();
  nextId = 1;
  ensured = 0;
  applied: CalendarDiff[] = [];
  failEnsure = false;
  async ensureCalendar() { if (this.failEnsure) throw new Error("chưa cấp quyền lịch"); this.ensured++; }
  async listManaged(): Promise<ManagedEntry[]> {
    return [...this.store].map(([eventId, it]) => ({ ref: it.ref, eventId, hash: it.hash }));
  }
  async applyDiff(d: CalendarDiff) {
    this.applied.push(d);
    for (const id of d.delete) this.store.delete(id);
    for (const u of d.update) this.store.set(u.eventId, u);
    for (const i of d.insert) this.store.set(this.nextId++, i);
  }
}

class FakeNotifier implements NotifierPort {
  pending: (ReminderPoint & { id: number })[] = [];
  cancels = 0;
  async cancelAll() { this.cancels++; this.pending = []; }
  async schedule(p: (ReminderPoint & { id: number })[]) { this.pending.push(...p); }
}

function fakeApi(list: () => Occurrence[], fail = false): SyncApi & { calls: [string, string][] } {
  const calls: [string, string][] = [];
  return {
    calls,
    async info() { if (fail) throw new Error("Network error"); return { tz: TZ, now: NOW_LOCAL }; },
    async events(from, to) {
      calls.push([from, to]);
      if (fail) throw new Error("Network error");
      return list().filter((o) => o.occurrence >= from && o.occurrence < to);
    },
  };
}

describe("hash và id", () => {
  it("hashText ổn định và nhạy với nội dung", () => {
    expect(hashText("a")).toBe(hashText("a"));
    expect(hashText("a")).not.toBe(hashText("b"));
  });
  it("notificationId: ổn định, dương, vừa 31 bit", () => {
    const id = notificationId("lv-12-202610281500");
    expect(id).toBe(notificationId("lv-12-202610281500"));
    expect(id).toBeGreaterThan(0);
    expect(id).toBeLessThanOrEqual(0x7fffffff);
    expect(Number.isInteger(id)).toBe(true);
    expect(notificationId("lv-12-202610281500-7d")).not.toBe(id);
  });
  it("giá trị cố định (khóa hành vi băm để id không đổi giữa các bản app)", () => {
    expect(notificationId("lv-1-202601010900")).toBe(notificationId("lv-1-202601010900"));
    expect(notificationId("")).toBe(0x811c9dc5 & 0x7fffffff);
  });
  it("withIds: không có hai id trùng", () => {
    const pts = Array.from({ length: 500 }, (_, i) => ({ ref: "r" + i, atMs: i, title: "t", body: "" }));
    const ids = withIds(pts).map((p) => p.id);
    expect(new Set(ids).size).toBe(500);
  });
});

describe("toCalendarItem", () => {
  it("việc có giờ: mặc định 60 phút, tz của server", () => {
    const it = toCalendarItem(occ({ id: 1, occurrence: "2026-11-01T15:30:00" }), TZ);
    expect(it.ref).toBe("lv-1-202611011530");
    expect(it.startMs).toBe(Date.parse("2026-11-01T15:30:00+07:00"));
    expect(it.endMs - it.startMs).toBe(60 * MIN);
    expect(it.tz).toBe(TZ);
    expect(it.allDay).toBe(false);
  });
  it("dùng duration_min khi có", () => {
    const it = toCalendarItem(occ({ id: 1, occurrence: "2026-11-01T15:30:00", duration_min: 90 }), TZ);
    expect(it.endMs - it.startMs).toBe(90 * MIN);
  });
  it("việc cả ngày: 00:00 UTC, tz UTC, dài đúng một ngày", () => {
    const it = toCalendarItem(occ({ id: 2, occurrence: "2026-11-01T00:00:00", all_day: true }), TZ);
    expect(it.startMs).toBe(Date.UTC(2026, 10, 1));
    expect(it.endMs - it.startMs).toBe(DAY);
    expect(it.tz).toBe("UTC");
    expect(it.allDay).toBe(true);
  });
  it("hash đổi khi tên, giờ, cả ngày hoặc ghi chú đổi; không đổi khi mọi thứ giữ nguyên", () => {
    const base = occ({ id: 1, occurrence: "2026-11-01T15:30:00" });
    const h = (o: Occurrence) => toCalendarItem(o, TZ).hash;
    expect(h(base)).toBe(h({ ...base }));
    expect(h({ ...base, title: "khác" })).not.toBe(h(base));
    expect(h({ ...base, occurrence_iso: "2026-11-01T16:30:00" + OFF })).not.toBe(h(base));
    expect(h({ ...base, duration_min: 30 })).not.toBe(h(base));
    expect(h({ ...base, notes: "mới" })).not.toBe(h(base));
    expect(h({ ...base, remind_before_min: 10 })).toBe(h(base)); // nhắc trước không nằm trong lịch
  });
});

describe("diffCalendar", () => {
  const a = toCalendarItem(occ({ id: 1, occurrence: "2026-11-01T09:00:00" }), TZ);
  const b = toCalendarItem(occ({ id: 2, occurrence: "2026-11-02T09:00:00" }), TZ);
  it("thêm ref mới", () => {
    const d = diffCalendar([a, b], [{ ref: a.ref, eventId: 10, hash: a.hash }]);
    expect(d.insert.map((x) => x.ref)).toEqual([b.ref]);
    expect(d.update).toEqual([]);
    expect(d.delete).toEqual([]);
  });
  it("sửa khi hash khác, mang theo eventId", () => {
    const d = diffCalendar([a], [{ ref: a.ref, eventId: 10, hash: "cũ" }]);
    expect(d.update).toEqual([{ ...a, eventId: 10 }]);
    expect(d.insert).toEqual([]);
  });
  it("xóa ref không còn", () => {
    const d = diffCalendar([a], [{ ref: a.ref, eventId: 10, hash: a.hash }, { ref: b.ref, eventId: 11, hash: b.hash }]);
    expect(d.delete).toEqual([11]);
  });
  it("không đổi gì thì diff rỗng", () => {
    const d = diffCalendar([a, b], [{ ref: a.ref, eventId: 1, hash: a.hash }, { ref: b.ref, eventId: 2, hash: b.hash }]);
    expect(d).toEqual({ insert: [], update: [], delete: [] });
  });
  it("ref bị ghi trùng trong lịch thì xóa bản thừa", () => {
    const d = diffCalendar([a], [{ ref: a.ref, eventId: 1, hash: a.hash }, { ref: a.ref, eventId: 2, hash: a.hash }]);
    expect(d.delete).toEqual([2]);
  });
});

describe("mốc nhắc", () => {
  it("việc thường không có remind_before_min: nhắc đúng giờ", () => {
    const p = reminderPoints([occ({ id: 1, occurrence: "2026-10-28T15:00:00" })], NOW_MS);
    expect(p).toHaveLength(1);
    expect(p[0].atMs).toBe(Date.parse("2026-10-28T15:00:00+07:00"));
    expect(p[0].ref).toBe("lv-1-202610281500");
    expect(p[0].title).toBe("Việc 1");
  });
  it("việc thường: trừ remind_before_min", () => {
    const p = reminderPoints([occ({ id: 1, occurrence: "2026-10-28T15:00:00", remind_before_min: 30 })], NOW_MS);
    expect(p[0].atMs).toBe(Date.parse("2026-10-28T14:30:00+07:00"));
  });
  it("việc cả ngày: mốc gốc 08:00 của ngày đó", () => {
    const p = reminderPoints([occ({ id: 3, occurrence: "2026-10-30T00:00:00", all_day: true })], NOW_MS);
    expect(p[0].atMs).toBe(Date.parse("2026-10-30T08:00:00+07:00"));
  });
  it("việc cả ngày có remind_before_min: trừ từ 08:00", () => {
    const p = reminderPoints([occ({ id: 3, occurrence: "2026-10-30T00:00:00", all_day: true, remind_before_min: 60 })], NOW_MS);
    expect(p[0].atMs).toBe(Date.parse("2026-10-30T07:00:00+07:00"));
  });
  it("giỗ: ba mốc 7 ngày, 1 ngày và đúng giờ, kèm tiêu đề riêng", () => {
    const g = occ({ id: 9, title: "Giỗ ông", occurrence: "2026-11-10T00:00:00", all_day: true, repeat: "lunar_yearly", remind_before_min: 0 });
    const p = reminderPoints([g], NOW_MS);
    expect(p.map((x) => x.ref)).toEqual(["lv-9-202611100000-7d", "lv-9-202611100000-1d", "lv-9-202611100000"]);
    expect(p.map((x) => x.atMs)).toEqual([
      Date.parse("2026-11-03T08:00:00+07:00"), Date.parse("2026-11-09T08:00:00+07:00"), Date.parse("2026-11-10T08:00:00+07:00"),
    ]);
    expect(p.map((x) => x.title)).toEqual(["Còn 7 ngày: Giỗ ông", "Ngày mai: Giỗ ông", "Giỗ ông"]);
  });
  it("giỗ: mốc đúng giờ trừ remind_before_min", () => {
    const g = occ({ id: 9, occurrence: "2026-11-10T09:00:00", repeat: "lunar_yearly", remind_before_min: 45 });
    const p = reminderPoints([g], NOW_MS);
    expect(p[p.length - 1].atMs).toBe(Date.parse("2026-11-10T08:15:00+07:00"));
  });
  it("bỏ mốc đã qua giờ (kể cả đúng bằng bây giờ)", () => {
    const p = reminderPoints([
      occ({ id: 1, occurrence: "2026-10-28T09:59:00" }),
      occ({ id: 2, occurrence: "2026-10-28T10:00:00" }),
      occ({ id: 3, occurrence: "2026-10-28T10:01:00" }),
    ], NOW_MS);
    expect(p.map((x) => x.ref)).toEqual(["lv-3-202610281001"]);
  });
  it("giỗ sắp tới: mốc 7 ngày đã qua thì bỏ, mốc còn lại giữ", () => {
    const g = occ({ id: 9, occurrence: "2026-11-02T00:00:00", all_day: true, repeat: "lunar_yearly" });
    const p = reminderPoints([g], NOW_MS);
    expect(p.map((x) => x.ref)).toEqual(["lv-9-202611020000-1d", "lv-9-202611020000"]);
  });
  it("bỏ mốc xa hơn 30 ngày, giữ mốc đúng 30 ngày", () => {
    const edge = new Date(NOW_MS + 30 * DAY);
    const toLocal = (ms: number) => new Date(ms + 7 * 3600_000).toISOString().slice(0, 19);
    const p = reminderPoints([
      occ({ id: 1, occurrence: toLocal(edge.getTime()) }),
      occ({ id: 2, occurrence: toLocal(edge.getTime() + MIN) }),
    ], NOW_MS);
    expect(p.map((x) => x.ref.slice(3, 4))).toEqual(["1"]);
  });
  it("giỗ cách hơn 30 ngày: chỉ hẹn các mốc nằm trong 30 ngày (-7d và -1d), mốc chính thì không", () => {
    const g = occ({ id: 9, occurrence: "2026-11-28T09:00:00", repeat: "lunar_yearly" });
    expect(reminderPoints([g], NOW_MS).map((x) => x.ref)).toEqual(["lv-9-202611280900-7d", "lv-9-202611280900-1d"]);
  });
  it(`giới hạn ${MAX_NOTIFICATIONS} mốc gần nhất`, () => {
    const many = Array.from({ length: 260 }, (_, i) => {
      const t = new Date(NOW_MS + (i + 1) * 5 * MIN + 7 * 3600_000).toISOString().slice(0, 19);
      return occ({ id: i + 1, occurrence: t });
    });
    const p = reminderPoints(many, NOW_MS);
    expect(p).toHaveLength(MAX_NOTIFICATIONS);
    expect(p[0].ref.startsWith("lv-1-")).toBe(true);
    expect(p[p.length - 1].ref.startsWith(`lv-${MAX_NOTIFICATIONS}-`)).toBe(true);
    for (let i = 1; i < p.length; i++) expect(p[i].atMs).toBeGreaterThanOrEqual(p[i - 1].atMs);
  });
  it("body có giờ và ghi chú", () => {
    const p = reminderPoints([occ({ id: 1, occurrence: "2026-10-29T08:05:00", notes: "mang hồ sơ" })], NOW_MS);
    expect(p[0].body).toBe("08:05 29/10 · mang hồ sơ");
  });
  it("eventRef giống UID .ics: lv-<id>-<yyyymmddHHMM>", () => {
    expect(eventRef(occ({ id: 5, occurrence: "2027-01-02T03:04:00" }))).toBe("lv-5-202701020304");
  });
});

describe("createSync", () => {
  const mk = (list: Occurrence[], fail = false) => {
    const state = { list };
    const api = fakeApi(() => state.list, fail);
    const cal = new FakeCalendar();
    const notifier = new FakeNotifier();
    const run = createSync({ api, calendar: cal, notifier, now: () => NOW_MS });
    return { state, api, cal, notifier, run };
  };

  it("lần đầu: thêm vào lịch và hẹn thông báo", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" }), occ({ id: 2, occurrence: "2026-11-02T00:00:00", all_day: true })]);
    const r = await t.run();
    expect(r).toMatchObject({ ok: true, inserted: 2, updated: 0, deleted: 0, scheduled: 2 });
    expect(t.cal.store.size).toBe(2);
    expect(t.notifier.pending).toHaveLength(2);
  });

  it("đồng bộ lần hai khi không đổi gì: không ghi gì vào lịch", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" })]);
    await t.run();
    const r = await t.run();
    expect(r).toMatchObject({ inserted: 0, updated: 0, deleted: 0 });
    expect(t.cal.applied).toHaveLength(1);
  });

  it("sửa việc thì cập nhật; xóa việc thì xóa khỏi lịch và thông báo", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" }), occ({ id: 2, occurrence: "2026-10-30T09:00:00" })]);
    await t.run();
    t.state.list = [occ({ id: 1, occurrence: "2026-10-29T09:00:00", title: "Đổi tên" })];
    const r = await t.run();
    expect(r).toMatchObject({ inserted: 0, updated: 1, deleted: 1, scheduled: 1 });
    expect([...t.cal.store.values()].map((x) => x.title)).toEqual(["Đổi tên"]);
    expect(t.notifier.pending.map((p) => p.title)).toEqual(["Đổi tên"]);
  });

  it("mỗi lần đồng bộ hủy hết thông báo cũ rồi hẹn lại", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" })]);
    await t.run();
    await t.run();
    expect(t.notifier.cancels).toBe(2);
    expect(t.notifier.pending).toHaveLength(1);
  });

  it("lỗi mạng: không xóa, không hủy gì, báo lỗi", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" })]);
    await t.run();
    const calBefore = new Map(t.cal.store);
    const pendingBefore = [...t.notifier.pending];
    const bad = createSync({ api: fakeApi(() => [], true), calendar: t.cal, notifier: t.notifier, now: () => NOW_MS });
    const r = await bad();
    expect(r.ok).toBe(false);
    expect(r.error).toMatch(/Network/);
    expect(t.cal.store).toEqual(calBefore);
    expect(t.cal.applied).toHaveLength(1);
    expect(t.notifier.pending).toEqual(pendingBefore);
    expect(t.notifier.cancels).toBe(1);
  });

  it("hỏi khoảng -7 ngày .. +120 ngày, giỗ tới +400 ngày", async () => {
    const t = mk([]);
    await t.run();
    expect(t.api.calls).toEqual([
      ["2026-10-21T00:00:00", "2027-02-26T00:00:00"],
      ["2026-10-21T00:00:00", "2027-12-03T00:00:00"],
    ]);
  });

  it("giỗ xa hơn 120 ngày vẫn vào lịch, việc thường xa thì không", async () => {
    const t = mk([
      occ({ id: 1, occurrence: "2027-06-01T09:00:00" }),
      occ({ id: 2, title: "Giỗ", occurrence: "2027-06-01T00:00:00", all_day: true, repeat: "lunar_yearly" }),
    ]);
    const r = await t.run();
    expect(r.inserted).toBe(1);
    expect([...t.cal.store.values()][0].title).toBe("Giỗ");
    expect(r.scheduled).toBe(0); // xa hơn 30 ngày
  });

  it("không chạy hai lần chồng nhau", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" })]);
    const [a, b] = [t.run(), t.run()];
    expect(a).toBe(b);
    await a;
    expect(t.api.calls).toHaveLength(2); // một lần đồng bộ = hai lần gọi events
    await t.run();
    expect(t.api.calls).toHaveLength(4);
  });

  it("lịch lỗi (chưa cấp quyền) thì thông báo vẫn được hẹn và lỗi được báo", async () => {
    const t = mk([occ({ id: 1, occurrence: "2026-10-29T09:00:00" })]);
    t.cal.failEnsure = true;
    const r = await t.run();
    expect(r.ok).toBe(false);
    expect(r.calendarError).toMatch(/quyền lịch/);
    expect(r.scheduled).toBe(1);
  });
});
