"""FreeCAD model of the tilt stand, plus fit and tilt-range checks.

    freecadcmd -c "import runpy; runpy.run_path('build_model.py', run_name='__main__')"

(`make model` does this.) Writes to out/:
  ../teststand.FCStd        Stand (static) and Rotor (tilting) App::Parts. Set
                            Rotor's placement angle to pose it; the axis is x
                            through (0, 0, AXIS_Z).
  teststand-assembly.step   the same, at 0 deg
  stl/*.stl                 meshes for render.py
  checks.txt                underside fit and tilt limits, also printed

Servo, brackets and BusLinker are envelopes from the vendor drawings, good
enough for clearance, not for appearance. The tagbase is KiCad's own 3D export
(kicad-cli, run here if out/tagbase-v7.step is missing).
"""
import math
import os
import subprocess
import sys

import FreeCAD as App
import Mesh
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
sys.path.insert(0, HERE)
import teststand as ts  # noqa: E402

OUT = os.path.join(HERE, "out")
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
POGO_STEP = os.path.join(HERE, "../../BoardDesigns/libraries/packages3D/mill-max-855-22-006-10-001101.step")
V = App.Vector
AXIS_P, AXIS_D = V(0, 0, ts.AXIS_Z), V(1, 0, 0)


def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def plate(name, z0, origin=(0, 0)):
    ox, oy = origin
    edges = []
    for seg in ts.outline(name):
        if seg[0] == "line":
            _, x0, y0, x1, y1 = seg
            edges.append(Part.LineSegment(V(x0 + ox, y0 + oy, z0), V(x1 + ox, y1 + oy, z0)).toShape())
        else:
            _, cx, cy, r, a0, a1 = seg
            c = Part.Circle(V(cx + ox, cy + oy, z0), V(0, 0, 1), r)
            a1 = a1 if a1 > a0 else a1 + 360
            edges.append(Part.ArcOfCircle(c, math.radians(a0), math.radians(a1)).toShape())
    w = Part.Wire(Part.__sortEdges__(edges))
    assert w.isClosed(), name
    s = Part.Face(w).extrude(V(0, 0, ts.PLEX_T))
    for p, x, y, _, d, role in ts.plate_holes():
        if p == name:
            s = s.cut(Part.makeCylinder(d / 2, ts.PLEX_T + 2, V(x + ox, y + oy, z0 - 1)))
            if "countersunk" in role:
                h = (ts.CSK_D - d) / 2 / math.tan(math.radians(41))
                s = s.cut(Part.makeCone(d / 2, ts.CSK_D / 2, h, V(x + ox, y + oy, z0 + ts.PLEX_T - h)))
    return s


def insert(x, y, z_face, flange_up):
    """A press-in insert seated with its flange on the face at z_face."""
    body = Part.makeCylinder(ts.INSERT_FINAL_D / 2, ts.INSERT_LEN - ts.INSERT_FLANGE_T,
                             V(x, y, z_face - (ts.INSERT_LEN - ts.INSERT_FLANGE_T) if flange_up else z_face))
    fz = z_face if flange_up else z_face - ts.INSERT_FLANGE_T
    fl = Part.makeCylinder(ts.INSERT_FLANGE_D / 2, ts.INSERT_FLANGE_T, V(x, y, fz))
    return body.fuse(fl)


def ring_holes(shape, z0, t, diag_d, axial_d, centre_d=None):
    for (x, y), d in [(p, diag_d) for p in ts.RING_DIAG] + [(p, axial_d) for p in ts.RING_AXIAL]:
        shape = shape.cut(Part.makeCylinder(d / 2, t + 2, V(x, y, z0 - 1)))
    if centre_d:
        shape = shape.cut(Part.makeCylinder(centre_d / 2, t + 2, V(0, 0, z0 - 1)))
    return shape


def static_parts():
    b = ts.BOT_BRKT
    parts = {"BasePlate": plate("base", -ts.PLEX_T)}
    feet = [Part.makeCylinder(ts.FOOT_D / 2, ts.FOOT_H, V(x, y, -ts.PLEX_T - ts.FOOT_H))
            for p, x, y, _, _, role in ts.plate_holes() if role.startswith("foot")]
    parts["Feet"] = Part.makeCompound(feet)
    # The uncut bracket on the plate, floor holes at the inserts drilled 1/8".
    sd = ts.SERVO_D / 2
    t = ts.BOT_T
    brk = box(-b["x"] / 2, -b["y"] / 2, 0, b["x"] / 2, b["y"] / 2, t)
    brk = ring_holes(brk, 0, t, ts.INSERT_FINAL_D, 2.1)
    for sx in (-1, 1):
        x0 = sx * b["x"] / 2 - (t if sx > 0 else 0)
        brk = brk.fuse(box(x0, -b["y"] / 2, 0, x0 + t, b["y"] / 2, b["h"]))
    parts["BottomBracket"] = brk
    parts["BracketScrews"] = Part.makeCompound(
        [Part.makeCylinder(ts.PAN_HEAD["d"] / 2, ts.PAN_HEAD["h"], V(x, y, t)) for x, y in ts.BRACKET_INSERTS])
    body = box(-sd, -ts.SERVO_W / 2, ts.SERVO_Z, sd, ts.SERVO_W / 2, ts.SERVO_Z + ts.SERVO_H)
    parts["LX16A"] = body
    # Horn and rear bearing ride with the shaft; they belong to the servo but
    # are excluded from the sweep (the U bracket is bolted to them).
    horn = Part.makeCylinder(ts.HORN_D / 2, ts.HORN_PROUD, V(sd, 0, ts.AXIS_Z), AXIS_D)
    brg = Part.makeCylinder(5.0, ts.BEARING_PROUD, V(-sd - ts.BEARING_PROUD, 0, ts.AXIS_Z), AXIS_D)
    parts["LX16A_horn"] = horn.fuse(brg)
    L = ts.LINKER
    z0 = ts.INSERT_FLANGE_T + ts.LINKER_SPACER
    holes = [(x, y) for p, x, y, _, _, role in ts.plate_holes() if role.startswith("BusLinker")]
    pcb = box(L["cx"] - L["lx"] / 2, L["cy"] - L["ly"] / 2, z0, L["cx"] + L["lx"] / 2, L["cy"] + L["ly"] / 2, z0 + 1.6)
    comp = box(L["cx"] - L["lx"] / 2 + 1, L["cy"] - L["ly"] / 2 + 1, z0 + 1.6,
               L["cx"] + L["lx"] / 2 - 1, L["cy"] + L["ly"] / 2 - 1, z0 + L["h"])
    for x, y in holes:
        pcb = pcb.cut(Part.makeCylinder(L["hole_d"] / 2, 4, V(x, y, z0 - 1)))
    parts["BusLinker"] = pcb.fuse(comp)
    parts["BusLinkerSpacers"] = Part.makeCompound(
        [Part.makeCylinder(ts.SPACER_OD / 2, ts.LINKER_SPACER, V(x, y, ts.INSERT_FLANGE_T)) for x, y in holes])
    parts["BaseInserts"] = Part.makeCompound(
        [insert(x, y, 0, True) if "flange up" in role else insert(x, y, -ts.PLEX_T, False)
         for p, x, y, _, _, role in ts.plate_holes() if p == "base" and "insert" in role])
    return parts


def tagbase_shape():
    step = os.path.join(OUT, "tagbase-v7.step")
    if not os.path.exists(step):
        subprocess.check_call([KICAD_CLI, "pcb", "export", "step", "--subst-models", "-f",
                               "-o", step, os.path.abspath(ts.TAGBASE_PCB)])
    s = Part.Shape()
    s.read(step)
    return Part.makeCompound([s, pogo_shape()])


def pogo_shape():
    """J101's Mill-Max 855 connector, which the board file carries hidden.

    Model frame as in b123d-models/tagcase/parts.py: pins along x, rows along
    z, plungers along +y, barrel shoulder (y = -4.4196) on the board top. Put
    it in the KiCad-export frame: footprint origin, board underside z = 0.
    """
    p = Part.Shape()
    p.read(POGO_STEP)
    m = App.Matrix(1, 0, 0, -3.3655,      # x: centre the pins
                   0, 0, -1, -1.4986,     # y = -z: centre the rows
                   0, 1, 0, 4.4196 + 1.6,  # z = y: shoulder on the board top
                   0, 0, 0, 1)
    p = p.transformGeometry(m)
    t = open(ts.TAGBASE_PCB).read()
    i = t.index('(footprint "tagbase:6pin_tagpoints_new_offset"')
    x, y = (float(v) for v in t[i:i + 600].split("(at ", 1)[1].split(")")[0].split()[:2])
    p.translate(V(x, -y, 0))
    return p


def place_tagbase(raw, orient):
    """KiCad STEP (x, -y kicad; board underside z = 0) to the rotor at 0 deg."""
    _, _, (cx, cy) = ts.tagbase_holes()
    s = raw.copy()
    s.translate(V(-cx, cy, 0))           # hole centroid to the origin, board frame +y up
    if orient == "A":
        s.rotate(V(0, 0, 0), V(0, 0, 1), -90)   # (x, y) -> (y, -x), as ts.board_to_world
    s.translate(V(0, 0, ts.TAGBASE_BOTTOM))
    return s


def rotor_parts(raw_tagbase):
    u = ts.U_BRKT
    t = ts.BRACKET_T
    cx = ts.U_CX
    zb = ts.U_BASE_TOP
    base = box(cx - u["x"] / 2, -u["y"] / 2, zb - t, cx + u["x"] / 2, u["y"] / 2, zb)
    base = ring_holes(base.translated(V(-cx, 0, 0)), zb - t, t, 2.2, 3.2, 8.0).translated(V(cx, 0, 0))
    arms = [box(x0, -u["y"] / 2, ts.AXIS_Z - u["tip_below_axis"], x0 + t, u["y"] / 2, zb)
            for x0 in (cx - u["x"] / 2, cx + u["x"] / 2 - t)]
    ub = base.fuse(arms).removeSplitter()
    bends = [e for e in ub.Edges if abs(e.BoundBox.ZMin - zb) < 1e-6 and abs(e.BoundBox.ZMax - zb) < 1e-6
             and e.BoundBox.XLength < 1e-6 and abs(abs(e.BoundBox.XMin - cx) - u["x"] / 2) < 1e-6]
    assert len(bends) == 2, bends
    parts = {"UBracket": ub.makeFillet(u["bend_r"], bends)}
    # The adapter plate is centred on the U ring, i.e. on the shaft line
    # (x = U_CX is only where the U is centred; its ring sits at x = U_CX).
    parts["AdapterPlate"] = plate("adapter", ts.U_BASE_TOP, (cx, 0))
    ad = [(x + cx, y, role) for p, x, y, _, _, role in ts.plate_holes() if p == "adapter"]
    parts["AdapterInserts"] = Part.makeCompound(
        [insert(x, y, ts.ADAPTER_TOP, True) for x, y, role in ad if "insert" in role])
    for orient in ("A", "B"):
        parts["TagSpacers" + orient] = Part.makeCompound(
            [Part.makeCylinder(ts.SPACER_OD / 2, ts.TAG_SPACER, V(x, y, ts.ADAPTER_TOP + ts.INSERT_FLANGE_T))
             for x, y, role in ad if role == "tagbase insert %s, flange up" % orient])
        tb = place_tagbase(raw_tagbase, orient)
        tb.translate(V(cx, 0, 0))
        parts["Tagbase" + orient] = tb
    return parts


def tagbase_envelope(orient):
    """Board plus top-side parts as one box, for the sweep (underside excluded)."""
    rel, (bx0, bx1, by0, by1), _ = ts.tagbase_holes()
    f = ts.board_to_world(orient)
    pts = [f(x, y) for x in (bx0, bx1) for y in (by0, by1)]
    xs, ys = [p[0] + ts.U_CX for p in pts], [p[1] for p in pts]
    # 12 mm above the board: the KiCad export's tallest part (10.1) plus a tag case lid.
    return box(min(xs), min(ys), ts.TAGBASE_BOTTOM, max(xs), max(ys), ts.TAGBASE_BOTTOM + 1.6 + 12)


def rotated(shape, deg):
    s = shape.copy()
    s.rotate(AXIS_P, AXIS_D, deg)
    return s


def tilt_limit(moving, static, sign):
    def hits(deg):
        m = rotated(moving, sign * deg)
        return [n for n, s in static.items() if m.common(s).Volume > 0.01]
    last = 0
    for deg in range(2, 182, 2):
        h = hits(deg)
        if h:
            lo, hi = last, deg
            while hi - lo > 0.25:
                mid = (lo + hi) / 2
                (lo, hi) = (lo, mid) if hits(mid) else (mid, hi)
            return lo, hits(hi)
        last = deg
    return 180, []


def main():
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    lines = []
    say = lambda s: (print(s), lines.append(s))
    st = static_parts()
    raw = tagbase_shape()
    ro = rotor_parts(raw)

    say("Axis at z = %.2f mm above the base plate; tagbase underside %.2f above the axis."
        % (ts.AXIS_Z, ts.TAGBASE_BOTTOM - ts.AXIS_Z))
    # 1. Real tagbase underside against the adapter plate and its inserts, at rest.
    for orient in ("A", "B"):
        tb = ro["Tagbase" + orient]
        bad = []
        for sol in tb.Solids:
            for n in ("AdapterPlate", "AdapterInserts"):
                v = sol.common(ro[n]).Volume
                if v > 1e-3:
                    bb = sol.BoundBox
                    bad.append("%s %.3f mm3 at (%.1f, %.1f), %.2f below board" %
                               (n, v, bb.Center.x, bb.Center.y, ts.TAGBASE_BOTTOM - bb.ZMin))
        say("Underside fit, orientation %s, %.2f mm spacer: %s" %
            (orient, ts.TAG_SPACER, "clear" if not bad else "; ".join(bad)))
        low = min(s.BoundBox.ZMin for s in tb.Solids)
        say("  lowest tagbase feature %.2f mm below the board (spacer %.2f)" % (ts.TAGBASE_BOTTOM - low, ts.TAG_SPACER))

    # 1a. The bracket screws' heads stand in the gap under the servo.
    v = st["BracketScrews"].common(st["LX16A"]).Volume
    say("Bracket screw heads under the servo: %s (gap %.2f, head %.2f)" %
        ("clear" if v < 1e-3 else "%.3f mm3 overlap" % v, ts.SERVO_GAP, ts.PAN_HEAD["h"]))
    # 1b. Inside the rotor: the plate must sit flat on the U base.
    for n in ("AdapterInserts",):
        v = ro[n].common(ro["UBracket"]).Volume
        say("%s against the U bracket: %s" % (n, "clear" if v < 1e-3 else "%.3f mm3 overlap" % v))
    # 2. Tilt range. Static obstacles exclude the horn; moving set is rigid.
    static = {k: st[k] for k in ("BasePlate", "BottomBracket", "LX16A", "BusLinker", "BusLinkerSpacers")}
    for orient in ("A", "B"):
        mov = Part.makeCompound([ro["UBracket"], ro["AdapterPlate"], ro["TagSpacers" + orient],
                                 tagbase_envelope(orient)])
        for sign, name in ((1, "+"), (-1, "-")):
            deg, by = tilt_limit(mov, static, sign)
            say("Tilt limit, orientation %s, %s direction: %.1f deg%s" %
                (orient, name, deg, (" (first contact: %s)" % ", ".join(by)) if by else ""))

    doc = App.newDocument("TestStand")
    stand = doc.addObject("App::Part", "Stand")
    rotor = doc.addObject("App::Part", "Rotor")
    for group, parts in ((stand, st), (rotor, ro)):
        for n, s in parts.items():
            o = doc.addObject("Part::Feature", n)
            o.Shape = s
            group.addObject(o)
            if n.endswith("B"):
                o.Visibility = False
    rotor.Placement = App.Placement(V(0, 0, 0), App.Rotation(AXIS_D, 0), AXIS_P)
    doc.recompute()
    doc.saveAs(os.path.join(HERE, "teststand.FCStd"))
    import Import
    Import.export([stand, rotor], os.path.join(OUT, "teststand-assembly.step"))

    for n, s in list(st.items()) + list(ro.items()):
        m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.1, AngularDeflection=0.3)
        m.write(os.path.join(OUT, "stl", n + ".stl"))
    open(os.path.join(OUT, "checks.txt"), "w").write("\n".join(lines) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
