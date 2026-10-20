import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  start TEXT NOT NULL,
  duration_min INTEGER,
  all_day INTEGER NOT NULL DEFAULT 0,
  repeat TEXT,
  remind_before_min INTEGER,
  notes TEXT,
  created TEXT NOT NULL,
  updated TEXT NOT NULL,
  lunar_day INTEGER,
  lunar_month INTEGER
);
CREATE TABLE IF NOT EXISTS fired(
  event_id INTEGER NOT NULL,
  occ_start TEXT NOT NULL,
  PRIMARY KEY(event_id, occ_start)
);
CREATE TABLE IF NOT EXISTS acked(
  event_id INTEGER NOT NULL,
  occ_start TEXT NOT NULL,
  PRIMARY KEY(event_id, occ_start)
);
CREATE TABLE IF NOT EXISTS changes(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  op TEXT NOT NULL,            -- upsert | delete (bia mộ)
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_changes_event ON changes(event_id, seq);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS devices(
  device_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,      -- ios | android | other
  label TEXT,
  registered TEXT NOT NULL,
  last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS delivered(   -- nhắc đã hiển thị trên từng thiết bị (không lưu token push)
  device_id TEXT NOT NULL,
  event_id INTEGER NOT NULL,
  occ_key TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY(device_id, event_id, occ_key)
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);
CREATE TABLE IF NOT EXISTS phrases(
  src TEXT PRIMARY KEY,
  dst TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0,
  uses INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS heard(
  src TEXT PRIMARY KEY,
  dst TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0,
  uses INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
"""

ISO = "%Y-%m-%dT%H:%M:%S"


def fmt(dt: datetime) -> str:
    return dt.strftime(ISO)


def parse(s: str) -> datetime:
    return datetime.strptime(s, ISO)


def _migrate(con: sqlite3.Connection) -> None:
    """Nâng cấp database cũ: thêm cột còn thiếu, không đụng đến dữ liệu đã có."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(events)")}
    for name in ("lunar_day", "lunar_month"):
        if name not in cols:
            con.execute("ALTER TABLE events ADD COLUMN %s INTEGER" % name)
    con.commit()


def connect(path: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(path, check_same_thread=False, timeout=5.0)
    con.row_factory = sqlite3.Row
    if path != ":memory:":
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA journal_mode=WAL")   # đọc và ghi không chặn nhau giữa các luồng/tiến trình
    con.executescript(SCHEMA)
    _migrate(con)
    # Nâng cấp từ bản chưa có nhật ký thay đổi: coi mọi việc hiện có là "đã upsert" để đồng bộ lần đầu thấy đủ.
    if con.execute("SELECT 1 FROM changes LIMIT 1").fetchone() is None:
        con.execute("INSERT INTO changes(event_id,op,at) SELECT id,'upsert',updated FROM events")
        con.commit()
    return con
