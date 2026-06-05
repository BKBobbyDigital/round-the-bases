"""
Generate og.png — the brand image that appears in Twitter cards,
iMessage previews, Slack unfurls, etc. 1200x630 (OG standard).

Run once after font or copy changes:
    python3 scripts/make_og_image.py
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "og.png"

W, H = 1200, 630
CREAM   = (241, 228, 200)
INK     = (26, 22, 18)
RED     = (178, 42, 43)
DIRT    = (139, 106, 63)
GREEN   = (53, 90, 59)


import os

# Concrete font paths covering macOS, Linux, and GitHub Actions runners.
# Tried in order; first one that exists wins. Every entry should support ★ (U+2605).
SERIF_PATHS = [
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",   # macOS
    "/System/Library/Fonts/Times.ttc",                                # macOS
    "/Library/Fonts/Times New Roman Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # Ubuntu / GH runners
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
SANS_PATHS = [
    # Arial Unicode actually has ★; Arial Bold's cmap maps it to a tofu box.
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux: real stars
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # last resort
    "/System/Library/Fonts/Helvetica.ttc",
]
MONO_PATHS = [
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/System/Library/Fonts/Courier.ttc",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]


def load_font(size: int, paths: list[str]) -> ImageFont.FreeTypeFont:
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # Halftone stipple
    for y in range(4, H, 8):
        for x in range(4, W, 8):
            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(26, 22, 18, 30))

    # Outer ticket-stub dashed border (manual dashes — Pillow has no built-in dash)
    def dashed_rect(box, dash=18, gap=12, width=4):
        x0, y0, x1, y1 = box
        def segs(a, b):
            i = a
            while i < b:
                yield i, min(i + dash, b)
                i += dash + gap
        for s, e in segs(x0, x1):
            d.line([(s, y0), (e, y0)], fill=INK, width=width)
            d.line([(s, y1), (e, y1)], fill=INK, width=width)
        for s, e in segs(y0, y1):
            d.line([(x0, s), (x0, e)], fill=INK, width=width)
            d.line([(x1, s), (x1, e)], fill=INK, width=width)

    dashed_rect((36, 36, W - 36, H - 36))

    slab  = load_font(110, SERIF_PATHS)
    small = load_font(28,  MONO_PATHS)
    eyebrow_f = load_font(32, SANS_PATHS)   # for ★, which the mono font may lack

    # Eyebrow — uses a sans font that reliably has ★ (U+2605).
    eyebrow = "★  DAILY  ★"
    bbox = d.textbbox((0, 0), eyebrow, font=eyebrow_f)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 70), eyebrow, font=eyebrow_f, fill=RED)

    # Title
    title = "ROUND THE BASES"
    bbox = d.textbbox((0, 0), title, font=slab)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) / 2, 130), title, font=slab, fill=INK)

    # Double underline under title
    y_ul = 280
    cx = W // 2
    d.line([(cx - 380, y_ul),     (cx + 380, y_ul)],     fill=INK, width=4)
    d.line([(cx - 380, y_ul + 10), (cx + 380, y_ul + 10)], fill=INK, width=4)

    # Tag line
    tagline = "ONE AT-BAT.  FOUR PITCHES.  REAL BASEBALL SCORING."
    bbox = d.textbbox((0, 0), tagline, font=small)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 320), tagline, font=small, fill=INK)

    # A central baseball icon — drawn from primitives so we don't depend on emoji fonts.
    bx, by, br = W // 2, 450, 70
    d.ellipse((bx - br, by - br, bx + br, by + br), fill=(252, 247, 235), outline=INK, width=4)
    # Stitches
    for offset in (-30, 30):
        d.arc((bx - br + 10 + offset, by - br + 10,
               bx + br + offset, by + br - 10),
              start=240 if offset < 0 else 60,
              end=300 if offset < 0 else 120,
              fill=RED, width=4)

    # Footer URL
    url = "playroundthebases.com"
    bbox = d.textbbox((0, 0), url, font=small)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 560), url, font=small, fill=INK)

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
