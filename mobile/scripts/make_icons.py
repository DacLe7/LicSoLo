"""Tạo icon launcher Android từ ../icon/icon.png. Chạy: python scripts/make_icons.py (cần Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = Image.open(ROOT.parent / "icon" / "icon.png").convert("RGBA")
RES = ROOT / "android" / "app" / "src" / "main" / "res"
DENSITY = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def fit(size: int) -> Image.Image:
    return SRC.resize((size, size), Image.LANCZOS)


for name, k in DENSITY.items():
    d = RES / f"mipmap-{name}"
    legacy = round(48 * k)
    fg = round(108 * k)
    fit(legacy).save(d / "ic_launcher.png")
    # vòng tròn cho ic_launcher_round
    big = fit(legacy)
    mask = Image.new("L", (legacy, legacy), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, legacy - 1, legacy - 1), fill=255)
    rnd = Image.new("RGBA", (legacy, legacy), (0, 0, 0, 0))
    rnd.paste(big, (0, 0), mask)
    rnd.save(d / "ic_launcher_round.png")
    # lớp trước của icon thích ứng: icon chiếm 61% giữa khung (vùng an toàn là 66%)
    canvas = Image.new("RGBA", (fg, fg), (0, 0, 0, 0))
    inner = round(fg * 0.61)
    canvas.paste(fit(inner), ((fg - inner) // 2, (fg - inner) // 2))
    canvas.save(d / "ic_launcher_foreground.png")
print("xong")
