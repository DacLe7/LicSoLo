"""Chuẩn hóa chữ do nhận giọng nói trả về: số đọc thành chữ ("ba giờ", "mười lăm tháng tám") đổi thành chữ số
("3 giờ", "15 tháng 8") để bộ phân tích hiểu như khi gõ tay.

Chỉ đổi khi ngữ cảnh chắc chắn là một con số: đứng trước giờ/phút/tháng/ngày/h hoặc đứng sau ngày/tháng/mùng/mồng/giờ.
Vì vậy "thứ ba", "thứ năm", "năm sau", "ngày mốt", "ba mẹ" được giữ nguyên.
"""
import re

from .parser import fold

_UNIT = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9}
_AFTER_TENS = {**_UNIT, "tu": 4, "lam": 5, "nham": 5}
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
_MUOI_VARIANTS = {"muu", "mui", "muoi"}
_LAM_VARIANTS = {"lem", "lam", "nem", "nham"}


_TAIL = ",.;:!?"
_DAYPART = {"ngày", "bữa", "sáng", "trưa", "chiều", "tối", "đêm"}


def _punct(t: str) -> str:
    return t[len(t.rstrip(_TAIL)):]


def _is_hour(f: str) -> bool:
    """Từ (đã bỏ dấu) đứng ngay trước buổi trong ngày khi nói giờ: "giờ", "rưỡi", "3", "3h", "15h30".
    Không tính số đọc bằng chữ để "chín chưa" (xoài chín chưa) không thành "chín trưa"."""
    return (f in ("gio", "h", "ruoi", "kem")
            or re.fullmatch(r"\d{1,2}(h|g|gio)?(\d{2})?", f) is not None)


# Từ nghe lệch theo vùng miền -> từ đúng, chỉ áp dụng khi từ đứng cạnh khớp điều kiện (xem dialect_fix).
_HOUR_WORDS = {"dờ", "dzờ", "giừ", "dừ", "rờ", "zờ"}          # "giờ" đọc theo giọng Nam/Trung
_DAY_AFTER = {"nay", "mai", "qua", "kia", "mot", "sau", "toi", "sang", "chieu", "trua", "dem"}
_PERIOD_WORDS = {"sáng": {"xáng"}, "chiều": {"triều", "chìu"}, "trưa": {"chưa", "chua"}, "tối": {"tói", "tồi"}}
_PERIOD_FIX = {v: k for k, vs in _PERIOD_WORDS.items() for v in vs}


def dialect_fix(text: str) -> str:
    """Sửa các chỗ nghe lệch do giọng địa phương, chỉ khi ngữ cảnh gần như chắc chắn.
    Không sửa mù các từ thật (nêm, nem, chưa, tấm...): luôn dựa vào từ đứng cạnh (giờ, mươi, ngày...)."""
    toks = text.split()
    out = []
    for i, t in enumerate(toks):
        raw = _clean(t).lower()
        f = fold(raw)
        p = _punct(t)
        prev = _clean(toks[i - 1]).lower() if i else ""
        pf = fold(prev)
        nf = fold(_clean(toks[i + 1])) if i + 1 < len(toks) else ""
        # "nêm/nem/nhăm/lăm giờ" -> "năm giờ" (lăm sau mười/mươi là đúng nên giữ)
        if nf == "gio" and (f in ("nem", "nham") or (f == "lam" and pf != "muoi")):
            out.append("năm" + p)
        elif nf == "gio" and f == "xau":
            out.append("sáu" + p)
        elif nf == "gio" and f == "trin":
            out.append("chín" + p)
        # "ba dờ chiều", "mười dzờ" -> "giờ" (chỉ khi ngay trước là một con số)
        elif raw in _HOUR_WORDS and (pf in _UNIT or pf in ("muoi", "ruoi") or pf.isdigit()):
            out.append("giờ" + p)
        # tr/ch, s/x, hỏi/ngã ở buổi trong ngày: "3 giờ triều mai", "12 giờ chưa", "7 giờ xáng" (chỉ sau giờ)
        elif raw in _PERIOD_FIX and _is_hour(pf):
            out.append(_PERIOD_FIX[raw] + p)
        elif raw in ("triều", "chìu", "xáng") and nf in ("mai", "nay", "qua", "mot", "kia"):
            out.append(_PERIOD_FIX[raw] + p)
        # "rưởi/rưới" -> "rưỡi" sau giờ; "30 phút nửa" -> "nữa"; "tuần xau" -> "tuần sau"
        elif raw in ("rưởi", "rưới", "rửi", "rưỡi") and _is_hour(pf):
            out.append("rưỡi" + p)
        elif raw in ("nửa", "nưa", "lữa", "lửa") and pf in ("phut", "tieng", "ngay", "hom", "tuan", "thang") and nf != "dem":
            out.append("nữa" + p)
        elif raw == "xau" and pf in ("tuan", "thang", "nam", "hom", "bua", "ngay"):
            out.append("sau" + p)
        # "mõi/mổi/mội ngày" -> "mỗi"; "bửa nay" -> "bữa"; "chủ nhựt" -> "chủ nhật"; "giổ" -> "giỗ"
        elif raw in ("mõi", "mổi", "mội") and nf in ("ngay", "tuan", "thang", "nam", "sang", "toi", "chieu", "trua", "dem"):
            out.append("mỗi" + p)
        elif raw in ("bửa", "bựa") and nf in _DAY_AFTER | {"hom", "kia", "truoc"}:
            out.append("bữa" + p)
        elif raw == "nhựt" and pf == "chu":
            out.append("nhật" + p)
        elif raw in ("giổ", "giộ"):   # không đụng "dỗ" (dỗ em ngủ) vì là từ thật
            out.append(("Giỗ" if t[:1].isupper() else "giỗ") + p)
        # l/n: "tối nai", "hôm lay" -> "nay"; "lăm sau" (= năm sau) ở cuối cụm thời gian
        elif raw in ("nai", "lay") and pf in ("toi", "sang", "chieu", "trua", "dem", "hom", "bua", "tuan", "thang", "nam"):
            out.append("nay" + p)
        elif raw == "lăm" and nf in ("sau", "ngoai", "toi") and pf in ("", "cuoi", "dau", "giua", "trong"):
            out.append("năm" + p)
        # "hăm" = hai mươi (hăm lăm, hăm mốt), "nhăm" = lăm sau hàng chục
        elif raw == "hăm" and (nf in _AFTER_TENS or nf in _NEXT_OK or pf in _PREV_OK):
            out.extend(["hai", "mươi" + p])
        elif raw == "nhăm" and pf == "muoi":
            out.append("lăm" + p)
        # từ chỉ ngày của Nam Bộ
        elif raw == "mơi":
            out.append("mai" + p)
        elif raw == "mốt" and prev in _DAYPART:      # "ngày mốt", "bữa mốt", "chiều mốt" = ngày kia
            if prev == "ngày":
                out.append("kia" + p)
            elif prev == "bữa":
                out[-1:] = ["ngày", "kia" + p]
            else:
                out[-1:] = ["ngày", "kia", toks[i - 1] + p]
        elif raw in ("này", "nay") and prev == "bữa":
            out[-1] = "hôm"
            out.append("nay" + p)
        # dạng viết tắt: T2..T7, CN
        elif len(raw) == 2 and raw[0] == "t" and raw[1] in "234567":
            out.extend(["thứ", raw[1] + p])
        elif raw == "cn":
            out.extend(["chủ", "nhật" + p])
        else:
            out.append(t)
    toks = out
    f = [fold(_clean(t)) for t in toks]
    for i in range(1, len(toks) - 1):   # [số] mưu/mưi [lem/nem]: "4 mưu lem" -> "4 mươi lăm"
        if f[i] in _MUOI_VARIANTS and (f[i - 1].isdigit() or f[i - 1] in _UNIT) and f[i - 1] not in ("0", "1"):
            toks[i] = "mươi"
            if f[i + 1] in _LAM_VARIANTS:
                toks[i + 1] = "lăm" + _punct(toks[i + 1])
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
