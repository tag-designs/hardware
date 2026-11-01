#!/usr/bin/env python3
"""Print the board geometry a tag case needs, in case coordinates.

    python3 Mechanical/tools/board_geometry.py BoardDesigns/Tags/<board>/<board>.kicad_pcb

Case coordinates are board-centred: x = kicad_x - cx, y = cy - kicad_y (KiCad's
y runs down the screen; the case's runs up). +x should be the pogo/battery end;
if J201 comes out at negative x, the board is drawn the other way round and
every x needs negating.

Extents are courtyards where the footprint has one, else pads. They are what
sizes the under-board pocket (B.Cu), the lid blocks (F.Cu) and the harness
slots (J30x holes).
"""
import math
import re
import sys


def balanced(text, i):
    """Return the s-expression starting at text[i] == '('."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise ValueError("unbalanced s-expression")


def blocks(text, head, top_level=True):
    """Yield each s-expression starting with `head` (top level: one indent in).

    KiCad 7+ indents with a tab, KiCad 6 (e.g. BitTagv8) with two spaces.
    """
    key = re.compile((r"\n(?:\t|  )\(" if top_level else r"\(") + re.escape(head) + r"[\s)]")
    i = 0
    while True:
        m = key.search(text, i)
        if not m:
            return
        b = balanced(text, text.index("(", m.start()))
        yield b
        i = m.start() + len(b)


def nums(s):
    return [float(v) for v in s.split()]


def main(path):
    t = open(path).read()
    thickness = re.search(r"\(general\s*\(thickness ([\d.]+)\)", t)

    # Board outline from Edge.Cuts endpoints; zero-length strays are skipped.
    xs, ys = [], []
    for head in ("gr_line", "gr_arc", "gr_rect"):
        for g in blocks(t, head):
            if '(layer "Edge.Cuts")' not in g:
                continue
            ends = [nums(m) for m in re.findall(r"\((?:start|mid|end) ([^)]+)\)", g)]
            if len(ends) == 2 and ends[0] == ends[1]:
                continue
            for x, y in ends:
                xs.append(x)
                ys.append(y)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    print("Board %s: %.3f x %.3f mm, centre KiCad (%.3f, %.3f), thickness %s"
          % (path.split("/")[-1], max(xs) - min(xs), max(ys) - min(ys), cx, cy,
             thickness.group(1) if thickness else "?"))
    print()

    rows = []
    for f in blocks(t, "footprint"):
        name = re.search(r'\(footprint "([^"]+)"', f).group(1)
        layer = re.search(r'\(layer "([^"]+)"\)', f).group(1)
        at = nums(re.search(r"\(at ([^)]+)\)", f).group(1))
        # KiCad 7+: (property "Reference" ...); KiCad 6: (fp_text reference ...).
        ref = re.search(r'\((?:property "Reference"|fp_text reference) "([^"]+)"', f).group(1)
        ox, oy, rot = at[0], at[1], (at[2] if len(at) > 2 else 0.0)
        a = math.radians(rot)

        def xf(x, y):
            kx = ox + x * math.cos(a) + y * math.sin(a)
            ky = oy - x * math.sin(a) + y * math.cos(a)
            return kx - cx, cy - ky

        pts = []
        for head in ("fp_line", "fp_rect", "fp_poly"):
            for g in blocks(f, head, top_level=False):
                if not re.search(r'\(layer "[FB]\.CrtYd"\)', g):
                    continue
                for m in re.findall(r"\((?:start|end|xy) ([-\d.]+ [-\d.]+)\)", g):
                    pts.append(xf(*nums(m)))
        if not pts:
            for m in re.finditer(r'\(pad "[^"]*" \w+ \w+\s*\(at ([^)]+)\)\s*\(size ([^)]+)\)', f):
                pa, sz = nums(m.group(1)), nums(m.group(2))
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        pts.append(xf(pa[0] + sx * sz[0] / 2, pa[1] + sy * sz[1] / 2))
        if not pts:
            continue
        px, py = [p[0] for p in pts], [p[1] for p in pts]
        origin = (ox - cx, cy - oy)
        rows.append((layer, ref, name, origin, rot, min(px), max(px), min(py), max(py)))

    for side in ("F.Cu", "B.Cu"):
        sel = [r for r in rows if r[0] == side]
        print("%s  (ref, origin, rotation, x-extent, y-extent, footprint)" % side)
        for _, ref, name, o, rot, x0, x1, y0, y1 in sorted(sel, key=lambda r: r[1]):
            print("  %-5s (%6.2f,%6.2f) %4.0f  x[%6.2f,%6.2f] y[%6.2f,%6.2f]  %s"
                  % (ref, o[0], o[1], rot, x0, x1, y0, y1, name))
        if side == "B.Cu":
            parts = [r for r in sel if not r[1].startswith("J")]
            if parts:
                print("  B.Cu parts envelope (excluding J*): x[%.2f, %.2f] y[%.2f, %.2f]"
                      % (min(r[5] for r in parts), max(r[6] for r in parts),
                         min(r[7] for r in parts), max(r[8] for r in parts)))
        print()


if __name__ == "__main__":
    main(sys.argv[1])
