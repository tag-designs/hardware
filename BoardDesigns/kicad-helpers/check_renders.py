#!/usr/bin/env python3
"""Check that the committed board renders match the committed layouts.

The renders under docs/src/images/boards are produced by kicad-cli and then
committed, because the workflow that publishes the hardware site has no KiCad
in it. That arrangement has one failure mode: a layout is edited and the images
are not redrawn, so the documentation shows a board that no longer exists.

This answers that without KiCad. Each time CMake renders a board it writes
BoardDesigns/.render-stamps/<board>.sha256, holding the hash of the .kicad_pcb
it drew from. Hashing the board again and comparing says whether the pictures
are current -- a file comparison, not an image comparison, so there is nothing
to go flaky.

The board list is read from the CMake files rather than repeated here, so this
cannot drift from what actually gets rendered.

    python3 check_renders.py [--repo <hardware root>]

Exit status is 0 when everything agrees, 1 otherwise.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

SUBDIR = re.compile(r"^\s*add_subdirectory\(([^)]+)\)", re.M)
RENDER = re.compile(r"^\s*add_board_renders(_top)?\(\s*([^)\s]+)\s*\)", re.M)


def boards(board_designs):
    """Yield (name, pcb path, [expected render names]) for every rendered board."""
    top = (board_designs / "CMakeLists.txt").read_text()
    for rel in SUBDIR.findall(top):
        d = board_designs / rel.strip()
        cml = d / "CMakeLists.txt"
        if not cml.exists():
            yield None, d, ["no CMakeLists.txt"]
            continue
        for top_only, name in RENDER.findall(cml.read_text()):
            sides = ["top"] if top_only else ["top", "bottom"]
            yield name, d / f"{name}.kicad_pcb", sides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None,
                    help="hardware repository root (default: inferred)")
    args = ap.parse_args()

    repo = args.repo or Path(__file__).resolve().parents[2]
    bd = repo / "BoardDesigns"
    renders = repo / "docs" / "src" / "images" / "boards"
    stamps = bd / ".render-stamps"

    problems = []
    unstamped = []
    claimed = set()
    checked = 0

    for name, pcb, sides in boards(bd):
        if name is None:
            problems.append(f"{pcb}: {sides[0]}")
            continue
        checked += 1
        if not pcb.exists():
            problems.append(f"{name}: no layout at {pcb.relative_to(repo)}")
            continue

        for side in sides:
            img = renders / f"{name}-{side}.png"
            claimed.add(img.name)
            if not img.exists():
                problems.append(f"{name}: missing render {img.name}")

        stamp = stamps / f"{name}.sha256"
        if not stamp.exists():
            unstamped.append(name)
            continue

        recorded = stamp.read_text().split()[0]
        actual = hashlib.sha256(pcb.read_bytes()).hexdigest()
        if recorded != actual:
            problems.append(
                f"{name}: layout has changed since its renders were drawn "
                f"(stamp {recorded[:12]}, layout {actual[:12]})")

    if renders.is_dir():
        for img in sorted(renders.glob("*.png")):
            if img.name not in claimed:
                problems.append(
                    f"{img.name}: render belongs to no board in the CMake files")

    print(f"{checked} boards checked")

    if unstamped:
        print()
        print("No render stamp for: " + ", ".join(sorted(unstamped)))
        print("Nothing has been rendered since stamping was introduced. Run")
        print("  cmake -S BoardDesigns -B build-boards")
        print("  cmake --build build-boards --target board-renders")
        print("and commit the stamps alongside the images.")

    if problems:
        print()
        for p in problems:
            print("FAIL " + p)
        return 1

    if unstamped:
        return 1

    print("renders are current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
