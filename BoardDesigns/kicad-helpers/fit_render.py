#!/usr/bin/env python3
"""Trim a board render to the board and stand it upright.

kicad-cli frames a render from a fixed camera, so one zoom setting cannot suit
boards of different sizes: tight enough to look right on one board clips the
coin cell off another. Every figure in the documentation was cropped at some
edge. The fix is to render deliberately wide and trim here, which makes the
framing a property of the board rather than of a number someone guessed.

Two steps:

  trim   the transparent border is cut back to a fixed fraction of the board,
         so every figure carries the same visual margin whatever its subject

  stand  a board that comes out wider than tall is turned 90 degrees clockwise,
         so every figure is portrait and a top/bottom pair sits side by side in
         the documentation's two-column grid without being squeezed. The tags
         are already portrait and are left alone; this is what rights the bases
         and the prototype carriers.

Refuses to trim an image whose content already runs into the frame edge: that
means the render clipped the board, and trimming would quietly crop it further
instead of saying so.

    python3 fit_render.py <png> [<png> ...]
"""

import argparse
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - reported to whoever ran the build
    print("fit_render.py needs Pillow (python3 -m pip install Pillow)",
          file=sys.stderr)
    raise SystemExit(2)

# Margin around the board, as a fraction of its longest side.
MARGIN = 0.04


def fit(path, margin=MARGIN, rotate=True):
    """Trim and stand one render. Returns None, or a message on failure."""
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size

    box = im.getchannel("A").getbbox()
    if box is None:
        return f"{path}: nothing was drawn"

    left, top, right, bottom = box
    if left <= 0 or top <= 0 or right >= w or bottom >= h:
        return (f"{path}: the board runs into the frame edge, so the render "
                f"clipped it. Lower BOARD_RENDER_ZOOM and draw it again.")

    pad = int(round(max(right - left, bottom - top) * margin))
    im = im.crop((max(left - pad, 0), max(top - pad, 0),
                  min(right + pad, w), min(bottom + pad, h)))

    if rotate and im.width > im.height:
        im = im.transpose(Image.ROTATE_270)   # PIL counts anticlockwise

    im.save(path)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--margin", type=float, default=MARGIN,
                    help=f"margin as a fraction of the board (default {MARGIN})")
    ap.add_argument("--no-rotate", action="store_true",
                    help="trim only; leave a landscape board lying down")
    args = ap.parse_args()

    bad = [m for m in (fit(p, args.margin, not args.no_rotate)
                       for p in args.images) if m]
    for m in bad:
        print("ERROR " + m, file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
