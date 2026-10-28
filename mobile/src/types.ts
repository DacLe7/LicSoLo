/** Một lần xảy ra của việc, đúng dạng GET /v1/events (service.list_range + api.with_iso). */
export interface Occurrence {
  id: number;
  title: string;
  /** giờ địa phương theo tz của server, không kèm múi giờ: 2026-10-28T09:00:00 */
  occurrence: string;
  /** cùng giờ, kèm độ lệch: 2026-10-28T09:00:00+07:00 */
  occurrence_iso: string;
  all_day: boolean;
  duration_min: number | null;
  repeat: string | null;
  remind_before_min: number | null;
  notes: string | null;
  lunar_day?: number | null;
  lunar_month?: number | null;
}

export interface ServerInfo {
  tz: string;
  /** giờ địa phương của server, không kèm múi giờ */
  now: string;
}

export interface ParseDraft {
  title: string;
  start: string | null;
  all_day: boolean;
  duration_min: number | null;
  repeat: string | null;
  remind_before_min: number | null;
  warnings: string[];
  used_ai: boolean;
  ai: { status: string; detail?: string; raw?: string } | null;
  lunar: [number, number] | null;
  memory: unknown;
}

export interface ParseResult {
  status: "draft" | "need_info" | "saved";
  missing?: string[];
  draft: ParseDraft;
  conflicts?: { title: string; occurrence: string }[];
  event?: { id: number; start: string; all_day: boolean; duplicate?: boolean };
}

export interface NewEvent {
  title: string;
  start: string;
  all_day: boolean;
  duration_min: number | null;
  repeat: string | null;
  remind_before_min: number | null;
  lunar: [number, number] | null;
}

/** Phần của server mà đồng bộ cần. */
export interface SyncApi {
  info(): Promise<ServerInfo>;
  events(from: string, to: string): Promise<Occurrence[]>;
}

/** Một sự kiện ghi vào lịch hệ thống. Mili giây UTC; việc cả ngày: 00:00 UTC và tz = "UTC". */
export interface CalendarItem {
  ref: string;
  title: string;
  startMs: number;
  endMs: number;
  allDay: boolean;
  tz: string;
  notes: string;
  hash: string;
}

export interface ManagedEntry {
  ref: string;
  eventId: number;
  hash: string;
}

export interface CalendarDiff {
  insert: CalendarItem[];
  update: (CalendarItem & { eventId: number })[];
  delete: number[];
}

export interface CalendarPort {
  ensureCalendar(): Promise<void>;
  listManaged(): Promise<ManagedEntry[]>;
  applyDiff(diff: CalendarDiff): Promise<void>;
}

export interface ReminderPoint {
  ref: string;
  /** mốc hẹn, mili giây UTC */
  atMs: number;
  title: string;
  body: string;
}

export interface NotifierPort {
  cancelAll(): Promise<void>;
  schedule(points: (ReminderPoint & { id: number })[]): Promise<void>;
}

export interface SyncResult {
  ok: boolean;
  /** lỗi mạng hoặc server: không đụng tới lịch và thông báo cũ */
  error?: string;
  calendarError?: string;
  notifyError?: string;
  inserted: number;
  updated: number;
  deleted: number;
  scheduled: number;
  occurrences: Occurrence[];
}
