#!/usr/bin/env python3
"""Which 3D models does KiCad actually fail to load, per board?

Reading model paths out of a .kicad_pcb tells you what a reference *says*.  It
does not tell you whether it resolves: that depends on the KiCad version, on
path variables configured outside the repository, and -- as PresTag-v6 showed
-- possibly on whether you are in the GUI or the CLI.  A model that cannot be
found is drawn as nothing rather than reported as an error, so the only
authority is KiCad's own output while it renders.

This runs a throwaway low-quality render of each board and keeps what KiCad
says while doing it, then sets that beside the static path inventory so the two
can be compared.  Where they disagree, believe the log.

Usage:
    model_resolution.py <board-dir-or-pcb> [...]
    model_resolution.py ../Tags/*/

    model_resolution.py --self-test <board-dir-or-pcb>

Needs kicad-cli on PATH, or KICAD_CLI set to it.  Renders go to a temporary
directory and are deleted; nothing in the repository is touched.

--self-test first:  a silent run only means "no models failed" if this tool can
detect a failure at all.  --self-test copies a board to a temporary file, points
one of its models at a path that cannot exist, and renders that.  If the probe
stays silent on a deliberately broken board, then silence on a real one tells
you nothing, and the images themselves are the only check left.
"""
import os
import re
import subprocess
import sys
import tempfile
import pathlib
import collections

MODEL = re.compile(r'\(model\s+"([^"]+)"')
# KiCad words this differently across versions, so match on substance.
COMPLAINT = re.compile(r'(model|3d|\.wrl|\.step)', re.I)
INTERESTING = re.compile(r'(not found|cannot|could not|unable|fail|missing|unresolved|no such)', re.I)


def cli():
    return os.environ.get("KICAD_CLI") or "kicad-cli"


def boards(args):
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            yield from sorted(p.glob("*.kicad_pcb"))
        elif p.suffix == ".kicad_pcb":
            yield p


def static_inventory(pcb):
    """What the file claims, grouped by path prefix."""
    paths = MODEL.findall(pcb.read_text(errors="replace"))
    c = collections.Counter()
    for p in paths:
        m = re.match(r'(\$\{[A-Z0-9_]+\})', p)
        c[m.group(1) if m else ("ABSOLUTE" if p.startswith("/") else "bare")] += 1
    return len(paths), c


def probe(pcb, tmp):
    """Render once, cheaply, and keep whatever KiCad says."""
    out = pathlib.Path(tmp) / (pcb.stem + ".png")
    cmd = [cli(), "pcb", "render", "--quality", "basic",
           "--width", "400", "--height", "400",
           "--output", str(out), str(pcb)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        sys.exit(f"kicad-cli not found. Set KICAD_CLI to its path.\n  tried: {cli()}")
    except subprocess.TimeoutExpired:
        return ["<render timed out after 300s>"], False
    blob = (r.stdout or "") + (r.stderr or "")
    lines = [l.strip() for l in blob.splitlines() if l.strip()]
    notable = [l for l in lines if COMPLAINT.search(l) and INTERESTING.search(l)]
    # Keep every line if nothing matched the filters but the run failed anyway.
    if r.returncode != 0 and not notable:
        notable = lines
    return notable, r.returncode == 0


def self_test(pcb, tmp):
    """Break one model reference on purpose and see whether the probe notices."""
    text = pcb.read_text(errors="replace")
    m = MODEL.search(text)
    if not m:
        return None, "no model references to break"
    broken_path = "${KIPRJMOD}/__no_such_dir__/__no_such_model__.step"
    broken = text[:m.start(1)] + broken_path + text[m.end(1):]
    victim = pathlib.Path(tmp) / ("selftest-" + pcb.name)
    victim.write_text(broken)
    notable, ok = probe(victim, tmp)
    return notable, None


def main(args):
    if not args:
        sys.exit(__doc__)

    if args[0] == "--self-test":
        rest = args[1:]
        if not rest:
            sys.exit("--self-test needs a board to work from")
        tmp = tempfile.mkdtemp(prefix="model-selftest-")
        pcb = next(boards(rest), None)
        if pcb is None:
            sys.exit("no .kicad_pcb found")
        print(f"  Breaking one model reference in a scratch copy of {pcb.name} ...")
        notable, err = self_test(pcb, tmp)
        if err:
            sys.exit("  " + err)
        if notable:
            print(f"  DETECTED -- kicad-cli said {len(notable)} thing(s) about it:")
            for l in notable:
                print(f"      {l}")
            print("\n  So a silent run on a real board is meaningful.")
        else:
            print("  NOT DETECTED -- kicad-cli said nothing about a model that cannot exist.")
            print("\n  So this probe cannot tell 'everything resolved' from 'nothing is")
            print("  reported', and a silent run proves nothing. Compare rendered images")
            print("  instead: a part that vanishes between two renders is the real signal.")
        return
    tmp = tempfile.mkdtemp(prefix="model-probe-")
    total_complaints = 0
    for pcb in boards(args):
        n, c = static_inventory(pcb)
        notable, ok = probe(pcb, tmp)
        total_complaints += len(notable)
        print(f"\n=== {pcb.parent.name} ({pcb.name}) ===")
        print(f"  render exit: {'ok' if ok else 'FAILED'}")
        print(f"  static: {n} model references -- " +
              ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
        if notable:
            print(f"  KiCad reported {len(notable)} line(s) about models:")
            for l in notable:
                print(f"      {l}")
        else:
            print("  KiCad reported nothing about models while rendering.")
    print(f"\n  Total model complaints across all boards: {total_complaints}")
    print("  Silence here means every reference resolved on THIS machine, which")
    print("  is not the same as resolving from a fresh clone.")


if __name__ == "__main__":
    main(sys.argv[1:])
