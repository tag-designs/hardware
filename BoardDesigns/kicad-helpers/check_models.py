#!/usr/bin/env python3
"""Check that every 3D model a board references can actually be found.

kicad-cli says nothing about a model it cannot load. It draws it as nothing and
reports success, so a board can lose a quarter of its parts and the build stays
green -- which is exactly what happened to tagbase-v7, and to six parts across
the tag boards before that when a user-defined path variable went stale.

Rendering in CI makes that worse, because nobody is looking at the output. This
is the guard: it resolves every `(model ...)` path against the filesystem and
fails if one is missing, before any rendering happens. Pure Python, no KiCad.

A reference is only safe if it goes through ${KIPRJMOD}, which is relative to
the board. ${KICAD10_3DMODEL_DIR} resolves on a workstation with KiCad
installed and not necessarily in a container; a user-defined variable such as
${TAG_LIBRARIES} resolves only where someone has defined it. Both are reported.

    python3 check_models.py [--repo <hardware root>]
"""

import argparse
import os
import re
import sys
from pathlib import Path

SUBDIR = re.compile(r"^\s*add_subdirectory\(([^)]+)\)", re.M)
MODEL = re.compile(r'\(model\s+"?([^"\n)]+)"?')
VAR = re.compile(r"^\$\{([A-Za-z0-9_]+)\}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None)
    args = ap.parse_args()

    repo = args.repo or Path(__file__).resolve().parents[2]
    bd = repo / "BoardDesigns"
    top = (bd / "CMakeLists.txt").read_text()

    boards = 0
    total = 0
    external = []
    missing = []

    for rel in SUBDIR.findall(top):
        d = (bd / rel.strip()).resolve()
        pcb = d / f"{d.name}.kicad_pcb"
        if not pcb.exists():
            continue
        boards += 1
        for ref in sorted(set(MODEL.findall(pcb.read_text()))):
            total += 1
            m = VAR.match(ref)
            if not m:
                missing.append((d.name, ref, "not anchored to a variable"))
                continue
            if m.group(1) != "KIPRJMOD":
                external.append((d.name, ref, m.group(1)))
                continue
            path = Path(os.path.normpath(ref.replace("${KIPRJMOD}", str(d))))
            if not path.is_file():
                missing.append((d.name, ref, "no such file"))

    print(f"{boards} boards, {total} distinct model references")

    for name, ref, var in external:
        print(f"FAIL {name}: ${{{var}}} is not guaranteed outside a "
              f"workstation -- {ref}")
    for name, ref, why in missing:
        print(f"FAIL {name}: {why} -- {ref}")

    if external or missing:
        print(f"\n{len(external) + len(missing)} references would be drawn as "
              f"nothing, silently.")
        return 1

    print("every model resolves inside the repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
