"""Activity-detector tilt stand: parameters and 2-D plate geometry.

Single source of truth for both outputs:

    python3 make_plates.py            # laser-cut DXF (in and mm) + SVG previews
    freecadcmd build_model.py         # FreeCAD assembly, STEP, tilt sweep

Pure Python, no dependencies, so FreeCAD's interpreter can import it too.

World frame (mm): z = 0 is the base-plate top, x is the servo output axis
(horn side +x), y completes a right-handed frame. The servo body is centred
on the origin in x and y. The tagbase tilts about the line y = 0, z = AXIS_Z.

Sources for every number are in DESIGN-NOTES.md; values marked VERIFY there
are inferred, not read off a drawing.
"""
import math
import os
import re

IN = 25.4
HERE = os.path.dirname(os.path.abspath(__file__))
TAGBASE_PCB = os.path.join(HERE, "../../BoardDesigns/Bases/tagbase-v7/tagbase-v7.kicad_pcb")

# --- stock -------------------------------------------------------------------
PLEX_T = 0.125 * IN            # nominal 1/8"; cast acrylic runs +-10%

# 2-56 press-in insert, McMaster 94615A111 (E-Z LOK 260-002BR): 0.156" long,
# flange 0.187" x 0.020", 1/8" hole. Laser at the multicharger's
# (0.125 - 0.007)" and drill to 1/8" after cutting.
INSERT_LASER_D = (0.125 - 0.007) * IN
INSERT_FINAL_D = 0.125 * IN
INSERT_LEN = 0.156 * IN
INSERT_FLANGE_D = 0.187 * IN
INSERT_FLANGE_T = 0.020 * IN
# 2-56 clearance, cut to size. Generous (0.106", #36) because the bracket
# hole positions come from a vendor drawing, not a measured part.
CLEAR_D = 0.106 * IN
# 2-56 82-degree flat head, for the adapter-to-U screws: J101's pogo tails and
# case screws sit over them, so the plate top there must be flush.
CSK_D = 0.172 * IN

# Nylon spacers. Tagbase: 1/16", as on the multicharger. Its one tall
# bottom-side lead is J1 (JST-XH), 1.8 mm in the KiCad model and over the
# adapter plate in both orientations: trim it if it touches. BusLinker: 1/8",
# for its untrimmed DC-jack and screw-terminal leads.
TAG_SPACER = 0.0625 * IN
LINKER_SPACER = 0.125 * IN
SPACER_OD = 0.1875 * IN
FOOT_H = 0.25 * IN             # rubber feet, for the model only
FOOT_D = 0.5 * IN

# --- Hiwonder brackets (vendor drawings, mm) ---------------------------------
# Both brackets carry the horn pattern: 8 holes on a 14 mm circle at 45 deg.
# Bottom bracket: all eight are 2.0. U bracket base: diagonals 3.0, on-axis
# 2.0, plus a 7.0 centre hole.
RING_R = 7.0
RING_DIAG = [(sx * 5.0, sy * 5.0) for sx in (-1, 1) for sy in (-1, 1)]
RING_AXIAL = [(7.0, 0.0), (-7.0, 0.0), (0.0, 7.0), (0.0, -7.0)]
BRACKET_T = 2.0                # U bracket, from the drawing
# Bottom bracket: thin sheet, and its 2.0 holes are too small to pass 2-56,
# too big to tap, and under the servo anyway. So it is cut in half across
# the floor and each half turned 180 deg about z: two L-angles whose flanges
# still hold the servo's horn and back faces but whose floor tabs now point
# outward, clear of the servo, screwed down from the top into inserts.
BOT_T = 1.0                    # VERIFY: sheet thickness (only the model uses it)
BOT_BRKT = dict(x=35.0, y=25.0, h=14.0)          # outside, x spans the flanges
# Tab inserts go in flange down (the screw pulls them up), so their bodies
# stand proud of the plate top by TAB_LIFT and the tabs sit on them. The
# servo stands on a shim of SHIM_T so its holes meet the flange holes as they
# did when it sat on the bracket floor. In practice: shim until they line up.
TAB_LIFT = INSERT_LEN - INSERT_FLANGE_T - PLEX_T
SHIM_T = BOT_T + TAB_LIFT
TAB_LEN = BOT_BRKT["x"] / 2    # each half's floor, flange face to the cut
TAB_INSERTS = [(sx * 24.0, sy * 7.0) for sx in (-1, 1) for sy in (-1, 1)]
TAB_CLEAR_D = 0.120 * IN       # #31, drilled through the tab via the 0.118" pilot
U_BRKT = dict(x=40.0, y=22.0, h=38.0, axis_to_base=34.0, tip_below_axis=4.0,
              bend_r=3.0)      # VERIFY: outer bend radius, from the photos

# --- LX-16A (Hiwonder: 45.22 x 24.72 x 36.3 overall) --------------------------
SERVO_H = 45.22                # z
SERVO_W = 24.72                # y
SERVO_D = BOT_BRKT["x"] - 2 * BOT_T       # x, body between the bracket flanges
HORN_PROUD = 2.5               # VERIFY: horn face beyond body, +x
BEARING_PROUD = U_BRKT["x"] - 2 * BRACKET_T - SERVO_D - HORN_PROUD  # -x; U inner is 36
SHAFT_FROM_TOP = 11.5          # VERIFY: output axis below servo top
HORN_D = 20.0                  # VERIFY

AXIS_Z = SHIM_T + SERVO_H - SHAFT_FROM_TOP
U_CX = (HORN_PROUD - BEARING_PROUD) / 2      # U centre, toward the horn
U_BASE_TOP = AXIS_Z + U_BRKT["axis_to_base"]
ADAPTER_TOP = U_BASE_TOP + PLEX_T
TAGBASE_BOTTOM = ADAPTER_TOP + INSERT_FLANGE_T + TAG_SPACER   # spacers sit on the flanges

# --- BusLinker V3.0 (Hiwonder: 42 x 33 x 15, holes 36 x 28) -------------------
# Placed on the -x side, clear of the swept volume, servo ports facing +x and
# USB-C / DC jack facing the plate edge. Long side along y.
LINKER = dict(cx=-55.0, cy=0.0, lx=33.0, ly=42.0, hx=28.0, hy=36.0, h=15.0,
              hole_d=3.0)     # holes and 28 x 36 centres measured by the designer, 2026-10-19

# --- plates ------------------------------------------------------------------
CORNER_R = 0.2 * IN            # as the multicharger
BASE = dict(x0=-85.0, x1=65.0, y0=-60.0, y1=60.0)
FOOT_INSET = 10.0
# Adapter: a cross, one arm per tagbase hole pattern, so each arm only spans
# its own four holes. A full square reaches J1's leads in both orientations.
ARM_HALF_W = 14.5              # across the arm: holes at 9.5
ARM_HALF_L = 25.5              # along the arm: holes at 21
INNER_R = 3.0                  # concave corners of the cross


def tagbase_holes():
    """H1-H4 of tagbase-v7 relative to their centroid, board frame (+y up).

    Also returns the board outline extents in the same frame, so the model
    and the overhang checks use the real board rather than copied numbers.
    """
    t = open(TAGBASE_PCB).read()
    holes = []
    for m in re.finditer(r'\(footprint "MountingHole:[^"]+"\s*\(layer "F.Cu"\)', t):
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", t[m.end():m.end() + 400])
        holes.append((float(at.group(1)), float(at.group(2))))
    assert len(holes) == 4, holes
    cx = sum(h[0] for h in holes) / 4
    cy = sum(h[1] for h in holes) / 4
    xs, ys = [], []
    for g in re.finditer(r'\((?:gr_line|gr_arc)\s+(.*?)\(layer "Edge.Cuts"\)', t, re.S):
        for x, y in re.findall(r"\((?:start|mid|end) ([-\d.]+) ([-\d.]+)\)", g.group(1)):
            xs.append(float(x))
            ys.append(float(y))
    rel = sorted((x - cx, cy - y) for x, y in holes)
    ext = (min(xs) - cx, max(xs) - cx, cy - max(ys), cy - min(ys))
    return rel, ext, (cx, cy)


def board_to_world(orient):
    """Map board-frame (x, y) about the hole centroid to adapter-plate (x, y).

    A: board long axis along the tilt axis; the USB end points +x and the
       short (50.8 mm) width swings, so it clears the base plate at +-90 deg.
    B: rotated 90 deg; the long overhang swings (+y). Smaller tilt range.
    """
    if orient == "A":
        return lambda x, y: (y, -x)
    return lambda x, y: (x, y)


def plate_holes():
    """Every hole in both plates: (plate, x, y, laser_d, final_d, role)."""
    out = []
    # Base plate.
    for x, y in TAB_INSERTS:
        out.append(("base", x, y, INSERT_LASER_D, INSERT_FINAL_D,
                    "bracket tab insert, flange down; pilot guides #31 into the tab"))
    L = LINKER
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(("base", L["cx"] + sx * L["hx"] / 2, L["cy"] + sy * L["hy"] / 2,
                        INSERT_LASER_D, INSERT_FINAL_D, "BusLinker insert, flange up"))
    for x in (BASE["x0"] + FOOT_INSET, BASE["x1"] - FOOT_INSET):
        for y in (BASE["y0"] + FOOT_INSET, BASE["y1"] - FOOT_INSET):
            out.append(("base", x, y, INSERT_LASER_D, INSERT_FINAL_D, "foot insert (optional), flange up"))
    # Adapter plate, in its own frame (centred on the U ring).
    for x, y in RING_DIAG:
        out.append(("adapter", x, y, CLEAR_D, CLEAR_D, "U bracket, 2-56 flat head countersunk from top, nut inside U"))
    rel, _, _ = tagbase_holes()
    for orient in ("A", "B"):
        f = board_to_world(orient)
        for bx, by in rel:
            x, y = f(bx, by)
            out.append(("adapter", x, y, INSERT_LASER_D, INSERT_FINAL_D,
                        "tagbase insert %s, flange up" % orient))
    return out


def _corner_polygon(plate):
    """Corner vertices, counter-clockwise, with a fillet radius for each."""
    if plate == "base":
        x0, y0, x1, y1 = BASE["x0"], BASE["y0"], BASE["x1"], BASE["y1"]
        return [((x0, y0), CORNER_R), ((x1, y0), CORNER_R), ((x1, y1), CORNER_R), ((x0, y1), CORNER_R)]
    w, l, R, r = ARM_HALF_W, ARM_HALF_L, CORNER_R, INNER_R
    return [((-w, -l), R), ((w, -l), R), ((w, -w), r), ((l, -w), R), ((l, w), R), ((w, w), r),
            ((w, l), R), ((-w, l), R), ((-w, w), r), ((-l, w), R), ((-l, -w), R), ((-w, -w), r)]


def outline(plate):
    """Closed outline as ("line", x0, y0, x1, y1) and ("arc", cx, cy, r, a0, a1).

    Arcs run counter-clockwise from a0 to a1 (degrees), as in DXF. Every
    corner is a right angle, so its fillet centre is P - r*d_in + r*d_out.
    """
    v = _corner_polygon(plate)
    n = len(v)
    unit = lambda a, b: ((b[0] - a[0]) / math.hypot(b[0] - a[0], b[1] - a[1]),
                         (b[1] - a[1]) / math.hypot(b[0] - a[0], b[1] - a[1]))
    tang = []
    for i in range(n):
        (p, r), prev, nxt = v[i], v[i - 1][0], v[(i + 1) % n][0]
        di, do = unit(prev, p), unit(p, nxt)
        t_in = (p[0] - r * di[0], p[1] - r * di[1])
        t_out = (p[0] + r * do[0], p[1] + r * do[1])
        c = (t_in[0] + r * do[0], t_in[1] + r * do[1])
        left = di[0] * do[1] - di[1] * do[0] > 0      # convex corner of a CCW outline
        ang = lambda t: math.degrees(math.atan2(t[1] - c[1], t[0] - c[0])) % 360
        a0, a1 = (ang(t_in), ang(t_out)) if left else (ang(t_out), ang(t_in))
        tang.append((t_in, t_out, ("arc", c[0], c[1], r, a0, a1)))
    segs = []
    for i in range(n):
        segs.append(tang[i][2])
        a, b = tang[i][1], tang[(i + 1) % n][0]
        segs.append(("line", a[0], a[1], b[0], b[1]))
    return segs


def outline_points(plate, step=0.1):
    """The outline sampled as a closed polyline, for the checks."""
    pts = []
    for s in outline(plate):
        if s[0] == "line":
            _, x0, y0, x1, y1 = s
            k = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            pts += [(x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k) for i in range(k)]
        else:
            _, cx, cy, r, a0, a1 = s
            span = (a1 - a0) % 360
            k = max(2, int(math.radians(span) * r / step))
            pts += [(cx + r * math.cos(math.radians(a0 + span * i / k)),
                     cy + r * math.sin(math.radians(a0 + span * i / k))) for i in range(k)]
    return pts


def extents(plate):
    pts = outline_points(plate, 1.0)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def inside(pts, x, y):
    n, c = len(pts), False
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i - 1]
        if (y0 > y) != (y1 > y) and x < x0 + (x1 - x0) * (y - y0) / (y1 - y0):
            c = not c
    return c


def check():
    """Geometric sanity checks on the plates; raises on failure."""
    holes = plate_holes()
    for plate in ("base", "adapter"):
        pts = outline_points(plate)
        hs = [h for h in holes if h[0] == plate]
        for _, x, y, _, d, role in hs:
            assert inside(pts, x, y), (plate, role, x, y)
            edge = min(math.hypot(px - x, py - y) for px, py in pts) - d / 2
            assert edge >= 2.5, "%s %s at (%.2f, %.2f): %.2f mm to edge" % (plate, role, x, y, edge)
        for i, a in enumerate(hs):
            for b in hs[i + 1:]:
                web = math.hypot(a[1] - b[1], a[2] - b[2]) - (a[4] + b[4]) / 2
                assert web >= 1.5, "%s: %s / %s web %.2f mm" % (plate, a[5], b[5], web)
    # Countersinks of the U screws must clear the tagbase spacers.
    ad = [h for h in holes if h[0] == "adapter"]
    for u in [h for h in ad if h[5].startswith("U")]:
        for t in [h for h in ad if h[5].startswith("tagbase")]:
            gap = math.hypot(u[1] - t[1], u[2] - t[2]) - CSK_D / 2 - SPACER_OD / 2
            assert gap > 0.5, (u, t, gap)
    return True


if __name__ == "__main__":
    rel, ext, c = tagbase_holes()
    print("tagbase holes about centroid KiCad %s:" % (c,), rel)
    print("board extents x[%.2f, %.2f] y[%.2f, %.2f]" % ext)
    print("axis z %.2f, U centre x %.2f, U base top %.2f, adapter top %.2f, tagbase bottom %.2f"
          % (AXIS_Z, U_CX, U_BASE_TOP, ADAPTER_TOP, TAGBASE_BOTTOM))
    for h in plate_holes():
        print("%-8s %7.2f %7.2f  laser %.3f  final %.3f  %s" % h)
    print("checks pass" if check() else "")
