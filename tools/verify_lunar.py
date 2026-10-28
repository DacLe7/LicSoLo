"""Đối chiếu lịch âm của LicSoLo với tính toán thiên văn độc lập (giờ Việt Nam, UTC+7).
Chạy từ thư mục gốc repo: pip install ephem && python tools/verify_lunar.py [năm_đầu] [năm_cuối]
Thoát mã 1 nếu có tháng lệch."""
import sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ephem
from lichviet.lunar import solar_to_lunar
y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2040
lo, hi = date(y0, 1, 1), date(y1, 12, 31)
truth, near = set(), []
d = ephem.Date(f"{y0}/1/1")
while True:
    d = ephem.next_new_moon(d)
    u = ephem.Date(d).datetime() + timedelta(hours=7)
    if u.date() > hi:
        break
    if u.date() >= lo:
        truth.add(u.date())
        m = u.hour * 60 + u.minute
        if m < 10 or m > 1430:
            near.append(u.strftime("%d/%m/%Y %H:%M"))
code, x = set(), lo
while x <= hi:
    if solar_to_lunar(x)[0] == 1:
        code.add(x)
    x += timedelta(days=1)
diff = sorted(truth ^ code)
print(f"{len(truth)} tháng trong {y0}-{y1}; lệch: {len(diff)}")
if near:
    print("Trăng mới cách nửa đêm dưới 10 phút:", ", ".join(near))
for x in diff:
    print("lệch:", x.isoformat())
sys.exit(1 if diff else 0)
