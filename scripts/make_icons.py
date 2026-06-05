"""
Generate PWA / Home-Screen icons:

    icon-192.png         (Android / Chrome Web App)
    icon-512.png         (Android maskable + splash)
    apple-touch-icon.png (iOS, 180x180)
    favicon-32.png       (browser tab)

Design: cream paper background with a centered baseball drawn from
primitives — matches the brand image. Reuses draw_baseball() from
make_og_image so the icon and OG image share the same baseball.
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_og_image import draw_baseball, CREAM, INK, RED  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

ICONS = [
    ("icon-192.png", 192),
    ("icon-512.png", 512),
    ("apple-touch-icon.png", 180),
    ("favicon-32.png", 32),
]


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), CREAM)
    d = ImageDraw.Draw(img)

    # Subtle paper grain — only at larger sizes; skipped at 32px (too noisy).
    if size >= 96:
        step = max(4, size // 48)
        for y in range(step // 2, size, step):
            for x in range(step // 2, size, step):
                d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(26, 22, 18, 40))

    # Inset border — gives the icon definition against bright backgrounds.
    pad = max(2, size // 20)
    border_w = max(1, size // 48)
    d.rectangle((pad, pad, size - pad - 1, size - pad - 1),
                outline=INK, width=border_w)

    # Centered baseball — fills most of the inner box.
    ball_r = int(size * 0.32)
    bx = by = size // 2
    # Scale stitch widths and tick counts with icon size for legibility.
    stroke_w  = max(2, size // 48)
    seam_w    = max(2, size // 48)
    tick_n    = 7 if size >= 128 else 5 if size >= 64 else 0
    draw_baseball(d, bx, by, ball_r,
                  ball_stroke_width=stroke_w,
                  seam_width=seam_w,
                  tick_count=tick_n)

    return img


def main() -> None:
    for name, size in ICONS:
        out = ROOT / name
        img = make_icon(size)
        img.save(out, "PNG", optimize=True)
        print(f"wrote {name:25s} ({size}×{size}, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
