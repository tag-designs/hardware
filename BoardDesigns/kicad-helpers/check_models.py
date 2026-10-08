#!/usr/bin/env python3
"""Check that every 3D model a board references can actually be found.

kicad-cli says nothing about a model it cannot load. It draws it as nothing and
reports success, so a board can lose a quarter of its parts and the build stays
green -- which is what happened to tagbase-v7, and to six parts across the tag
boards when a user-defined path variable went stale in October.

Rendering in CI makes that worse, because nobody is looking at the output. This
is the guard: it resolves every `(model ...)` path against the filesystem and
fails if one is missing, before any rendering happens. Pure Python, no KiCad.

A reference is only safe if it goes through ${KIPRJMOD}, which is relative to
the board. An absolute path resolves only on the machine that wrote it.
${KICAD10_3DMODEL_DIR} resolves where KiCad is installed and not necessarily in
a container, and a user-defined variable such as ${TAG_LIBRARIES} resolves only
where someone has defined it -- and points at nothing if the tree is later
reorganized, which is exactly how six models were lost without a word.

--fix repairs what it can. KiCad writes an absolute path whenever a model is
picked through the file dialog rather than reached through a configured path
variable, and the shared library sits outside every board's project directory,
so no variable covers it and there is nothing for KiCad to substitute. That is
not a mistake made only once. --fix rewrites such a reference relative to the
board, which needs no configuration on any machine and so survives a clone and
a container.

    python3 check_models.py [--repo <hardware root>] [--fix]
"""

import argparse
import os
import re
import sys
from pathlib import Path

SUBDIR = re.compile(r"^\s*add_subdirectory\(([^)]+)\)", re.M)
MODEL = re.compile(r'\(model\s+"?([^"\n)]+)"?')
VAR = re.compile(r"^\$\{([A-Za-z0-9_]+)\}")


def classify(ref, board_dir):
    """Return (ok, why). ok is True when this reference resolves portably."""
    m = VAR.match(ref)
    if not m:
        return False, "an absolute path, which resolves only on the machine that wrote it"
    if m.group(1) != "KIPRJMOD":
        return False, f"${{{m.group(1)}}} is not guaranteed outside a workstation"
    path = Path(os.path.normpath(ref.replace("${KIPRJMOD}", str(board_dir))))
    if not path.is_file():
        return False, "no such file"
    return True, None


def portable(ref, board_dir, repo, library):
    """The ${KIPRJMOD} form of ref, or None if it cannot be placed.

    An absolute path that lands inside this repository is simply made relative.
    One that does not -- because it was written on another machine, which is
    what a clone or a container sees -- is looked up in the shared library by
    file name, as is a reference through a variable only that machine defines.
    """
    candidate = None
    if ref.startswith("/") and Path(ref).is_file():
        candidate = Path(ref)
    else:
        # Either a path absolute on somebody else's machine -- which is what a
        # clone or a container sees -- or a variable only that machine defines.
        # Both are placed by file name against the shared library.
        byname = library / ref.rsplit("/", 1)[-1]
        if byname.is_file():
            candidate = byname
    if candidate is None or not candidate.is_file():
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        return None                     # outside the repository; not ours to place
    rel = os.path.relpath(resolved, board_dir)
    return "${KIPRJMOD}/" + rel.replace(os.sep, "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None)
    ap.add_argument("--fix", action="store_true",
                    help="rewrite references that point outside the repository "
                         "so they go through ${KIPRJMOD}")
    args = ap.parse_args()

    repo = args.repo or Path(__file__).resolve().parents[2]
    bd = repo / "BoardDesigns"
    library = (bd / "kicad_libraries" / "3d_models").resolve()
    top = (bd / "CMakeLists.txt").read_text()

    boards = total = 0
    bad = []
    fixed = []

    for rel in SUBDIR.findall(top):
        d = (bd / rel.strip()).resolve()
        pcb = d / f"{d.name}.kicad_pcb"
        if not pcb.exists():
            continue
        boards += 1

        text = pcb.read_text()
        changed = False
        for ref in sorted(set(MODEL.findall(text))):
            total += 1
            ok, why = classify(ref, d)
            if ok:
                continue
            if args.fix:
                better = portable(ref, d, repo, library)
                if better and better != ref:
                    text = text.replace(ref, better)
                    changed = True
                    fixed.append((d.name, ref, better))
                    continue
            bad.append((d.name, ref, why))
        if changed:
            pcb.write_text(text)

    print(f"{boards} boards, {total} distinct model references")

    for name, ref, better in fixed:
        print(f"fixed {name}\n        {ref}\n     -> {better}")
    for name, ref, why in bad:
        print(f"FAIL {name}: {why} -- {ref}")

    if bad:
        print(f"\n{len(bad)} references would be drawn as nothing, silently."
              + ("" if args.fix else " Try --fix."))
        return 1
    if fixed:
        print(f"\n{len(fixed)} rewritten; every model now resolves inside the "
              f"repository")
        return 0
    print("every model resolves inside the repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
