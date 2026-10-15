"""Read what a tag case needs from a .kicad_pcb.

Case coordinates: origin at the centre of the Edge.Cuts bounding box,
x = kicad_x - cx, y = cy - kicad_y (KiCad's y runs down), z = 0 at the board
underside. +x is the pogo/battery end; a board drawn the other way round is
rejected rather than silently mirrored.

Parses the file as s-expressions, so the KiCad 6 files (space-indented,
fp_text references) read the same as KiCad 8/9 ones (tab-indented,
property references).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Edge, Face, Vector, Wire

# ---------------------------------------------------------------------------
# s-expressions
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


class Sym(str):
    """An unquoted atom, so (layer F.Cu) and (layer "F.Cu") compare equal."""


def parse_sexpr(text: str) -> list:
    stack, cur = [], []
    pos, n = 0, len(text)
    while True:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip():
                raise ValueError("bad s-expression at %d" % pos)
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done, cur = cur, stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(m.group(3))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0]


def head(node) -> str | None:
    return node[0] if isinstance(node, list) and node else None


def children(node, name):
    return [c for c in node[1:] if head(c) == name]


def child(node, name, default=None):
    for c in node[1:]:
        if head(c) == name:
            return c
    return default


def nums(node, name):
    c = child(node, name)
    return tuple(float(v) for v in c[1:] if _is_num(v)) if c else None


def _is_num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def layer_of(node):
    c = child(node, "layer")
    return str(c[1]) if c else None


# ---------------------------------------------------------------------------
# Board model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rect:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @staticmethod
    def around(points):
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        return Rect(min(xs), min(ys), max(xs), max(ys))

    def union(self, other: "Rect") -> "Rect":
        return Rect(min(self.xmin, other.xmin), min(self.ymin, other.ymin),
                    max(self.xmax, other.xmax), max(self.ymax, other.ymax))

    def grow(self, d) -> "Rect":
        return Rect(self.xmin - d, self.ymin - d, self.xmax + d, self.ymax + d)

    def overlaps_y(self, y0, y1) -> bool:
        return self.ymin < y1 and self.ymax > y0


@dataclass(frozen=True)
class Footprint:
    ref: str
    lib_id: str
    at: Vector             # case coordinates
    rotation: float        # KiCad degrees
    side: str              # "F" or "B"
    extent: Rect           # courtyard, else pads
    has_courtyard: bool
    drill: float | None    # largest pad drill, for the harness holes

    @property
    def name(self):
        return self.lib_id.split(":")[-1]


@dataclass(frozen=True)
class Board:
    path: Path
    name: str
    outline: Face          # case coordinates, z = 0
    thickness: float
    kicad_centre: tuple    # (cx, cy) in KiCad coordinates: kicad-cli --user-origin
    footprints: dict = field(repr=False)
    discarded_edges: tuple = ()   # degenerate Edge.Cuts primitives, reported not used

    # -- the parts every tag has -------------------------------------------

    def fp(self, ref) -> Footprint:
        return self.footprints[ref]

    @property
    def pogo(self) -> Footprint:
        return self.fp("J201")

    @property
    def battery_pads(self) -> Footprint | None:
        return self.footprints.get("J401")

    @property
    def harness_holes(self) -> list[Footprint]:
        return sorted((f for f in self.footprints.values() if "taghole" in f.lib_id),
                      key=lambda f: (f.at.X, f.at.Y))

    def parts(self, side) -> list[Footprint]:
        """Components on one side: everything but connectors, holes, logos."""
        return [f for f in self.footprints.values()
                if f.side == side and not f.ref.startswith(("J", "H", "G", "#", "TP"))
                and f.ref[:1].isalpha()]

    def envelope(self, side) -> Rect:
        r = None
        for f in self.parts(side):
            r = f.extent if r is None else r.union(f.extent)
        return r

    @property
    def bbox(self) -> Rect:
        b = self.outline.bounding_box()
        return Rect(b.min.X, b.min.Y, b.max.X, b.max.Y)

    def x_extent_at(self, y0, y1) -> tuple[float, float]:
        """The board's x extent across the strip y0 < y < y1."""
        from build123d import Pos, Rectangle
        bb = self.bbox
        strip = Pos((bb.xmin + bb.xmax) / 2, (y0 + y1) / 2) * Rectangle(
            bb.xmax - bb.xmin + 2, y1 - y0)
        b = (self.outline & strip).bounding_box()
        return b.min.X, b.max.X

    def width_at(self, x0, x1) -> tuple[float, float]:
        """The board's y extent across the strip x0 < x < x1."""
        from build123d import Pos, Rectangle
        bb = self.bbox
        strip = Pos((x0 + x1) / 2, (bb.ymin + bb.ymax) / 2) * Rectangle(
            x1 - x0, bb.ymax - bb.ymin + 2)
        b = (self.outline & strip).bounding_box()
        return b.min.Y, b.max.Y


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _edge_cuts_edges(pcb, to_case):
    """Edges of every Edge.Cuts primitive, board-level and inside footprints."""
    edges, bad = [], []

    def add(kind, node, xf):
        pts = {k: xf(nums(node, k)) for k in ("start", "mid", "end", "center")
               if child(node, k)}
        try:
            if kind == "line":
                if (pts["start"] - pts["end"]).length < 1e-6:
                    raise ValueError("zero length")
                edges.append(Edge.make_line(pts["start"], pts["end"]))
            elif kind == "arc":
                edges.append(Edge.make_three_point_arc(pts["start"], pts["mid"], pts["end"]))
            elif kind == "circle":
                edges.append(Edge.make_circle((pts["end"] - pts["center"]).length).moved(
                    __import__("build123d").Location(pts["center"])))
            elif kind == "rect":
                a, b = pts["start"], pts["end"]
                c = [a, Vector(b.X, a.Y), b, Vector(a.X, b.Y)]
                edges.extend([Edge.make_line(c[i], c[(i + 1) % 4]) for i in range(4)])
            elif kind == "poly":
                p = [xf(tuple(float(v) for v in xy[1:3])) for xy in children(child(node, "pts"), "xy")]
                edges.extend(Edge.make_line(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))
        except (ValueError, KeyError) as e:
            bad.append("%s %s: %s" % (kind, {k: (round(v.X, 3), round(v.Y, 3)) for k, v in pts.items()}, e))

    for node in pcb[1:]:
        h = head(node)
        if h and h.startswith("gr_") and layer_of(node) == "Edge.Cuts":
            add(h[3:], node, to_case)
    for fp in children(pcb, "footprint") + children(pcb, "module"):
        xf = _fp_transform(fp, to_case)
        for node in fp[1:]:
            h = head(node)
            if h and h.startswith("fp_") and layer_of(node) == "Edge.Cuts":
                add(h[3:], node, xf)
    return edges, bad


def _fp_transform(fp, to_case):
    at = nums(fp, "at")
    X, Y = at[0], at[1]
    r = math.radians(at[2] if len(at) > 2 else 0.0)

    def xf(p):
        lx, ly = p[0], p[1]
        # KiCad rotates footprints counter-clockwise on screen, with y down.
        return to_case((X + lx * math.cos(r) + ly * math.sin(r),
                        Y - lx * math.sin(r) + ly * math.cos(r)))
    return xf


def _ref(fp):
    for p in children(fp, "property"):
        if p[1] == "Reference":
            return str(p[2])
    for t in children(fp, "fp_text"):
        if t[1] == "reference":
            return str(t[2])
    return "?"


def _footprint(fp, to_case) -> Footprint:
    xf = _fp_transform(fp, to_case)
    side = "B" if layer_of(fp).startswith("B.") else "F"
    crt, pads, drill = [], [], None
    for node in fp[1:]:
        h = head(node)
        if h in ("fp_line", "fp_rect", "fp_poly", "fp_arc", "fp_circle") and \
                (layer_of(node) or "").endswith("CrtYd"):
            for k in ("start", "end", "mid"):
                if child(node, k):
                    crt.append(xf(nums(node, k)))
            if h == "fp_rect":
                a, b = nums(node, "start"), nums(node, "end")
                crt += [xf((a[0], b[1])), xf((b[0], a[1]))]
            if h == "fp_circle":
                c, e = nums(node, "center"), nums(node, "end")
                rr = math.dist(c, e)
                crt += [xf((c[0] + dx * rr, c[1] + dy * rr)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if h == "fp_poly":
                crt += [xf(tuple(float(v) for v in xy[1:3])) for xy in children(child(node, "pts"), "xy")]
        elif h == "pad":
            pat = nums(node, "at")
            size = nums(node, "size")
            prot = math.radians((pat[2] if len(pat) > 2 else 0.0))
            hw, hh = size[0] / 2, size[1] / 2
            for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
                # pad rotation is absolute in the file; undo the footprint's
                pads.append(xf((pat[0] + dx, pat[1] + dy)))
            d = child(node, "drill")
            if d:
                dv = max(float(v) for v in d[1:] if _is_num(v))
                drill = dv if drill is None else max(drill, dv)
    at = nums(fp, "at")
    return Footprint(
        ref=_ref(fp), lib_id=str(fp[1]), at=to_case((at[0], at[1])),
        rotation=at[2] if len(at) > 2 else 0.0, side=side,
        extent=Rect.around([(p.X, p.Y) for p in (crt or pads or [to_case((at[0], at[1]))])]),
        has_courtyard=bool(crt), drill=drill)


def read_board(path) -> Board:
    path = Path(path)
    pcb = parse_sexpr(path.read_text())
    if head(pcb) != "kicad_pcb":
        raise ValueError("%s is not a .kicad_pcb" % path)

    raw, bad = _edge_cuts_edges(pcb, lambda p: Vector(p[0], -p[1]))   # y up, no offset
    if not raw:
        raise ValueError("%s: no Edge.Cuts outline" % path.name)
    xs = [v.X for e in raw for v in e.vertices()] + [e.bounding_box().min.X for e in raw] + \
         [e.bounding_box().max.X for e in raw]
    wires = Wire.combine(raw, tol=1e-3)
    closed = sorted((w for w in wires if w.is_closed), key=lambda w: -Face(w).area)
    if not closed:
        raise ValueError("%s: Edge.Cuts does not close" % path.name)
    stray = [w for w in wires if not w.is_closed]
    bad += ["open Edge.Cuts run near (%.2f, %.2f)" % (w.center().X, -w.center().Y) for w in stray]

    outer = Face(closed[0])
    bb = outer.bounding_box()
    cx, cy = (bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2   # KiCad coordinates

    def to_case(p):
        return Vector(p[0] - cx, cy - p[1])

    edges, _ = _edge_cuts_edges(pcb, to_case)
    wires = sorted((w for w in Wire.combine(edges, tol=1e-3) if w.is_closed),
                   key=lambda w: -Face(w).area)
    outline = Face(wires[0], [w for w in wires[1:]
                              if Face(wires[0]).is_inside(w.center())])
    # Flipping KiCad's y reverses the winding, so the face can come out facing
    # -z, and extrude() then runs downward: on BitTagNG the board groove was
    # cut below the base top instead of through it. Always face +z.
    if outline.normal_at().Z < 0:
        outline = -outline
    assert outline.normal_at().Z > 0.999

    general = child(pcb, "general")
    thickness = float(child(general, "thickness")[1])
    fps = {}
    for fp in children(pcb, "footprint") + children(pcb, "module"):
        f = _footprint(fp, to_case)
        fps[f.ref] = f

    board = Board(path=path, name=path.stem, outline=outline, thickness=thickness,
                  kicad_centre=(cx, cy), footprints=fps, discarded_edges=tuple(bad))
    if "J201" not in fps:
        raise ValueError("%s: no J201 (pogo pads)" % path.name)
    if board.pogo.at.X < 0:
        raise ValueError("%s: J201 is at negative x; board drawn with the pogo end to the left"
                         % path.name)
    return board


KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def export_board_step(board: Board, cache: Path) -> Path:
    """kicad-cli's STEP of the board with every component model, centred on
    case coordinates, cached until the .kicad_pcb changes."""
    import subprocess
    out = Path(cache) / ("%s-board.step" % board.name)
    if not out.exists() or out.stat().st_mtime < board.path.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        cx, cy = board.kicad_centre
        # --subst-models: footprints that name a .wrl get the same-named STEP;
        # without it they are silently left out (BitTagNG: the 0201s, the QFN
        # and the RTC), and kicad-cli exits 2.
        r = subprocess.run([KICAD_CLI, "pcb", "export", "step", "--include-pads", "--subst-models",
                            "--user-origin=%gx%gmm" % (cx, cy), "-f", "-o", str(out), str(board.path)],
                           capture_output=True, text=True)
        if r.returncode or "Cannot use VRML" in r.stdout + r.stderr:
            out.unlink(missing_ok=True)
            raise RuntimeError("kicad-cli STEP export of %s incomplete:\n%s" % (board.name, r.stdout + r.stderr))
    return out


@dataclass
class Board3D:
    """The exported board, shifted so its lowest feature is at z = 0.
    KiCad's board body is thinner than nominal (0.31 + copper for a 0.4
    board), so heights are taken from component_floor, where KiCad seats the
    top-side models."""
    pcb: object
    pads: object
    components: list          # (label, shape), cells and board included
    z_shift: float

    @property
    def board_top(self) -> float:
        return self.pcb.bounding_box().max.Z

    @property
    def top_side(self) -> list:
        return [(l, s) for l, s in self.components
                if not l.endswith(("_PCB", "_pad")) and s.bounding_box().min.Z > self.z_shift]

    @property
    def component_floor(self) -> float:
        tops = [s.bounding_box().min.Z for _, s in self.top_side]
        return min(tops) if tops else self.board_top


def load_board_3d(board: Board, cache: Path) -> Board3D:
    from build123d import Pos, import_step
    step = import_step(export_board_step(board, cache))
    parts = [(ch.label, ch) for ch in step.children]
    pcb = next(s for l, s in parts if l.endswith("_PCB"))
    pads = next(s for l, s in parts if l.endswith("_pad"))
    dz = -min(pcb.bounding_box().min.Z, pads.bounding_box().min.Z)
    parts = [(l, Pos(0, 0, dz) * s) for l, s in parts]
    return Board3D(pcb=next(s for l, s in parts if l.endswith("_PCB")),
                   pads=next(s for l, s in parts if l.endswith("_pad")),
                   components=parts, z_shift=dz)


def describe(board: Board) -> str:
    bb = board.bbox
    lines = ["%s: %.3f x %.3f, thickness %.2f, KiCad centre (%.3f, %.3f)" % (
        board.name, bb.xmax - bb.xmin, bb.ymax - bb.ymin, board.thickness, *board.kicad_centre),
        "  outline: %d edges, area %.2f (rectangle would be %.2f)" % (
            len(board.outline.edges()), board.outline.area, (bb.xmax - bb.xmin) * (bb.ymax - bb.ymin))]
    for e in board.discarded_edges:
        lines.append("  discarded Edge.Cuts: %s" % e)
    p, j = board.pogo, board.battery_pads
    lines.append("  J201 %s at (%.3f, %.3f) rot %g" % (p.name, p.at.X, p.at.Y, p.rotation))
    if j:
        lines.append("  J401 %s at (%.3f, %.3f) rot %g" % (j.name, j.at.X, j.at.Y, j.rotation))
    for h in board.harness_holes:
        lines.append("  %s hole at (%.3f, %.3f) drill %s" % (h.ref, h.at.X, h.at.Y, h.drill))
    for side in "FB":
        e = board.envelope(side)
        lines.append("  %s.Cu parts envelope x %.2f..%.2f y %.2f..%.2f (%d parts)" % (
            side, e.xmin, e.xmax, e.ymin, e.ymax, len(board.parts(side))))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:]:
        print(describe(read_board(a)))
