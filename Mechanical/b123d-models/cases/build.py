"""Build, report and fit-check the tag cases.

    ~/cq-env/bin/python -m cases.build [--out DIR] [UIUCTag BitTagNG ...]
    ~/cq-env/bin/python -m cases.build --list     # name and board, for CMake

Exits non-zero if any fit requirement fails.
"""
import argparse
import sys
import time
from pathlib import Path

from build123d import export_step, export_stl

from dataclasses import replace  # noqa: F401  (for per-case design= overrides)

from tagcase.case import CaseDesign, TagCase  # noqa: F401
from tagcase.fit import FitCheck
from tagcase.kicad import read_board
from tagcase.parts import LIPO, REPO, SINGLE_PAIR, Pins  # noqa: F401  (tag_base=, pins=)

TAGS = REPO / "BoardDesigns" / "Tags"
OUT = Path(__file__).resolve().parent.parent / "out"     # default; make and CMake pass --out

# One line per case: its board, then the TagCase arguments -- the label and
# anything that is a decision rather than read from the board.
CASES = {
    "UIUCTag": (TAGS / "UIUCTag/UIUCTag.kicad_pcb", dict(label="UIUC")),
    "BitTagNG": (TAGS / "BitTagNG/BitTagNG.kicad_pcb", dict(label="BTNG")),
}


def make_case(name, out=OUT) -> TagCase:
    board, kwargs = CASES[name]
    return TagCase(read_board(board), cache=Path(out) / "cache", **kwargs)


def main(names, out=OUT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    unknown = [n for n in names if n not in CASES]
    if unknown:
        raise SystemExit("unknown case %s; known: %s" % (", ".join(unknown), ", ".join(CASES)))
    ok = True
    for name in names or CASES:
        t = time.time()
        case = make_case(name, out)
        print("\n" + case.report())
        for part in ("base", "lid", "lid_nb"):
            shape = getattr(case, part)
            stem = out / ("%s-%s" % (name, part.replace("_nb", "-nobattery")))
            export_step(shape, str(stem) + ".step")
            export_stl(shape, str(stem) + ".stl", tolerance=0.001, angular_tolerance=0.05)
        fit = FitCheck(case)
        ok &= fit.run()
        print(fit.table())
        fit.export(out / ("%s-assembly.step" % name))
        print("  (%.0fs)" % (time.time() - t))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="*", help="default: every case")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--list", action="store_true", help="print name<TAB>board per case and exit")
    a = ap.parse_args()
    if a.list:
        for name, (board, _) in CASES.items():
            print("%s\t%s" % (name, board))
        sys.exit(0)
    sys.exit(0 if main(a.cases, a.out) else 1)
