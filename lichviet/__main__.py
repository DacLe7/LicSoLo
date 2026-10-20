import os
import sys
from datetime import datetime, timedelta
from .service import Service

USAGE = "dùng: python -m lichviet <db> add \"câu lệnh\" | today | week | due | serve [port]"


def main(argv):
    if len(argv) < 2:
        print(USAGE); return 1
    db, cmd, rest = argv[0], argv[1], argv[2:]
    if cmd == "serve":
        import logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        from .api import serve
        serve(db, host=os.environ.get("LICHVIET_HOST", "127.0.0.1"), port=int(rest[0]) if rest else 8765); return 0
    s = Service(db)
    now = s.clock()
    if cmd == "add" and rest:
        r = s.from_text(" ".join(rest), save=True)
        if r["status"] == "need_info":
            print("Thiếu:", ", ".join(r["missing"]), r["draft"])
        else:
            e = r["event"]
            print("Đã lưu #%d: %s lúc %s" % (e["id"], e["title"], e["start"]))
            for c in r["conflicts"]:
                print("  Lưu ý: trùng với", c["title"], c["occurrence"])
    elif cmd in ("today", "week"):
        lo = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for e in s.list_range(lo, lo + timedelta(days=1 if cmd == "today" else 7)):
            print(e["occurrence"].replace("T", " "), "-", e["title"])
    elif cmd == "due":
        for d in s.due_reminders():
            print(d["occurrence"].replace("T", " "), "-", d["title"])
    else:
        print(USAGE); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
