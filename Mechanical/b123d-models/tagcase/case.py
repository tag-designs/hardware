"""A tag case (base, lid, no-battery lid) derived from a board.

    case = TagCase(read_board("UIUCTag.kicad_pcb"), label="UIUC")
    case.base, case.lid, case.lid_nb      # build123d Parts
    case.report()                         # every derived number, and why

Coordinates are the board's case coordinates (see kicad.py): +x the pogo/
battery end, z = 0 the board underside. Lids are built with z = 0 at their
underside and placed by lid_z / lid_nb_z.

The rules are TAGCASE-PROCESS.md's, written as code. CaseDesign holds the
house choices; everything else comes from the board, the cells it may carry
and the tag base.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path

from build123d import (Align, Box, Circle, Cylinder, Face, Kind, Location, Part, Plane,
                       Pos, Rectangle, Rot, Text, Vector, extrude, make_hull, mirror,
                       offset)

from .kicad import Board, Rect
from .parts import MIN_BOARD_THICKNESS, SINGLE_PAIR, Pins, TagBase, cells_for

FLOOR = (Align.CENTER, Align.CENTER, Align.MIN)
CORNER = (Align.MIN, Align.MIN, Align.MIN)
FONT = Path.home() / ("Software/OpenSCAD-2021.01.app/Contents/Resources/fonts/"
            "Liberation-2.00.1/ttf/LiberationSans-Bold.ttf")  # the font OpenSCAD used
SWEEP = 4.0      # height of the space the board and cells sweep through


def _erode(face, d):
    """Shrink a planar face by d. build123d 0.13's offset() fails on faces
    with holes (it calls a missing Face.unwrap), so shrink the outer wire and
    grow the holes separately. None if nothing is left."""
    try:
        out = Face(face.outer_wire().offset_2d(-d, kind=Kind.ARC))
    except (RuntimeError, ValueError):
        return None
    for w in face.inner_wires():
        try:
            out = out - Face(w.offset_2d(d, kind=Kind.ARC))
        except (RuntimeError, ValueError):
            return None
    return out if out is not None and out.area > 1e-6 else None


class CaseError(ValueError):
    """The board cannot be cased by these rules without a decision."""


@dataclass(frozen=True)
class CaseDesign:
    # board fit
    edge_clearance: float = 0.0015 * 25.4      # per edge, routing tolerance
    base_margin: tuple = (8.0, 7.0)            # base block beyond the board bbox (x, y)
    base_above_board: float = 1.0              # base top over the board underside
    pocket_clearance: float = 0.2              # around the B.Cu courtyards
    pocket_depth: float = 1.5
    min_ledge: float = 0.5                     # board edge left resting on the base
    # harness slots
    slot_width: float = 2.5
    slot_margin: float = 0.1                   # slot edge beyond the holes' -x edge
    # cells: soldered by hand, so allow for skew about the pads and offset
    cell_clearance: float = 0.4                # to the model's rim, beyond skew and shift
    cell_skew_deg: float = 5.0
    cell_shift: float = 0.3
    stop_below_top: float = 0.05               # end stop height below the board top
    notch_below_top: float = 0.15              # lower again where the tabs cross
    # lid
    pogo_block_drop: float = 1.95              # lid underside over the tallest cell top
    pogo_block_len: float = 2.0
    far_block_gap: float = 0.2                 # pogo end always seats first
    far_block_inset: float = 0.25              # from the board end
    far_block_max_len: float = 2.0
    far_block_hole_clearance: float = 0.5      # from the far harness holes, in y
    part_clearance: float = 0.25               # lid blocks to F.Cu courtyards
    min_contact: float = 0.5                   # narrowest useful bearing foot
    # Far block: "board" bears on the laminate between parts, "parts" on the
    # tallest part under a full-width block, "auto" the board when that leaves
    # two usable feet. Sometimes bearing on a component is the only option.
    far_block_bearing: str = "auto"
    nb_pogo_block_drop: float = 2.6            # no-battery lid, onto the board
    nb_hole_clearance: float = 0.25
    lid_body_height: float = 3.0
    lid_end_height: float = 4.0
    post_r: float = 3.0
    post_spacing: float = 20.0
    # base reinforcement round the posts
    post_secondary_dx: float = -3.5
    post_fill: tuple = (-1.75, 3.5, 6.0)       # dx, length, width
    # engraving
    text_cap_height: tuple = (2.07, 1.79)      # base, lid (OpenSCAD size 3, 2.6)
    marker_size: tuple = (1.99, 2.81)          # "*" glyph width, base, lid
    text_depth: float = 0.8
    text_grow: float = 0.05
    base_text_dx: float = -6.4                 # from the post centre
    marker_inset: float = (2.04, 2.3)          # from the base end / lid pogo end
    marker_margin: float = 0.5                 # base "*" to any edge of the top face
    nb_text: str = "TEST"


@dataclass
class TagCase:
    board: Board
    label: str
    tag_base: TagBase = SINGLE_PAIR
    pins: Pins = Pins.NARROW
    cells: tuple = None                         # default: the board's J401 family
    design: CaseDesign = field(default_factory=CaseDesign)
    cache: Path = None                          # kicad-cli STEP exports

    def __post_init__(self):
        if self.cells is None:
            self.cells = cells_for(self.board)
        if self.pins not in self.tag_base.pins:
            raise CaseError("%s pins do not exist on the %s base" % (self.pins.name, self.tag_base.name))
        if abs(self.board.pogo.rotation % 180 - 90) > 1e-6:
            raise CaseError("J201 at %g deg: the pogo window assumes 90" % self.board.pogo.rotation)
        if self.cache is None:
            self.cache = Path(__file__).resolve().parents[1] / "out" / "cache"
        self._validate_pins()

    # -- derived positions -------------------------------------------------

    @property
    def d(self) -> CaseDesign:
        return self.design

    @property
    def board_top(self) -> float:
        return MIN_BOARD_THICKNESS

    @property
    def pogo(self) -> Vector:
        return self.board.pogo.at

    @property
    def post_x(self) -> float:
        return self.pogo.X + self.tag_base.screws[0][0]

    @property
    def underside(self) -> float:
        return -self.tag_base.board_underside

    @cached_property
    def base_size(self):
        bb = self.board.bbox
        c = self.d.edge_clearance
        return (bb.xmax - bb.xmin + 2 * c + self.d.base_margin[0],
                bb.ymax - bb.ymin + 2 * c + self.d.base_margin[1])

    @cached_property
    def groove(self) -> Face:
        return offset(self.board.outline, self.d.edge_clearance, kind=Kind.INTERSECTION)

    def _holes(self, end):
        hs = [h for h in self.board.harness_holes if (h.at.X > 0) == (end == "pogo")]
        if not hs:
            raise CaseError("no harness holes at the %s end" % end)
        return hs

    def slot_x(self, end) -> float:
        hs = self._holes(end)
        r = max(h.drill for h in hs) / 2
        lo = min(h.at.X for h in hs) - r - self.d.slot_margin
        hi = max(h.at.X for h in hs) + r
        if hi > lo + self.d.slot_width:
            raise CaseError("%s-end holes span %.2f, wider than the slot" % (end, hi - lo))
        return lo + self.d.slot_width / 2

    @cached_property
    def pocket(self) -> Rect:
        """B.Cu courtyards plus clearance, run on into the pogo-end slot."""
        env = self.board.envelope("B").grow(self.d.pocket_clearance)
        return Rect(env.xmin, env.ymin, max(env.xmax, self.slot_x("pogo")), env.ymax)

    @cached_property
    def cell_positions(self):
        """Every (cell, Location) the case must accept: nominal, skewed about
        the pads both ways, for each cell the board may carry."""
        j = self.board.battery_pads
        out = []
        for cell in self.cells:
            for skew in (-self.d.cell_skew_deg, 0.0, self.d.cell_skew_deg):
                loc = Location((j.at.X, j.at.Y, self.board_top), (0, 0, j.rotation + skew))
                out.append((cell, skew, loc))
        return out

    @cached_property
    def relief(self) -> Face:
        circles = []
        for cell, _, loc in self.cell_positions:
            c = (loc * Location((*cell.centre, 0))).position
            r = cell.radius + self.d.cell_clearance + self.d.cell_shift
            circles.append(Pos(c.X, c.Y) * Circle(r).edges()[0])
        return make_hull(circles)

    @cached_property
    def tallest_cell(self) -> float:
        return self.board_top + max((c.height for c in self.cells), default=0.0)

    # -- lid geometry --------------------------------------------------------

    @cached_property
    def lid_z(self) -> float:
        """Standard lid underside: a fixed drop above the tallest cell keeps
        the screw stack of the earlier lids."""
        return self.tallest_cell + self.d.pogo_block_drop

    @cached_property
    def lid_nb_z(self) -> float:
        return self.board_top + self.d.nb_pogo_block_drop

    @cached_property
    def pogo_block_seat(self) -> float:
        """Where the standard lid's pogo-end block lands: the highest cell
        material under it, over every cell and skew. On UIUCTag that is the
        cell top; on BitTag-shaped boards J201 sits behind J401 and the block
        lands on the positive tab."""
        prism = Pos(self.pogo.X, self.pogo.Y, 0) * Box(
            self.d.pogo_block_len, self.pogo_block_width, 20, align=FLOOR)
        tops = []
        for cell, _, loc in self.cell_positions:
            hit = prism & (loc * cell.model())
            if hit is not None and hit.volume > 1e-6:
                tops.append(hit.bounding_box().max.Z)
        if not tops:
            raise CaseError("no cell under the pogo-end block")
        return max(tops)

    @property
    def pogo_block_width(self) -> float:
        lo, hi = self.board.width_at(self.pogo.X - self.d.pogo_block_len / 2,
                                     self.pogo.X + self.d.pogo_block_len / 2)
        return hi - lo - 1.0

    @cached_property
    def nb_pogo_block_width(self) -> float:
        hs = self._holes("pogo")
        return 2 * (min(abs(h.at.Y) for h in hs) - hs[0].drill / 2 - self.d.nb_hole_clearance)

    @cached_property
    def far_block(self):
        """(x0, x1, halfwidth, keep-outs). Inset from the far end, short of the
        nearest top-side part further in; parts right at the end become
        keep-outs cut from the block."""
        hs = self._holes("far")
        hw = min(abs(h.at.Y) for h in hs) - hs[0].drill / 2 - self.d.far_block_hole_clearance
        x0 = self.board.x_extent_at(-hw, hw)[0] + self.d.far_block_inset
        c = self.d.part_clearance
        in_strip = [p for p in self.board.parts("F") if p.extent.overlaps_y(-hw - c, hw + c)]
        at_end = [p for p in in_strip if p.extent.xmin - c < x0 + self.d.min_contact]
        further = [p.extent.xmin - c for p in in_strip if p not in at_end and p.extent.xmin > x0]
        x1 = min([x0 + self.d.far_block_max_len] + further)
        keepouts = [p.extent.grow(c) for p in at_end]
        return x0, x1, hw, keepouts

    @cached_property
    def board_3d(self):
        from .kicad import load_board_3d
        return load_board_3d(self.board, self.cache)

    @cached_property
    def far_block_bearing(self):
        """(mode, feet as y spans, height it bears at above the board top,
        what it bears on). Part heights come from the board's KiCad models."""
        feet, _ = self.far_block_feet()
        mode = self.d.far_block_bearing
        if mode == "board" or (mode == "auto" and len(feet) >= 2):
            return "board", feet, 0.0, None
        x0, x1, hw, _ = self.far_block
        prism = Pos(x0, -hw, 0) * Box(x1 - x0, 2 * hw, 50, align=CORNER)
        b3, best = self.board_3d, (0.0, None)
        for label, s in b3.top_side:
            hit = prism & s
            if hit is not None and hit.volume > 1e-6:
                h = hit.bounding_box().max.Z - b3.component_floor
                c = s.bounding_box().center()
                ref = next((f.ref for f in self.board.parts("F")
                            if f.extent.xmin <= c.X <= f.extent.xmax and f.extent.ymin <= c.Y <= f.extent.ymax),
                           label)
                best = max(best, (h, ref), key=lambda t: t[0])
        if best[1] is None:
            return "board", [(-hw, hw)], 0.0, None
        return "parts", [(-hw, hw)], best[0], best[1]

    def far_block_feet(self):
        """The far block's bearing area, as rectangles, after keep-outs."""
        x0, x1, hw, keep = self.far_block
        spans = [(-hw, hw)]
        for k in keep:
            if k.xmin < x1 and k.xmax > x0:
                nxt = []
                for a, b in spans:
                    if k.ymin > a:
                        nxt.append((a, min(b, k.ymin)))
                    if k.ymax < b:
                        nxt.append((max(a, k.ymax), b))
                spans = [(a, b) for a, b in nxt if b > a]
        return [(a, b) for a, b in spans if b - a >= self.d.min_contact], spans

    # -- validation ----------------------------------------------------------

    def _validate_pins(self):
        g = self.board.bbox.grow(self.d.edge_clearance)
        for x, y in self.pins.value:
            px, py = self.pogo.X + x, self.pogo.Y + y
            r = self.tag_base.pin_r
            if g.xmin - r < px < g.xmax + r and g.ymin - r < py < g.ymax + r:
                raise CaseError("%s pin hole at (%.2f, %.2f) cuts the board groove; use WIDE pins "
                                "on a lipo base" % (self.pins.name, px, py))

    # -- solids ----------------------------------------------------------------

    def _engraving(self, s, cap_height, mirrored=False):
        em = cap_height / 0.688              # Liberation Sans cap height is 0.688 em
        faces = Text(s, font_size=em, font_path=str(FONT), align=(Align.CENTER, Align.CENTER)).faces()
        grown = []
        for f in faces:
            try:
                grown.append(offset(f, self.d.text_grow, kind=Kind.INTERSECTION))
            except RuntimeError:                 # Bezier glyphs (C, S)
                grown.append(offset(f, self.d.text_grow, kind=Kind.ARC))
        solid = Part() + [extrude(f, self.d.text_depth + 0.1) for f in grown]
        solid = Rot(0, 0, -90) * solid
        return mirror(solid, about=Plane.YZ) if mirrored else solid

    def _marker_face(self, width):
        em = width / 0.389                   # "*" ink is 0.389 em wide
        return Text("*", font_size=em, font_path=str(FONT), align=(Align.CENTER, Align.CENTER))

    def _marker(self, width):
        return extrude(self._marker_face(width), self.d.text_depth + 0.1)

    def _posts(self, r, h, z=0.0):
        return [Pos(self.post_x + x - self.tag_base.screws[0][0] + self.tag_base.screws[0][0],
                    self.pogo.Y + y, z) * Cylinder(r, h, align=FLOOR)
                for x, y in [(0, s * self.d.post_spacing / 2) for s in (-1, 1)]]

    @cached_property
    def base(self) -> Part:
        where, u, v = self.base_marker
        # The end face has room for the larger, lid-size glyph.
        mark = self._marker(self.d.marker_size[0 if where == "top" else 1])
        if where == "top":
            return self._base_body - Pos(u, v, self.d.base_above_board - self.d.text_depth) * mark
        # On the pogo-end face: glyph upright, cut in along -x.
        end = Plane(origin=(self.base_size[0] / 2 - self.d.text_depth, u, v),
                    x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        return self._base_body - end * mark

    @cached_property
    def _base_body(self) -> Part:
        """The base with every cut but the "*" marker, which is placed on
        whatever top surface this leaves."""
        d, tb = self.d, self.tag_base
        z0, h = self.underside, self.tag_base.board_underside + d.base_above_board
        L, W = self.base_size
        solid = Pos(0, 0, z0) * Box(L, W, h, align=FLOOR)
        for y in (-d.post_spacing / 2, d.post_spacing / 2):
            at = Pos(self.post_x, self.pogo.Y + y, z0)
            solid += at * Cylinder(d.post_r, h, align=FLOOR)
            solid += at * Pos(d.post_secondary_dx, 0, 0) * Cylinder(d.post_r, h, align=FLOOR)
            solid += at * Pos(d.post_fill[0], 0, 0) * Box(d.post_fill[1], d.post_fill[2], h, align=FLOOR)

        cuts = [extrude(self.groove, SWEEP)]
        p = self.pocket
        cuts.append(Pos(p.xmin, p.ymin, -d.pocket_depth) * Box(
            p.xmax - p.xmin, p.ymax - p.ymin, SWEEP + d.pocket_depth, align=CORNER))
        for end in ("far", "pogo"):
            cuts.append(Pos(self.slot_x(end), 0, -d.pocket_depth) * Box(
                d.slot_width, W + 0.1, SWEEP + d.pocket_depth, align=FLOOR))
        wx, wy = tb.pogo_window
        cuts.append(Pos(self.pogo.X, self.pogo.Y, z0 - 0.1) * Box(wx, wy, h + 0.2, align=FLOOR))
        for x, y in self.pins.value:
            cuts.append(Pos(self.pogo.X + x, self.pogo.Y + y, z0 - 0.1) *
                        Cylinder(tb.pin_r, h + 0.2, align=FLOOR))
        for x, y in tb.screws:
            cuts.append(Pos(self.pogo.X + x, self.pogo.Y + y, z0 - 0.1) *
                        Cylinder(tb.insert_r, h + 0.2, align=FLOOR))
        if self.cells:
            stop = self.board_top - d.stop_below_top
            cuts.append(Pos(0, 0, stop) * extrude(self.relief, SWEEP))
            cuts.append(Pos(self.board.battery_pads.at.X, -self.notch_halfwidth,
                            self.board_top - d.notch_below_top) *
                        Box(L, 2 * self.notch_halfwidth, SWEEP, align=CORNER))
        cuts.append(Pos(self.post_x + d.base_text_dx, 0, z0 - 0.1) *
                    self._engraving(self.label, d.text_cap_height[0], mirrored=True))
        return solid - cuts

    @cached_property
    def notch_halfwidth(self) -> float:
        """Where the under-cell tabs cross the board end, with the skew."""
        j = self.board.battery_pads
        reach = self.board.bbox.xmax - j.at.X
        return (max(c.tab_halfwidth for c in self.cells) + self.d.cell_shift
                + reach * math.sin(math.radians(self.d.cell_skew_deg)))

    @cached_property
    def base_marker(self):
        """Where the base "*" goes. Only its end matters (it pairs with the
        lid's to show which way round the lid sits), so take the place on the
        base top nearest the pogo end where the real glyph fits with
        marker_margin all round. Candidates come from the top faces eroded by
        the glyph's half-width plus the margin; each is then tested with the
        glyph itself, since the "*" fills a corner of its box poorly."""
        top, m = self.d.base_above_board, self.d.marker_margin
        # The lid turns 180 deg about the screw axis, so a marker means
        # something only clearly on the pogo side of it.
        x_min = self.post_x + self.d.post_r
        glyph = self._marker_face(self.d.marker_size[0])
        gb = glyph.bounding_box()
        need = max(gb.max.X - gb.min.X, gb.max.Y - gb.min.Y) / 2 + m
        faces = [Pos(0, 0, -top) * f for f in self._base_body.faces()
                 if f.normal_at().Z > 0.999 and abs(f.center().Z - top) < 1e-6]
        candidates = []
        for f in faces:
            inner = _erode(f, need)
            if inner is None:
                continue
            for e in inner.edges():
                candidates += [(e.position_at(i / 40), f) for i in range(41)]
        for p, f in sorted(candidates, key=lambda c: -c[0].X):
            if p.X < x_min:
                break
            g = Pos(p.X, p.Y) * glyph
            outside = g - f
            if (outside is None or outside.area < 1e-6) and \
                    min(g.distance_to(e) for e in f.edges()) >= m - 1e-6:
                return "top", p.X, p.Y
        # No room on top: the pogo-end face, centred, halfway up the solid
        # part below the cell relief.
        stop = self.board_top - self.d.stop_below_top if self.cells else top
        return "end", 0.0, (self.underside + stop) / 2

    def _lid(self, nb: bool) -> Part:
        d, tb = self.d, self.tag_base
        x0, x1, hw, keep = self.far_block
        bb = self.board.bbox.grow(d.edge_clearance)
        body_x1 = self.pogo.X + d.pogo_block_len / 2
        lid = Pos(x0, bb.ymin, 0) * Box(body_x1 - x0, bb.ymax - bb.ymin, d.lid_body_height, align=CORNER)
        lid += Pos(self.post_x, self.pogo.Y, 0) * Box(2 * d.post_r, d.post_spacing, d.lid_body_height, align=FLOOR)
        for y in (-d.post_spacing / 2, d.post_spacing / 2):
            lid += Pos(self.post_x, self.pogo.Y + y, 0) * Cylinder(d.post_r, d.lid_end_height, align=FLOOR)

        _, feet, bear_h, _ = self.far_block_bearing
        if nb:
            seat, drop_far = self.board_top, self.lid_nb_z - self.board_top - bear_h - d.far_block_gap
            width = self.nb_pogo_block_width
            lz = self.lid_nb_z
        else:
            seat, drop_far = self.pogo_block_seat, self.lid_z - self.board_top - bear_h - d.far_block_gap
            width = self.pogo_block_width
            lz = self.lid_z
        drop = lz - seat
        lid += Pos(self.pogo.X, self.pogo.Y, -drop) * Box(d.pogo_block_len, width,
                                                         drop + d.lid_body_height, align=FLOOR)
        # Bearing on the board: only the feet left between keep-outs wide
        # enough to print and bear. On a part: one block, full width.
        for a, b in feet:
            lid += Pos(x0, a, -drop_far) * Box(x1 - x0, b - a, drop_far + d.lid_body_height, align=CORNER)

        cuts = [Pos(self.post_x, self.pogo.Y + y, -0.1) * Cylinder(tb.screw_r, d.lid_end_height + 0.2, align=FLOOR)
                for y in (-d.post_spacing / 2, d.post_spacing / 2)]
        top = d.lid_body_height - d.text_depth
        cuts.append(Pos(self.post_x, self.pogo.Y, top) * self._engraving(self.label, d.text_cap_height[1]))
        cuts.append(Pos(body_x1 - d.marker_inset[1], self.pogo.Y, top) * self._marker(d.marker_size[1]))
        if nb:
            cuts.append(Pos((x0 + self.post_x - d.post_r) / 2, self.pogo.Y, top) *
                        self._engraving(d.nb_text, d.text_cap_height[1]))
        return lid - cuts

    @cached_property
    def lid(self) -> Part:
        return self._lid(False)

    @cached_property
    def lid_nb(self) -> Part:
        return self._lid(True)

    # -- report ----------------------------------------------------------------

    def report(self) -> str:
        b, d = self.board, self.d
        x0, x1, hw, keep = self.far_block
        feet, spans = self.far_block_feet()
        bb = b.bbox
        out = [
            "%s case for %s (%s base, %s pins, cells %s)" % (
                self.label, b.name, self.tag_base.name, self.pins.name,
                "/".join(c.name for c in self.cells) or "none"),
            "  board %.3f x %.3f bbox, outline area %.2f, designed at %.2f thick"
            % (bb.xmax - bb.xmin, bb.ymax - bb.ymin, b.outline.area, self.board_top),
            "  base %.3f x %.3f, underside z %.2f; J201 (%.3f, %.3f), posts x %.3f"
            % (*self.base_size, self.underside, self.pogo.X, self.pogo.Y, self.post_x),
            "  slots x %.3f (far), %.3f (pogo); pocket x %.2f..%.2f y %.2f..%.2f"
            % (self.slot_x("far"), self.slot_x("pogo"), self.pocket.xmin, self.pocket.xmax,
               self.pocket.ymin, self.pocket.ymax),
        ]
        ylo, yhi = b.width_at(self.pocket.xmin, min(self.pocket.xmax, self.slot_x("pogo") - d.slot_width / 2))
        ledges = (self.pocket.ymin - ylo, yhi - self.pocket.ymax)
        out.append("  pocket ledges %.2f / %.2f (min %.2f)%s" % (
            *ledges, d.min_ledge, "" if min(ledges) >= d.min_ledge else "  ** BELOW MINIMUM"))
        if self.cells:
            rb = self.relief.bounding_box()
            out.append("  cell relief x %.2f..%.2f y %.2f..%.2f (skew +-%g deg, shift %.2f); tab notch +-%.2f"
                       % (rb.min.X, rb.max.X, rb.min.Y, rb.max.Y, d.cell_skew_deg, d.cell_shift,
                          self.notch_halfwidth))
            out.append("  lid underside z %.3f (tallest cell %.3f + %.2f); pogo block seats at z %.3f, drop %.3f"
                       % (self.lid_z, self.tallest_cell, d.pogo_block_drop, self.pogo_block_seat,
                          self.lid_z - self.pogo_block_seat))
        out.append("  no-battery lid underside z %.3f; pogo block width %.2f" % (self.lid_nb_z, self.nb_pogo_block_width))
        out.append("  far block x %.3f..%.3f, |y| < %.3f; keep-outs %s"
                   % (x0, x1, hw, ", ".join("x %.2f..%.2f y %.2f..%.2f" % (k.xmin, k.xmax, k.ymin, k.ymax)
                                            for k in keep) or "none"))
        mode, bfeet, bh, on = self.far_block_bearing
        if mode == "parts":
            out.append("  far block bears on %s (%.2f above the board): the board leaves %s"
                       % (on, bh, ", ".join("y %.2f..%.2f" % s for s in spans)))
        elif keep:
            out.append("  far block feet %s%s" % (
                ", ".join("y %.2f..%.2f" % s for s in bfeet),
                "" if len(bfeet) >= 2 else "  ** FEWER THAN TWO USABLE FEET (min %.2f wide)" % d.min_contact))
        where, u, v = self.base_marker
        out.append("  base marker: %s" % (
            "top at (%.2f, %.2f), %.2f clear all round" % (u, v, d.marker_margin) if where == "top"
            else "on the pogo-end face at y %.2f, z %.2f (no room on top past the screws)" % (u, v)))
        for e in b.discarded_edges:
            out.append("  ignored Edge.Cuts: %s" % e)
        return "\n".join(out)
