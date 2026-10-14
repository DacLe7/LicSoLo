"""Múi giờ của người dùng. Mặc định Việt Nam (UTC+7, không có giờ mùa hè).

Đặt biến môi trường LICHVIET_TZ (ví dụ Asia/Bangkok, America/Los_Angeles) để đổi.
Câu lệnh như "mai", "3h chiều" luôn được hiểu theo múi giờ này, không phụ thuộc
múi giờ của máy chủ hay của container (thường là UTC).
"""
import os
from datetime import datetime, timedelta, timezone

DEFAULT_TZ = "Asia/Ho_Chi_Minh"


def get_tz():
    name = os.environ.get("LICHVIET_TZ", DEFAULT_TZ)
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        # thiếu dữ liệu múi giờ trong image: lùi về UTC+7 cho mặc định
        return timezone(timedelta(hours=7)) if name == DEFAULT_TZ else timezone.utc


def local_now() -> datetime:
    """Giờ hiện tại theo múi giờ người dùng, dạng naive (cùng kiểu dữ liệu đang lưu)."""
    return datetime.now(get_tz()).replace(tzinfo=None)