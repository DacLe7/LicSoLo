/** Hằng số dùng chung giữa app và runner nền. Phải khớp với plugins.BackgroundRunner.label trong capacitor.config.ts. */
export const RUNNER_LABEL = "vn.lacvietnode.lich.bg";
export const RUNNER_EVENT = "syncReminders";
export const DEFAULT_URL = "https://d.taila2d06a.ts.net";

/** Khóa trong kho chung (SharedPreferences tên RUNNER_LABEL): app ghi qua Preferences, runner đọc qua CapacitorKV. */
export const KEY = {
  serverUrl: "serverUrl",
  lastSync: "lastSync",
  onboarded: "onboarded",
  bgEnabled: "bgEnabled", // "0" = tắt; thiếu hoặc "1" = bật
  tzOffsetMin: "tzOffsetMin", // độ lệch múi giờ của máy (phút), runner cần để hẹn đúng giờ
  appRefs: "appRefs", // mốc app đã hẹn
  bgRefs: "bgRefs", // mốc runner đã hẹn
  bgLastRun: "bgLastRun", // ms của lần runner chạy xong gần nhất
  bgLastError: "bgLastError",
} as const;
