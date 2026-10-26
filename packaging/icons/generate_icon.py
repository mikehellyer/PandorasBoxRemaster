"""One-off script: draws the Pandora's Box Remaster app icon (our own design, none of
the original's art) and exports the sizes the installers need. Re-run by hand if the
design changes; the outputs are committed.

Usage: venv/bin/python packaging/icons/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parent
SIZE = 1024
WOOD = (74, 30, 10, 255)
WOOD_DARK = (46, 17, 5, 255)
GOLD = (232, 168, 74, 255)
GOLD_DARK = (168, 104, 34, 255)
GLOW = (255, 226, 150)


def draw_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = SIZE * 0.06
    d.rounded_rectangle([m, m, SIZE - m, SIZE - m], radius=SIZE * 0.22, fill=(32, 12, 4, 255))

    # light escaping from the opened lid
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.polygon([(SIZE * 0.30, SIZE * 0.47), (SIZE * 0.70, SIZE * 0.47), (SIZE * 0.88, SIZE * 0.12),
               (SIZE * 0.12, SIZE * 0.12)], fill=GLOW + (150,))
    glow = glow.filter(ImageFilter.GaussianBlur(SIZE * 0.04))
    img.alpha_composite(glow)

    # the box: front face and top rim
    x0, x1, y0, y1 = SIZE * 0.24, SIZE * 0.76, SIZE * 0.50, SIZE * 0.82
    d.rounded_rectangle([x0, y0, x1, y1], radius=SIZE * 0.03, fill=WOOD, outline=GOLD, width=int(SIZE * 0.018))
    d.rectangle([x0, y0 - SIZE * 0.035, x1, y0 + SIZE * 0.015], fill=GOLD_DARK)
    # gold bands and corner studs
    for fx in (0.36, 0.64):
        x = SIZE * fx
        d.rectangle([x - SIZE * 0.014, y0, x + SIZE * 0.014, y1], fill=GOLD_DARK)
    for cx, cy in ((x0 + 22, y0 + 22), (x1 - 22, y0 + 22), (x0 + 22, y1 - 22), (x1 - 22, y1 - 22)):
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=GOLD)
    # keyhole plate
    kx, ky = SIZE * 0.5, SIZE * 0.66
    d.ellipse([kx - SIZE * 0.07, ky - SIZE * 0.07, kx + SIZE * 0.07, ky + SIZE * 0.07], fill=GOLD,
              outline=GOLD_DARK, width=8)
    d.ellipse([kx - 18, ky - 34, kx + 18, ky + 2], fill=WOOD_DARK)
    d.polygon([(kx - 12, ky - 6), (kx + 12, ky - 6), (kx + 18, ky + 40), (kx - 18, ky + 40)], fill=WOOD_DARK)

    # the lid, tipped open
    # open lid seen from the front: its lit inner face widens as it swings back
    lid = [(x0, y0 - SIZE * 0.04), (x1, y0 - SIZE * 0.04),
           (x1 + SIZE * 0.05, y0 - SIZE * 0.30), (x0 - SIZE * 0.05, y0 - SIZE * 0.30)]
    d.polygon(lid, fill=(150, 84, 30, 255))
    inner = [(x0 + 18, y0 - SIZE * 0.06), (x1 - 18, y0 - SIZE * 0.06),
             (x1 + SIZE * 0.03, y0 - SIZE * 0.28), (x0 - SIZE * 0.03, y0 - SIZE * 0.28)]
    d.polygon(inner, fill=(214, 150, 76, 255))
    d.line(lid + [lid[0]], fill=GOLD, width=int(SIZE * 0.016))

    # a few sparks
    for sx, sy, r in ((0.30, 0.18, 14), (0.62, 0.14, 18), (0.76, 0.24, 11), (0.45, 0.10, 9)):
        d.ellipse([SIZE * sx - r, SIZE * sy - r, SIZE * sx + r, SIZE * sy + r], fill=GLOW + (255,))
    return img


def main():
    icon = draw_icon()
    icon.save(OUT / "icon.png")
    icon.save(OUT / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    for s in (16, 32, 48, 64, 128, 256, 512):
        icon.resize((s, s), Image.LANCZOS).save(OUT / f"icon_{s}.png")
    print("wrote icon.png, icon.ico, icon_16..512.png")


if __name__ == "__main__":
    main()
