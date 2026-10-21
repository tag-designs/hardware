#!/usr/bin/env python3
"""Write the two 1/8" acrylic plates as DXF (inch and mm) and SVG previews.

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
        x0, y0, x1, y1 = ts.extents(plate)
        n = sum(1 for h in ts.plate_holes() if h[0] == plate)
        print("%s: %.1f x %.1f mm (%.3f x %.3f in), %d holes -> %s-{in,mm}.dxf"
              % (plate, x1 - x0, y1 - y0, (x1 - x0) / ts.IN, (y1 - y0) / ts.IN, n, stem))


if __name__ == "__main__":
    main()
