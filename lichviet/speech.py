"""Chuẩn hóa chữ do nhận giọng nói trả về: số đọc thành chữ ("ba giờ", "mười lăm tháng tám") đổi thành chữ số
("3 giờ", "15 tháng 8") để bộ phân tích hiểu như khi gõ tay.

Chỉ đổi khi ngữ cảnh chắc chắn là một con số: đứng trước giờ/phút/tháng/ngày/h hoặc đứng sau ngày/tháng/mùng/mồng/giờ.
Vì vậy "thứ ba", "thứ năm", "năm sau", "ngày mốt", "ba mẹ" được giữ nguyên.
"""
from .parser import fold

_UNIT = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9}
_AFTER_TENS = {**_UNIT, "tu": 4, "lam": 5}
_NEXT_OK = {"gio", "h", "phut", "thang", "ngay"}
_PREV_OK = {"ngay", "thang", "mung", "mong", "gio"}
_NUMWORDS = set(_UNIT) | {"muoi", "tu", "lam", "linh", "le"}


def _clean(tok: str) -> str:
    return tok.strip(",.;:!?")


def _read_number(toks, i):
    """Đọc một số 1..99 bắt đầu ở vị trí i. Trả về (giá trị, số từ đã dùng) hoặc None."""
    f = [fold(_clean(t)) for t in toks]
    raw = [_clean(t).lower() for t in toks]
    n = len(toks)
    if f[i] == "muoi":                                   # mười, mười một, mười lăm
        if i + 1 < n and f[i + 1] in _AFTER_TENS and f[i + 1] not in ("tu",):
            return 10 + _AFTER_TENS[f[i + 1]], 2
        return 10, 1
    if f[i] in _UNIT and not (f[i] == "mot" and raw[i] == "mốt"):
        if i + 1 < n and f[i + 1] == "muoi" and f[i] != "mot":   # hai mươi, hai mươi ba, hai mươi mốt
            if i + 2 < n and f[i + 2] in _AFTER_TENS and not (f[i + 2] in ("tu",) and False):
                return _UNIT[f[i]] * 10 + _AFTER_TENS[f[i + 2]], 3
            return _UNIT[f[i]] * 10, 2
        return _UNIT[f[i]], 1
    return None


# Giọng địa phương hay bị nghe lệch: "năm giờ" -> "nêm/nem/nềm giờ", "bốn mươi lăm" -> "bốn mưu lem".
# Chỉ sửa khi ngữ cảnh gần như chắc chắn (nêm/nem đứng ngay trước "giờ"; mưu/mưi đứng sau số).
_NAM_VARIANTS = {"nem", "nham"}
_MUOI_VARIANTS = {"muu", "mui", "muoi"}
_LAM_VARIANTS = {"lem", "lam", "nem", "nham"}


def dialect_fix(text: str) -> str:
    toks = text.split()
    f = [fold(_clean(t)) for t in toks]
    for i, t in enumerate(toks):
        nxt = f[i + 1] if i + 1 < len(toks) else ""
        if f[i] in _NAM_VARIANTS and nxt == "gio":
            toks[i] = "năm" + t[len(t.rstrip(",.;:!?")):]
            f[i] = "nam"
    for i in range(1, len(toks) - 1):   # [số] mưu/mưi [lem/nem]: "4 mưu lem" -> "4 mươi lăm"
        if f[i] in _MUOI_VARIANTS and (f[i - 1].isdigit() or f[i - 1] in _UNIT) and f[i - 1] not in ("0", "1"):
            toks[i] = "mươi"
            if f[i + 1] in _LAM_VARIANTS or f[i + 1] in _UNIT:
                tail = toks[i + 1][len(toks[i + 1].rstrip(",.;:!?")):]
                if f[i + 1] in _LAM_VARIANTS:
                    toks[i + 1] = "lăm" + tail
    return " ".join(toks)


def digits_from_words(text: str) -> str:
    text = dialect_fix(text)
    toks = text.split()
    out, i = [], 0
    while i < len(toks):
        f = fold(_clean(toks[i]))
        if f == "tu" and i and fold(_clean(toks[i - 1])) == "thang" and _clean(toks[i]).lower() == "tư":
            tail = toks[i]                                  # "tháng tư" = tháng 4
            out.append("4" + tail[len(tail.rstrip(",.;:!?")):])
            i += 1
            continue
        if f.isdigit() and 2 <= int(f) <= 9 and i + 1 < len(toks) and fold(_clean(toks[i + 1])) == "muoi":
            val, used = int(f) * 10, 2                       # "4 mươi lăm" -> 45
            if i + 2 < len(toks) and fold(_clean(toks[i + 2])) in _AFTER_TENS:
                val, used = val + _AFTER_TENS[fold(_clean(toks[i + 2]))], 3
            tail = toks[i + used - 1]
            out.append(str(val) + tail[len(tail.rstrip(",.;:!?")):])
            i += used
            continue
        if f in _NUMWORDS and f not in ("tu", "lam", "linh", "le"):
            got = _read_number(toks, i)
            prev = fold(_clean(toks[i - 1])) if i else ""
            if got and prev != "thu":
                val, used = got
                nxt = fold(_clean(toks[i + used])) if i + used < len(toks) else ""
                if nxt in _NEXT_OK or prev in _PREV_OK:
                    tail = toks[i + used - 1]
                    punct = tail[len(tail.rstrip(",.;:!?")):]
                    out.append(str(val) + punct)
                    i += used
                    continue
        out.append(toks[i])
        i += 1
    return " ".join(out)
