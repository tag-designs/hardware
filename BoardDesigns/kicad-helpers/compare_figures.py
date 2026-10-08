#!/usr/bin/env python3
"""Compare a set of generated figures against the committed ones.

For deciding whether a container produces the same figures a workstation does.
Byte comparison answers nothing here: the renders are raytraced and carry noise,
so two runs on the same machine already differ. What matters is whether the
same things were drawn.

Three signals, in the order they are worth reading:

  size     the trimmed image's dimensions are the board's own extent, because
           the trim crops to what was drawn. A model that failed to load, or a
           font that is missing, changes what the alpha channel covers and so
           changes the size. Equal sizes are strong evidence the same geometry
           was drawn; a difference of more than a pixel or two is worth looking
           at before anything else.

  pixels   mean absolute difference over a coarse grid, which averages the
           raytracing noise away. A few percent is noise. A large number with
           equal sizes usually means shading or lighting, not content.

  text     for the schematic PDFs, the extracted text compared word for word.
           This is where a missing font shows up, and it is exact rather than
           approximate.

    python3 compare_figures.py <generated dir> [--repo <hardware root>]

where <generated dir> holds docs/src/images/boards and docs/src/schematics as
the workflow artifact does.
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("compare_figures.py needs Pillow", file=sys.stderr)
    raise SystemExit(2)

GRID = 64          # coarse grid for the pixel comparison


def coarse_diff(a, b):
    """Mean absolute difference, 0..1, on a GRID x GRID grayscale downsample."""
    ga = a.convert("L").resize((GRID, GRID), Image.LANCZOS).getdata()
    gb = b.convert("L").resize((GRID, GRID), Image.LANCZOS).getdata()
    return sum(abs(x - y) for x, y in zip(ga, gb)) / (len(ga) * 255)


def flatten(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def pdf_words(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return out.stdout.split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("generated", type=Path)
    ap.add_argument("--repo", type=Path, default=None)
    args = ap.parse_args()

    repo = args.repo or Path(__file__).resolve().parents[2]
    issues = 0

    print("=== renders ===")
    print(f"{'image':42s} {'committed':>12s} {'generated':>12s} {'pixels':>8s}")
    here = repo / "docs" / "src" / "images" / "boards"
    there = args.generated / "docs" / "src" / "images" / "boards"
    for f in sorted(here.glob("*.png")):
        g = there / f.name
        if not g.exists():
            print(f"{f.name:42s} {'':>12s} {'MISSING':>12s}")
            issues += 1
            continue
        a, b = flatten(f), flatten(g)
        d = coarse_diff(a, b)
        flag = ""
        if a.size != b.size:
            flag = "  <-- SIZE"
            issues += 1
        elif d > 0.05:
            flag = "  <-- look"
            issues += 1
        print(f"{f.name:42s} {f'{a.size[0]}x{a.size[1]}':>12s} "
              f"{f'{b.size[0]}x{b.size[1]}':>12s} {d:>7.1%}{flag}")

    print("\n=== schematics ===")
    here = repo / "docs" / "src" / "schematics"
    there = args.generated / "docs" / "src" / "schematics"
    for f in sorted(here.glob("*.pdf")):
        g = there / f.name
        if not g.exists():
            print(f"{f.name:42s} MISSING")
            issues += 1
            continue
        wa, wb = pdf_words(f), pdf_words(g)
        if wa is None:
            print(f"{f.name:42s} (pdftotext unavailable)")
            continue
        if wa == wb:
            print(f"{f.name:42s} {len(wa)} words, identical")
        else:
            only_a = [w for w in wa if w not in set(wb)][:6]
            only_b = [w for w in wb if w not in set(wa)][:6]
            print(f"{f.name:42s} {len(wa)} -> {len(wb)} words  <-- TEXT DIFFERS")
            if only_a:
                print(f"    only in committed: {' '.join(only_a)}")
            if only_b:
                print(f"    only in generated: {' '.join(only_b)}")
            issues += 1

    print()
    if issues:
        print(f"{issues} figures worth looking at before trusting the container")
        return 1
    print("the container produced the same figures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
