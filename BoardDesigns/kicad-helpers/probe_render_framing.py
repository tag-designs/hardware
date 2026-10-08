#!/usr/bin/env python3
"""Measure what actually controls kicad-cli's render framing.

Two guesses have now been wrong about this. The renders clip, and it is not
settled whether the lever is --zoom, the frame size, both or neither: every
measurement so far happened to be taken at the same frame height, so it could
not separate them.

This renders one board across a small matrix and reports the geometry it gets,
at --quality basic because only the numbers matter here. Read the table like
this:

  board width constant as the frame grows   -> scale is absolute; a bigger
                                               frame buys margin
  board width grows in step with the frame  -> the board is fitted to the
                                               frame; a bigger frame buys
                                               nothing and zoom is the only
                                               lever
  width changes with --zoom                 -> zoom works, and in which
                                               direction

    python3 probe_render_framing.py <board.kicad_pcb> [--kicad-cli <path>]
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

FRAMES = [1200, 2400]
ZOOMS = [None, "1", "2", "0.5", "0.25"]

DEFAULT_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def render(cli, board, out, frame, zoom):
    cmd = [cli, "pcb", "render", "--side", "top", "--rotate", "0,0,90",
           "--quality", "basic", "--width", str(frame), "--height", str(frame),
           "--background", "transparent", "--output", str(out), str(board)]
    if zoom is not None:
        cmd += ["--zoom", zoom]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stderr or r.stdout).strip().splitlines()[-1:] 


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", type=Path)
    ap.add_argument("--kicad-cli",
                    default=shutil.which("kicad-cli") or DEFAULT_CLI)
    args = ap.parse_args()

    if not Path(args.kicad_cli).exists():
        sys.exit(f"no kicad-cli at {args.kicad_cli}")

    print(f"board    {args.board}")
    print(f"cli      {args.kicad_cli}")
    print()
    print(f"{'frame':>7} {'--zoom':>8} {'image':>12} {'board px':>12} "
          f"{'board/frame':>12}  clipped")
    print("-" * 70)

    seen = []
    with tempfile.TemporaryDirectory() as tmp:
        for frame in FRAMES:
            for zoom in ZOOMS:
                out = Path(tmp) / "p.png"
                rc, tail = render(args.kicad_cli, args.board, out, frame, zoom)
                if rc != 0 or not out.exists():
                    print(f"{frame:>7} {str(zoom):>8}   failed: "
                          f"{' '.join(tail)[:40]}")
                    continue
                im = Image.open(out).convert("RGBA")
                W, H = im.size
                box = im.getchannel("A").getbbox()
                if box is None:
                    print(f"{frame:>7} {str(zoom):>8} {W}x{H:<7} nothing drawn")
                    continue
                l, t, r, b = box
                edges = "".join(s for s, c in (("L", l <= 0), ("T", t <= 0),
                                               ("R", r >= W), ("B", b >= H))
                                if c)
                print(f"{frame:>7} {str(zoom):>8} {f'{W}x{H}':>12} "
                      f"{f'{r-l}x{b-t}':>12} {(r-l)/W:>11.3f}  {edges or '-'}")
                seen.append((frame, zoom, (r - l) / W))
                out.unlink()

    print()
    base = {f: r for f, z, r in seen if z in (None, "1")}
    half = {f: r for f, z, r in seen if z == "0.5"}
    if base and half:
        shrink = [half[f] / base[f] for f in base if f in half]
        if shrink and sum(shrink) / len(shrink) < 0.9:
            print("--zoom below 1 pulls the camera back: it is the lever.")
        else:
            print("--zoom below 1 changes nothing: the camera is clamped at "
                  "fit, so the frame cannot be widened that way.")
    ratios = {z: [r for f, zz, r in seen if zz == z] for z in (None, "1")}
    flat = [r for v in ratios.values() for r in v]
    if len(set(round(r, 3) for r in flat)) == 1 and flat:
        print("board/frame ratio is identical at both frame sizes: the board "
              "is fitted to the frame, so a bigger frame buys no margin.")


if __name__ == "__main__":
    sys.exit(main())
