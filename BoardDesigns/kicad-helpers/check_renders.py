#!/usr/bin/env python3
"""Check that the published board figures still match the committed designs.

The renders and schematic PDFs under docs/src are committed, because the
workflow that publishes the hardware site has no KiCad in it. That arrangement
has one failure mode: a design is edited and the figures are not regenerated,
so the documentation shows a board that no longer exists. Nothing reports it.

This answers it without KiCad. Each time CMake draws a board it writes a stamp
under BoardDesigns/.render-stamps holding the SHA-256 of what it drew from --
<board>.sha256 for the layout behind the renders, <board>.sch.sha256 for the
sheets behind the PDF. Hashing the sources again and comparing says whether the
figures are current: a file comparison, not an image comparison, so there is
nothing to go flaky and no rendering nondeterminism to threshold against.

The board list is read from the CMake files rather than repeated here, so this
cannot drift from what actually gets generated.

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
    """Yield (name, directory, [sides]) for every board CMake generates for."""
    top = (board_designs / "CMakeLists.txt").read_text()
    for rel in SUBDIR.findall(top):
        d = board_designs / rel.strip()
        cml = d / "CMakeLists.txt"
        if not cml.exists():
            yield None, d, ["no CMakeLists.txt"]
            continue
        for top_only, name in RENDER.findall(cml.read_text()):
            yield name, d, (["top"] if top_only else ["top", "bottom"])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_stamp(path):
    """{filename: hash} from a stamp file."""
    out = {}
    for line in path.read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            out[parts[1].strip()] = parts[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None,
                    help="hardware repository root (default: inferred)")
    args = ap.parse_args()

    repo = args.repo or Path(__file__).resolve().parents[2]
    bd = repo / "BoardDesigns"
    renders = repo / "docs" / "src" / "images" / "boards"
    schematics = repo / "docs" / "src" / "schematics"
    stamps = bd / ".render-stamps"

    problems = []
    unstamped = []
    claimed_png = set()
    claimed_pdf = set()
    checked = 0

    for name, d, sides in boards(bd):
        if name is None:
            problems.append(f"{d}: {sides[0]}")
            continue
        checked += 1

        # --- renders, against the layout --------------------------------
        pcb = d / f"{name}.kicad_pcb"
        for side in sides:
            img = renders / f"{name}-{side}.png"
            claimed_png.add(img.name)
            if not img.exists():
                problems.append(f"{name}: missing render {img.name}")

        if not pcb.exists():
            problems.append(f"{name}: no layout at {pcb.relative_to(repo)}")
        else:
            stamp = stamps / f"{name}.sha256"
            if not stamp.exists():
                unstamped.append(f"{name} (renders)")
            elif read_stamp(stamp).get(pcb.name) != sha256(pcb):
                problems.append(
                    f"{name}: the layout has changed since its renders were "
                    f"drawn")

        # --- schematic PDF, against every sheet --------------------------
        sheets = sorted(d.glob("*.kicad_sch"))
        if not sheets:
            continue
        pdf = schematics / f"{name}.pdf"
        claimed_pdf.add(pdf.name)
        if not pdf.exists():
            problems.append(f"{name}: missing schematic {pdf.name}")

        stamp = stamps / f"{name}.sch.sha256"
        if not stamp.exists():
            unstamped.append(f"{name} (schematic)")
        else:
            recorded = read_stamp(stamp)
            actual = {s.name: sha256(s) for s in sheets}
            if recorded != actual:
                added = sorted(set(actual) - set(recorded))
                gone = sorted(set(recorded) - set(actual))
                edited = sorted(k for k in set(actual) & set(recorded)
                                if actual[k] != recorded[k])
                detail = "; ".join(filter(None, [
                    "sheets added: " + ", ".join(added) if added else "",
                    "sheets removed: " + ", ".join(gone) if gone else "",
                    "sheets edited: " + ", ".join(edited) if edited else ""]))
                problems.append(
                    f"{name}: the drawing has changed since its PDF was "
                    f"exported ({detail})")

    for directory, claimed, what in ((renders, claimed_png, "render"),
                                     (schematics, claimed_pdf, "schematic")):
        if not directory.is_dir():
            continue
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.name not in claimed:
                problems.append(
                    f"{f.name}: {what} belongs to no board in the CMake files")

    print(f"{checked} boards checked")

    if unstamped:
        print()
        print("No stamp for: " + ", ".join(sorted(unstamped)))
        print("Nothing has been generated since stamping was introduced. Run")
        print("  cmake -S BoardDesigns -B build-boards")
        print("  cmake --build build-boards --target board-docs")
        print("and commit the stamps alongside the figures.")

    if problems:
        print()
        for p in problems:
            print("FAIL " + p)
        return 1

    return 0 if not unstamped else 1


if __name__ == "__main__":
    sys.exit(main())
