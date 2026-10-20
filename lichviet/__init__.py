"""lichviet - lõi lịch/nhắc việc tiếng Việt. Chỉ dùng thư viện chuẩn, không cần AI."""
__version__ = "0.6.0"   # tăng khi phát hành; hiện ở /health, /v1/info và chân trang

from .service import Service
from .parser import parse_vi, ParseResult

__all__ = ["Service", "parse_vi", "ParseResult", "__version__"]
