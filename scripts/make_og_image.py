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


def find_font(*candidates: str) -> str | None:
    """Return the first font path that exists on this system."""
    import os
    for name in candidates:
        for prefix in ("/System/Library/Fonts/", "/Library/Fonts/", "/usr/share/fonts/",
                       "/System/Library/Fonts/Supplemental/"):
            for ext in (".ttf", ".ttc", ".otf"):
                p = os.path.join(prefix, name + ext)
                if os.path.exists(p):
                    return p
        if os.path.exists(name):
            return name
    return None


def load_font(size: int, *candidates: str) -> ImageFont.FreeTypeFont:
    path = find_font(*candidates)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
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

    # Pick the best slab serif and monospace fonts available locally.
    slab  = load_font(110, "Times New Roman Bold", "Times-Bold", "DejaVuSerif-Bold", "Georgia Bold")
    small = load_font(28,  "Courier New Bold", "Courier", "DejaVuSansMono-Bold")
    tag   = load_font(40,  "Times New Roman Bold", "Georgia Bold")

    # Eyebrow
    eyebrow = "★  DAILY  ★"
    bbox = d.textbbox((0, 0), eyebrow, font=small)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 80), eyebrow, font=small, fill=RED)

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
    url = "play.roundthebases.com"
    bbox = d.textbbox((0, 0), url, font=small)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 560), url, font=small, fill=INK)

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
