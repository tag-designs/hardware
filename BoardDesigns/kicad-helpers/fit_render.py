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

  stand  a board that is not taller than it is wide is turned 90 degrees
         clockwise, so every figure is portrait and a top/bottom pair sits side
         by side in the documentation's two-column grid without being squeezed.
         The tags are already portrait and are left alone; this is what rights
         the bases, and the square prototype carriers with them.

Refuses to trim an image whose content already runs into the frame edge: that
means the render clipped the board, and trimming would quietly crop it further
instead of saying so. kicad-cli fits the board outline to the frame, so
anything overhanging it -- a coin cell, mostly -- is what runs off, and the
cure is a lower BOARD_RENDER_ZOOM, which pulls the camera back. A larger frame
does not help on its own: the board scales with it. Also warns when a board
comes within a few per cent of the frame, so the margin can be seen shrinking
before it is lost.

Writes somewhere other than it read when given --output, so the render goes to
a scratch file and only replaces the committed image once the trim has
succeeded. A clipped board then leaves the previous image untouched instead of
destroying it.

    python3 fit_render.py <png> [--output <png>]
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

# Warn below this much clearance, as a fraction of the frame. Low on purpose:
# a tall overhanging part eats most of the slack on its side even when the
# render is fine, so a generous threshold would fire on every board and be
# ignored. This is close enough to the edge to mean something.
SLACK_WARN = 0.03


def fit(path, out=None, margin=MARGIN, rotate=True):
    """Trim and stand one render. Returns None, or a message on failure."""
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size

    box = im.getchannel("A").getbbox()
    if box is None:
        return f"{path}: nothing was drawn"

    left, top, right, bottom = box
    edges = [name for name, clipped in (("left", left <= 0), ("top", top <= 0),
                                        ("right", right >= w),
                                        ("bottom", bottom >= h)) if clipped]
    if edges:
        return (f"{path}: the board runs off the {', '.join(edges)} of a "
                f"{w}x{h} frame, so the render clipped it. Lower "
                f"BOARD_RENDER_ZOOM and draw it again -- a bigger frame will "
                f"not help, the board scales with it.")

    slack = min(left, top, w - right, h - bottom) / max(w, h)
    if slack < SLACK_WARN:
        print(f"note: {path} clears a {w}x{h} frame by only {slack:.1%}; "
              f"lower BOARD_RENDER_ZOOM before it clips", file=sys.stderr)

    pad = int(round(max(right - left, bottom - top) * margin))
    im = im.crop((max(left - pad, 0), max(top - pad, 0),
                  min(right + pad, w), min(bottom + pad, h)))

    # >= and not >, so a square board turns too. The prototype carriers are all
    # 48.3 mm square, and left alone they came out in the one orientation
    # nobody asked for; the tags are clearly taller than wide and are untouched
    # either way.
    if rotate and im.width >= im.height:
        im = im.transpose(Image.ROTATE_270)   # PIL counts anticlockwise

    im.save(out or path)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--output", type=str, default=None,
                    help="write here instead of in place (one image only)")
    ap.add_argument("--margin", type=float, default=MARGIN,
                    help=f"margin as a fraction of the board (default {MARGIN})")
    ap.add_argument("--no-rotate", action="store_true",
                    help="trim only; leave a landscape board lying down")
    args = ap.parse_args()

    if args.output and len(args.images) != 1:
        ap.error("--output takes exactly one image")

    bad = [m for m in (fit(p, args.output, args.margin, not args.no_rotate)
                       for p in args.images) if m]
    for m in bad:
        print("ERROR " + m, file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
