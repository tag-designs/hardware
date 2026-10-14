#!/usr/bin/env python3
"""UIUCTag: ADXL362 (U2) decoupling distance and far-end case room.

Run from the board directory:

    python3 analysis/helpers/u2_fit_check.py

Prints
  1. the nearest VIN capacitor pad to each U2 supply pin (pin 1 VDD I/O,
     pin 14 VS), in mm, with the capacitor's layer;
  2. the board outline, and U2's body (B.SilkS box, pin-1 tick excluded)
     and courtyard x-extent in case coordinates (x = KiCad x - centre, so -x
     is the far, non-pogo end -- see Mechanical/TAGCASE-PROCESS.md);
  3. the room a case has at the far end, as TAGCASE-PROCESS.md builds it:
     the base ledge the board rests on, from the board groove (edge + 0.038)
     to whichever reaches further out of the under-board pocket (U2 courtyard
     + 0.2) and the far harness slot (hole edge + 0.1); and the lid far block,
     0.25 in from the board edge and 0.25 clear of the first F.Cu courtyard.
     The BitPresTagBMP585 case, for comparison, has a 0.82 mm ledge and a
     1.75 mm far block.
"""
import math
import re
import sys
from pathlib import Path

PCB = Path("UIUCTag.kicad_pcb")
BOTTOM_PARTS_CLEARANCE = 0.2    # TAGCASE-PROCESS.md: pocket = B.Cu envelope + 0.2
GROOVE_CLEARANCE = 0.0015 * 25.4  # board groove: outline + 1.5 mil per edge
HOLE_RADIUS = 0.55               # J30x harness holes
SLOT_MARGIN = 0.1                # harness slot -x edge just past the holes
LID_PART_CLEARANCE = 0.25       # TAGCASE-PROCESS.md: lid far block keeps >= 0.25 clear
LID_FAR_BLOCK_HALF_WIDTH = 5.2 / 2


def tokenize(text):
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)


def parse(tokens):
    pos = 0

    def read():
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            node = []
            while tokens[pos] != ")":
                node.append(read())
            pos += 1
            return node
        return tok.strip('"')
    return read()


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def outline(board):
    xs, ys = [], []
    for kind in ("gr_line", "gr_arc"):
        for g in children(board, kind):
            if children(g, "layer")[0][1] != "Edge.Cuts":
                continue
            for pt in children(g, "start") + children(g, "end") + children(g, "mid"):
                xs.append(float(pt[1]))
                ys.append(float(pt[2]))
    return min(xs), max(xs), min(ys), max(ys)


def footprints(board):
    out = {}
    for fp in children(board, "footprint"):
        ref = [p[2] for p in children(fp, "property") if p[1] == "Reference"]
        if ref:
            out[ref[0]] = fp
    return out


def placement(fp):
    at = children(fp, "at")[0]
    rot = float(at[3]) if len(at) > 3 else 0.0
    return float(at[1]), float(at[2]), rot, children(fp, "layer")[0][1]


def to_board(fp, lx, ly):
    x, y, rot, _ = placement(fp)
    a = math.radians(-rot)
    return (x + lx * math.cos(a) - ly * math.sin(a),
            y + lx * math.sin(a) + ly * math.cos(a))


def pads(fp):
    for p in children(fp, "pad"):
        at = children(p, "at")[0]
        net = children(p, "net")
        name = (net[0][2] if len(net[0]) > 2 else net[0][1]) if net else None
        bx, by = to_board(fp, float(at[1]), float(at[2]))
        yield p[1], bx, by, name


def extent(fp, layer_suffix, centre, max_local=None):
    """Case-coordinate extent of a footprint's graphics on one layer.

    max_local drops segments reaching beyond that local |x| or |y|; used to
    keep U2's pin-1 silk tick (local x = -1.85) out of the body outline.
    """
    xs, ys = [], []
    for kind in ("fp_line", "fp_rect"):
        for g in children(fp, kind):
            if not children(g, "layer")[0][1].endswith(layer_suffix):
                continue
            pts = children(g, "start") + children(g, "end")
            if max_local and any(abs(float(c)) > max_local for pt in pts for c in pt[1:3]):
                continue
            for pt in pts:
                bx, by = to_board(fp, float(pt[1]), float(pt[2]))
                xs.append(bx - centre[0])
                ys.append(centre[1] - by)
    return (min(xs), max(xs), min(ys), max(ys)) if xs else None


def main():
    if not PCB.is_file():
        sys.exit(f"run from the board directory: {PCB} not found")
    board = parse(tokenize(PCB.read_text()))
    fps = footprints(board)
    u2 = fps["U2"]
    x0, x1, y0, y1 = outline(board)
    centre = ((x0 + x1) / 2, (y0 + y1) / 2)
    far_edge = x0 - centre[0]

    print("1. U2 supply-pin decoupling")
    for pin in ("1", "14"):
        _, ux, uy, net = next(p for p in pads(u2) if p[0] == pin)
        near = []
        for ref, fp in fps.items():
            if not ref.startswith("C"):
                continue
            for _, cx, cy, cnet in pads(fp):
                if cnet == net:
                    near.append((math.hypot(cx - ux, cy - uy), ref, placement(fp)[3]))
        near.sort()
        print(f"   U2.{pin} ({net}): " + ", ".join(f"{r} {l} {d:.2f} mm" for d, r, l in near[:3]))

    body = extent(u2, "SilkS", centre, max_local=1.6)   # 3.2 x 3.0 silk box, CC-16-4 body
    crt = extent(u2, "CrtYd", centre)
    print(f"2. Board {x1 - x0:.2f} x {y1 - y0:.2f} mm, centre KiCad ({centre[0]:.3f}, {centre[1]:.3f}); "
          f"far edge at case x = {far_edge:.2f}")
    print(f"   U2 body x[{body[0]:.2f}, {body[1]:.2f}]  courtyard x[{crt[0]:.2f}, {crt[1]:.2f}]")
    print(f"   body-to-edge {body[0] - far_edge:.2f} mm, courtyard-to-edge {crt[0] - far_edge:.2f} mm")

    print("3. Far-end case room")
    far_holes = [placement(fp)[0] - centre[0] for ref, fp in fps.items() if ref in ("J303", "J304")]
    slot_edge = sum(far_holes) / len(far_holes) - HOLE_RADIUS - SLOT_MARGIN
    groove = far_edge - GROOVE_CLEARANCE
    for label, pocket in (("U2 courtyard", crt[0]), ("U2 body", body[0])):
        inner = min(pocket - BOTTOM_PARTS_CLEARANCE, slot_edge)
        print(f"   base ledge, pocket from {label}: {inner - groove:.2f} mm "
              f"(groove {groove:.2f} to {inner:.2f}; slot edge {slot_edge:.2f})")
    first = None
    for ref, fp in sorted(fps.items()):
        if placement(fp)[3] != "F.Cu" or ref.startswith("J"):
            continue
        e = extent(fp, "CrtYd", centre)
        if e and e[2] < LID_FAR_BLOCK_HALF_WIDTH and e[3] > -LID_FAR_BLOCK_HALF_WIDTH:
            if first is None or e[0] < first[1]:
                first = (ref, e[0])
    block = (first[1] - LID_PART_CLEARANCE) - (far_edge + LID_PART_CLEARANCE)
    print(f"   lid far block (|y| <= {LID_FAR_BLOCK_HALF_WIDTH}): first F.Cu part {first[0]} at x = {first[1]:.2f}; "
          f"block x[{far_edge + LID_PART_CLEARANCE:.2f}, {first[1] - LID_PART_CLEARANCE:.2f}] = {block:.2f} mm")


if __name__ == "__main__":
    main()
