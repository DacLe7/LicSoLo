import { describe, expect, it } from "vitest";
import {
  createSync, parseRefMap, planBackground, pruneRefs, refMapOf, reminderPoints, runnerScheduleAt, withoutTaken,
} from "../src/sync";
import type { RefMap } from "../src/sync";
import type { CalendarPort, NotifierPort, Occurrence, ReminderPoint, SyncApi } from "../src/types";
import { MIN } from "../src/timeutil";

const OFF = "+07:00";
const NOW_MS = Date.parse("2026-10-28T10:00:00" + OFF);
const occ = (id: number, occurrence: string, extra: Partial<Occurrence> = {}): Occurrence => ({
  id, title: "Việc " + id, occurrence, occurrence_iso: occurrence + OFF, all_day: false, duration_min: null,
  repeat: null, remind_before_min: null, notes: null, ...extra,
});
const pt = (ref: string, atMs: number): ReminderPoint => ({ ref, atMs, title: ref, body: "" });

describe("runnerScheduleAt", () => {
  it("cộng độ lệch múi giờ của máy để runner (đọc chuỗi theo giờ máy) ra đúng thời điểm", () => {
    const at = Date.parse("2026-10-28T15:00:00+07:00");
    expect(runnerScheduleAt(at, 420)).toBe("2026-10-28T15:00:00.000Z");
    expect(runnerScheduleAt(at, 0)).toBe("2026-10-28T08:00:00.000Z");
    expect(runnerScheduleAt(at, -300)).toBe("2026-10-28T03:00:00.000Z");
  });
  it("đọc ngược như Java SimpleDateFormat theo giờ máy UTC+7 thì ra đúng thời điểm", () => {
    const at = Date.parse("2026-10-28T15:00:00+07:00");
    const s = runnerScheduleAt(at, 420); // Java bỏ chữ Z, đọc "2026-10-28T15:00:00.000" theo UTC+7
    const javaReads = Date.parse(s.replace("Z", "") + "+07:00");
    expect(javaReads).toBe(at);
  });
});

describe("chia việc giữa app và runner", () => {
  it("withoutTaken chỉ bỏ mốc trùng cả ref lẫn giờ hẹn", () => {
    const pts = [pt("a", 100), pt("b", 200), pt("c", 300)];
    expect(withoutTaken(pts, { a: 100, b: 999 }).map((p) => p.ref)).toEqual(["b", "c"]);
  });
  it("pruneRefs bỏ mốc đã qua giờ", () => {
    expect(pruneRefs({ a: 50, b: 150 }, 100)).toEqual({ b: 150 });
  });
  it("parseRefMap chịu được dữ liệu hỏng", () => {
    expect(parseRefMap(null)).toEqual({});
    expect(parseRefMap("không phải json")).toEqual({});
    expect(parseRefMap("[1,2]")).toEqual({});
    expect(parseRefMap('{"a":5}')).toEqual({ a: 5 });
  });
  it("runner chỉ hẹn mốc mà app và chính nó chưa hẹn", () => {
    const pts = [pt("a", NOW_MS + 10), pt("b", NOW_MS + 20), pt("c", NOW_MS + 30)];
    const plan = planBackground(pts, { a: NOW_MS + 10 }, { b: NOW_MS + 20 }, NOW_MS);
    expect(plan.toSchedule.map((p) => p.ref)).toEqual(["c"]);
    expect(plan.bgRefs).toEqual({ b: NOW_MS + 20, c: NOW_MS + 30 });
  });
  it("runner chạy hai lần liên tiếp: lần hai không hẹn lại", () => {
    const pts = [pt("a", NOW_MS + 10), pt("b", NOW_MS + 20)];
    const first = planBackground(pts, {}, {}, NOW_MS);
    const second = planBackground(pts, {}, first.bgRefs, NOW_MS + 1);
    expect(first.toSchedule).toHaveLength(2);
    expect(second.toSchedule).toHaveLength(0);
  });
  it("bản ghi của runner tự bỏ các mốc đã qua giờ", () => {
    const plan = planBackground([], {}, { old: NOW_MS - 1, fresh: NOW_MS + 1 }, NOW_MS);
    expect(plan.bgRefs).toEqual({ fresh: NOW_MS + 1 });
  });
  it("giờ hẹn đổi thì coi là mốc mới", () => {
    const plan = planBackground([pt("a", NOW_MS + 99)], { a: NOW_MS + 10 }, {}, NOW_MS);
    expect(plan.toSchedule.map((p) => p.ref)).toEqual(["a"]);
  });
  it("runner dùng cùng mốc nhắc như app (module dùng chung)", () => {
    const occs = [occ(1, "2026-10-29T09:00:00", { remind_before_min: 15 })];
    const plan = planBackground(reminderPoints(occs, NOW_MS), {}, {}, NOW_MS);
    expect(plan.toSchedule[0].atMs).toBe(Date.parse("2026-10-29T08:45:00" + OFF));
    expect(plan.toSchedule[0].atMs - NOW_MS).toBeGreaterThan(MIN);
  });
});

describe("createSync với runner nền", () => {
  const api = (list: Occurrence[]): SyncApi => ({
    async info() { return { tz: "Asia/Ho_Chi_Minh", now: "2026-10-28T10:00:00" }; },
    async events(from, to) { return list.filter((o) => o.occurrence >= from && o.occurrence < to); },
  });
  const cal: CalendarPort = { async ensureCalendar() {}, async listManaged() { return []; }, async applyDiff() {} };
  const mk = (list: Occurrence[], bg: RefMap) => {
    const scheduled: string[] = [];
    let saved: RefMap = {};
    const notifier: NotifierPort = { async cancelAll() {}, async schedule(p) { scheduled.push(...p.map((x) => x.ref)); } };
    const run = createSync({
      api: api(list), calendar: cal, notifier, now: () => NOW_MS,
      shared: { async bgRefs() { return bg; }, async saveAppRefs(r) { saved = r; } },
    });
    return { run, scheduled, saved: () => saved };
  };

  it("app bỏ mốc runner đã hẹn và ghi lại mốc của mình", async () => {
    const list = [occ(1, "2026-10-29T09:00:00"), occ(2, "2026-10-30T09:00:00")];
    const t = mk(list, { "lv-1-202610290900": Date.parse("2026-10-29T09:00:00" + OFF) });
    const r = await t.run();
    expect(t.scheduled).toEqual(["lv-2-202610300900"]);
    expect(r.scheduled).toBe(1);
    expect(t.saved()).toEqual({ "lv-2-202610300900": Date.parse("2026-10-30T09:00:00" + OFF) });
  });
  it("mốc runner đã hẹn nhưng giờ hẹn khác thì app vẫn hẹn", async () => {
    const t = mk([occ(1, "2026-10-29T09:00:00")], { "lv-1-202610290900": 123 });
    await t.run();
    expect(t.scheduled).toEqual(["lv-1-202610290900"]);
  });
  it("bản ghi của app khớp refMapOf", () => {
    expect(refMapOf([pt("x", 1)])).toEqual({ x: 1 });
  });
});
