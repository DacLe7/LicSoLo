"""lichviet - lõi lịch/nhắc việc tiếng Việt. Chỉ dùng thư viện chuẩn, không cần AI."""
from .service import Service
from .parser import parse_vi, ParseResult

__all__ = ["Service", "parse_vi", "ParseResult"]
