#!/usr/bin/env python3
"""Write the two 1/8" acrylic plates as DXF (inch and mm), SVG previews, and
1:1 printable PDFs for checking against the hardware before cutting.

    python3 make_plates.py [--out DIR]       # default: ./plates

Layers
  CUT        outline and 2-56 clearance holes, cut to final size (the four
             central adapter holes are then countersunk from the top)
  CUT_PILOT  insert holes at 0.118"; drill to 1/8" after cutting
  ENGRAVE    placement outlines and the tilt-axis marks (score, don't cut)

The inch DXFs match Acrylic/multicharger-acrylic.dxf, which is in inches.
"""
import argparse
import math
import os

import teststand as ts

LAYERS = {"CUT": 7, "CUT_PILOT": 1, "ENGRAVE": 5}   # ACI colours: white, red, blue


def entities(plate):
    """(layer, kind, data) in mm, plate frame."""
    e = [("CUT", seg[0], seg[1:]) for seg in ts.outline(plate)]
    for p, x, y, laser, final, role in ts.plate_holes():
        if p == plate:
            layer = "CUT" if laser == final else "CUT_PILOT"
            e.append((layer, "circle", (x, y, laser / 2)))

    def rect(cx, cy, w, h):
        a, b, c, d = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        return [("ENGRAVE", "line", s) for s in ((a, b, c, b), (c, b, c, d), (c, d, a, d), (a, d, a, b))]

    if plate == "base":
        e += rect(0, 0, ts.BOT_BRKT["x"], ts.BOT_BRKT["y"])
        L = ts.LINKER
        e += rect(L["cx"], L["cy"], L["lx"], L["ly"])
        # Tilt axis direction, beyond the bracket.
        e += [("ENGRAVE", "line", (22, 0, 32, 0)), ("ENGRAVE", "line", (-32, 0, -22, 0))]
    else:
        # Tilt axis (x) on the B arm ends; pattern keys: one tick on the A
        # arm (+y end), two on the B arm (-x end).
        a = ts.ARM_HALF_L
        e += [("ENGRAVE", "line", (a - 2.5, 0, a - 0.8, 0)),
              ("ENGRAVE", "line", (-a + 0.8, 0, -a + 2.5, 0))]
        e += [("ENGRAVE", "line", (-1, a - 1.5, 1, a - 1.5))]
        e += [("ENGRAVE", "line", (-a + 1.5, -6, -a + 1.5, -4)),
              ("ENGRAVE", "line", (-a + 2.7, -6, -a + 2.7, -4))]
    return e


def dxf(ents, scale, insunits):
    out = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009",
           "9", "$INSUNITS", "70", str(insunits), "0", "ENDSEC",
           "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(LAYERS))]
    for name, col in LAYERS.items():
        out += ["0", "LAYER", "2", name, "70", "0", "62", str(col), "6", "CONTINUOUS"]
    out += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    f = lambda v: "%.6f" % (v * scale)
    for layer, kind, d in ents:
        if kind == "line":
            out += ["0", "LINE", "8", layer, "10", f(d[0]), "20", f(d[1]), "11", f(d[2]), "21", f(d[3])]
        elif kind == "circle":
            out += ["0", "CIRCLE", "8", layer, "10", f(d[0]), "20", f(d[1]), "40", f(d[2])]
        else:
            out += ["0", "ARC", "8", layer, "10", f(d[0]), "20", f(d[1]), "40", f(d[2]),
                    "50", "%.3f" % d[3], "51", "%.3f" % d[4]]
    out += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(out) + "\n"


def svg(ents, plate):
    x0, y0, x1, y1 = ts.extents(plate)
    m = 4
    col = {"CUT": "#000", "CUT_PILOT": "#d00", "ENGRAVE": "#06c"}
    w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="%g %g %g %g">'
         % (w, h, x0 - m, -y1 - m, w, h), '<rect x="%g" y="%g" width="%g" height="%g" fill="#fff"/>'
         % (x0 - m, -y1 - m, w, h), '<g fill="none" stroke-width="0.25">']
    for layer, kind, d in ents:
        c = col[layer]
        if kind == "line":
            s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s"/>' % (d[0], -d[1], d[2], -d[3], c))
        elif kind == "circle":
            s.append('<circle cx="%g" cy="%g" r="%g" stroke="%s"/>' % (d[0], -d[1], d[2], c))
        else:
            cx, cy, r, a0, a1 = d
            p0 = (cx + r * math.cos(math.radians(a0)), -(cy + r * math.sin(math.radians(a0))))
            p1 = (cx + r * math.cos(math.radians(a1)), -(cy + r * math.sin(math.radians(a1))))
            s.append('<path d="M %g %g A %g %g 0 0 0 %g %g" stroke="%s"/>' % (p0 + (r, r) + p1 + (c,)))
    s += ["</g>", "</svg>"]
    return "\n".join(s) + "\n"


PT = 72 / 25.4                 # points per mm
PAGE = (612, 792)              # US Letter; content kept inside A4's width too


def _fmt(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def reference(plate):
    """Dashed outlines of the hardware, for laying the real parts on the print.

    (kind, data, label) in mm, plate frame.
    """
    r = []
    if plate == "base":
        for (x, y), d in [(p, 2.1) for p in ts.RING_DIAG + ts.RING_AXIAL]:
            r.append(("circle", (x, y, d / 2), None))
        r.append(("rect", (0, 0, ts.SERVO_D, ts.SERVO_W), None))
        L = ts.LINKER
        for sx in (-1, 1):
            for sy in (-1, 1):
                r.append(("circle", (L["cx"] + sx * L["hx"] / 2, L["cy"] + sy * L["hy"] / 2, L["hole_d"] / 2), None))
    else:
        u = ts.U_BRKT
        r.append(("rect", (0, 0, u["x"], u["y"]), None))
        for (x, y), d in [(p, 2.2) for p in ts.RING_DIAG] + [(p, 3.2) for p in ts.RING_AXIAL]:
            r.append(("circle", (x, y, d / 2), None))
        r.append(("circle", (0, 0, 4.0), None))
    return r


LABELS = {
    "bottom bracket insert": "bottom-bracket inserts (from below), Ø14 ring at 45°",
    "BusLinker insert": "BusLinker inserts, 28 × 36",
    "foot insert": "foot inserts (optional)",
    "U bracket": "U bracket, countersink from top",
    "tagbase insert A": "tagbase pattern A",
    "tagbase insert B": "tagbase pattern B",
}


# Where each hole group's label goes (mm, plate frame), and the hole a leader
# line runs to, if any: clear of the outlines.
LABEL_AT = {
    "base": {"bottom bracket insert": (-12, -26, (-4.95, -4.95)),
             "BusLinker insert": (-71, -27, None),
             "foot insert": (-77, 53, None)},
    "adapter": {"tagbase insert A": (31, 24, (9.5 + 2, 21)),
                "tagbase insert B": (31, 12, (21 + 2, 9.5)),
                "U bracket": (31, -4, (7 + 2, 0))},
}


def pdf(plate):
    """A one-page, 1:1 PDF of a plate with scale bars. Returns bytes."""
    x0, y0, x1, y1 = ts.extents(plate)
    ox = PAGE[0] / 2 - (x0 + x1) / 2 * PT
    oy = PAGE[1] - 90 - y1 * PT
    X = lambda x: ox + x * PT
    Y = lambda y: oy + y * PT
    ops = []

    def stroke(rgb, w=0.5, dash=None):
        ops.append("%s %s %s RG %s w %s d" % (_fmt(rgb[0]), _fmt(rgb[1]), _fmt(rgb[2]), _fmt(w),
                                              "[%s] 0" % " ".join(map(_fmt, dash)) if dash else "[] 0"))

    def line(xa, ya, xb, yb):
        ops.append("%s %s m %s %s l S" % (_fmt(X(xa)), _fmt(Y(ya)), _fmt(X(xb)), _fmt(Y(yb))))

    def arc_pts(cx, cy, r, a0, a1):
        """Bezier segments for a counter-clockwise arc, <= 90 deg each."""
        span = (a1 - a0) % 360 or 360
        n = int(math.ceil(span / 90))
        out = []
        for i in range(n):
            t0 = math.radians(a0 + span * i / n)
            t1 = math.radians(a0 + span * (i + 1) / n)
            k = 4 / 3 * math.tan((t1 - t0) / 4)
            p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
            p3 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
            p1 = (p0[0] - k * r * math.sin(t0), p0[1] + k * r * math.cos(t0))
            p2 = (p3[0] + k * r * math.sin(t1), p3[1] - k * r * math.cos(t1))
            out.append((p0, p1, p2, p3))
        return out

    def arc(cx, cy, r, a0, a1):
        segs = arc_pts(cx, cy, r, a0, a1)
        o = ["%s %s m" % (_fmt(X(segs[0][0][0])), _fmt(Y(segs[0][0][1])))]
        for _, p1, p2, p3 in segs:
            o.append("%s %s %s %s %s %s c" % tuple(_fmt(v) for v in (X(p1[0]), Y(p1[1]), X(p2[0]), Y(p2[1]), X(p3[0]), Y(p3[1]))))
        ops.append(" ".join(o) + " S")

    def text(x, y, s, size=7, rgb=(0, 0, 0), page=False):
        s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        s = s.encode("cp1252", "replace").decode("latin-1")
        px, py = (x, y) if page else (X(x), Y(y))
        ops.append("BT %s %s %s rg /F1 %s Tf %s %s Td (%s) Tj ET" % (
            _fmt(rgb[0]), _fmt(rgb[1]), _fmt(rgb[2]), _fmt(size), _fmt(px), _fmt(py), s))

    # Title.
    text(54, PAGE[1] - 50, "ActivityTestStand  -  teststand-%s-plate  -  1:1, 1/8\" acrylic" % plate, 12, page=True)
    text(54, PAGE[1] - 64, "Print at 100% (Actual size, no fit-to-page). Check both scale bars before using.", 8, page=True)

    # Reference hardware, dashed grey, under everything.
    stroke((0.55, 0.55, 0.55), 0.35, (2, 1.5))
    for kind, d, _ in reference(plate):
        if kind == "circle":
            arc(d[0], d[1], d[2], 0, 360)
        else:
            cx, cy, w, h = d
            for a in ((cx - w / 2, cy - h / 2, cx + w / 2, cy - h / 2), (cx + w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                      (cx + w / 2, cy + h / 2, cx - w / 2, cy + h / 2), (cx - w / 2, cy + h / 2, cx - w / 2, cy - h / 2)):
                line(*a)

    # Engraving, blue; outline, black.
    for layer, kind, d in entities(plate):
        if layer == "ENGRAVE":
            stroke((0, 0.35, 0.8), 0.4)
            line(*d)
        elif kind != "circle":
            stroke((0, 0, 0), 0.6)
            (line if kind == "line" else arc)(*d)

    # Holes at final size, with centre crosshairs; red = insert (drill 1/8").
    groups = {}
    for p, x, y, laser, final, role in ts.plate_holes():
        if p != plate:
            continue
        stroke((0.8, 0, 0) if laser != final else (0, 0, 0), 0.5)
        arc(x, y, final / 2, 0, 360)
        c = final / 2 + 0.8
        stroke((0, 0, 0), 0.25)
        line(x - c, y, x + c, y)
        line(x, y - c, x, y + c)
        key = next((k for k in LABELS if role.startswith(k)), role)
        groups.setdefault(key, []).append((x, y))
    for key, pts in groups.items():
        lx, ly, target = LABEL_AT[plate].get(key, (pts[0][0] + 3, pts[0][1] + 3, None))
        if target:
            stroke((0.5, 0.5, 0.5), 0.25)
            line(lx - 0.8, ly + 0.8, *target)
        text(lx, ly, LABELS.get(key, key), 5.5, (0.3, 0.3, 0.3))
    # Origin.
    stroke((0, 0, 0), 0.25)
    line(-2, 0, 2, 0)
    line(0, -2, 0, 2)

    # Scale bars: 100 mm and 4 in, under the plate.
    bx, by = 54, Y(y0) - 60
    for length, ticks, label in ((100 * PT, [(i * PT, 6 if i % 10 == 0 else (4 if i % 5 == 0 else 2.5)) for i in range(101)], "100 mm"),
                                 (4 * 72, [(i * 72 / 8, 6 if i % 8 == 0 else (4 if i % 4 == 0 else 2.5)) for i in range(33)], "4.000 in")):
        ops.append("0 0 0 RG 0.5 w [] 0 d %s %s m %s %s l S" % (_fmt(bx), _fmt(by), _fmt(bx + length), _fmt(by)))
        for t, hgt in ticks:
            ops.append("%s %s m %s %s l S" % (_fmt(bx + t), _fmt(by), _fmt(bx + t), _fmt(by + hgt)))
        text(bx + length + 6, by, label, 8, page=True)
        by -= 30

    # Legend.
    ly = by - 10
    for rgb, dash, s in (((0, 0, 0), None, "black: plate outline and 2-56 clearance holes (cut to size)"),
                         ((0.8, 0, 0), None, "red: insert holes at final 1/8\" (laser 0.118\", then drill)"),
                         ((0, 0.35, 0.8), None, "blue: engraved placement outlines and the tilt axis"),
                         ((0.55, 0.55, 0.55), (2, 1.5), "grey dashed: the hardware, for comparison (bracket ring Ø2.1, servo footprint, BusLinker Ø3 holes)"
                          if plate == "base" else "grey dashed: the U bracket base, its ring holes and Ø8 centre")):
        stroke(rgb, 0.6, dash)
        ops.append("%s %s m %s %s l S" % (_fmt(54), _fmt(ly + 2.5), _fmt(78), _fmt(ly + 2.5)))
        text(84, ly, s, 7, page=True)
        ly -= 12
    text(54, ly - 4, "Origin cross (0, 0) is the %s. x runs along the tilt axis. From Mechanical/ActivityTestStand/teststand.py."
         % ("servo / bracket centre" if plate == "base" else "U-bracket ring centre"), 6.5, (0.3, 0.3, 0.3), page=True)

    content = "\n".join(ops).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
             "/Resources << /Font << /F1 5 0 R >> >> >>" % PAGE).encode(),
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ts.HERE, "plates"))
    a = ap.parse_args()
    ts.check()
    os.makedirs(a.out, exist_ok=True)
    for plate in ("base", "adapter"):
        e = entities(plate)
        stem = os.path.join(a.out, "teststand-%s-plate" % plate)
        open(stem + "-in.dxf", "w").write(dxf(e, 1 / ts.IN, 1))
        open(stem + "-mm.dxf", "w").write(dxf(e, 1.0, 4))
        open(stem + ".svg", "w").write(svg(e, plate))
        open(stem + "-1to1.pdf", "wb").write(pdf(plate))
        x0, y0, x1, y1 = ts.extents(plate)
        n = sum(1 for h in ts.plate_holes() if h[0] == plate)
        print("%s: %.1f x %.1f mm (%.3f x %.3f in), %d holes -> %s-{in,mm}.dxf, -1to1.pdf"
              % (plate, x1 - x0, y1 - y0, (x1 - x0) / ts.IN, (y1 - y0) / ts.IN, n, stem))


if __name__ == "__main__":
    main()
