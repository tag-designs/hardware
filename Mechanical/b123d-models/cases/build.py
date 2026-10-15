"""Build, report and fit-check the proving cases.

    ~/cq-env/bin/python -m cases.build [UIUCTag BitTagNG ...]
"""
import sys
import time
from pathlib import Path

from build123d import export_step, export_stl

from tagcase.case import TagCase
from tagcase.fit import FitCheck
from tagcase.kicad import read_board

from tagcase.parts import REPO

TAGS = REPO / "BoardDesigns" / "Tags"
OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

# One line per case: the board, its label, and anything that is a decision.
CASES = {
    "UIUCTag": lambda: TagCase(read_board(TAGS / "UIUCTag/UIUCTag.kicad_pcb"), label="UIUC"),
    "BitTagNG": lambda: TagCase(read_board(TAGS / "BitTagNG/BitTagNG.kicad_pcb"), label="BTNG"),
}


def main(names):
    ok = True
    for name in names or CASES:
        t = time.time()
        case = CASES[name]()
        print("\n" + case.report())
        for part in ("base", "lid", "lid_nb"):
            shape = getattr(case, part)
            stem = OUT / ("%s-%s" % (name, part.replace("_nb", "-nobattery")))
            export_step(shape, str(stem) + ".step")
            export_stl(shape, str(stem) + ".stl", tolerance=0.001, angular_tolerance=0.05)
        fit = FitCheck(case)
        ok &= fit.run()
        print(fit.table())
        fit.export(OUT / ("%s-assembly.step" % name))
        print("  (%.0fs)" % (time.time() - t))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
