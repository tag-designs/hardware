"""Fit check of a TagCase against the real parts.

The tag comes from kicad-cli's STEP export of the board (every component
model); the cells, tag-base PCB, 855 connector and dowels from the library.
Each cell is checked at every position the case allows for: nominal and
skewed both ways about its pads. Lids are lowered until their pogo-end block
lands, on the real geometry.

Results are requirements with a measured value, so a shrinking margin shows
before it becomes a collision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Compound, Cylinder, Location, Pos, export_step, import_step

from .case import CORNER, FLOOR, TagCase

TOL = 1e-3                                   # mm^3: boolean noise


def overlap(a, b) -> float:
    """Solid by solid: OCCT's common is undefined when one argument's own
    solids overlap (the 855 connector's plungers sit in their barrels)."""
    total = 0.0
    for sa in a.solids():
        for sb in b.solids():
            r = sa & sb
            total += r.volume if r is not None else 0.0
    return total


@dataclass
class Result:
    label: str
    value: float
    ok: bool
    note: str = ""


class FitCheck:
    def __init__(self, case: TagCase):
        self.case = case
        self.results: list[Result] = []
        self._load()

    # -- parts ---------------------------------------------------------------

    def _load(self):
        c = self.case
        b3 = c.board_3d
        parts, dz = b3.components, b3.z_shift
        cell_labels = [l for l, _ in parts if "MS621" in l or "MS920" in l or "Battery" in l]
        self.pcb = next(s for l, s in parts if l.endswith("_PCB"))
        self.board_top = self.pcb.bounding_box().max.Z
        self.components = [(l, s) for l, s in parts if l not in cell_labels]
        self.tag = Compound([s for _, s in self.components])
        self.bottom = Compound([s for l, s in self.components
                                if s.bounding_box().max.Z <= dz + 1e-3 and not l.endswith("_pad")])
        # Cells sit where KiCad's component models do (its board body is
        # thinner than the 0.4 nominal; see TAGCASE-PROCESS.md).
        self.cell_floor = b3.component_floor
        self.cells = []
        for cell, skew, loc in c.cell_positions:
            at = Location((loc.position.X, loc.position.Y, self.cell_floor), tuple(loc.orientation))
            self.cells.append(("%s %+g deg" % (cell.name, skew), at * cell.model()))

        tb = c.tag_base
        self.base_pcb = Location((c.pogo.X, c.pogo.Y, c.underside), (0, 0, -90)) * tb.pcb()
        self.connector = Pos(c.pogo.X, c.pogo.Y, c.underside) * tb.connector()
        ztop = self.connector.bounding_box().max.Z
        self.plungers = [s for s in self.connector.solids() if abs(s.bounding_box().max.Z - ztop) < 1e-3]
        dz0 = tb.dowel().bounding_box().min.Z
        self.dowels = [Pos(c.pogo.X + x, c.pogo.Y + y, c.underside - tb.pcb_thickness - dz0) * tb.dowel()
                       for x, y in c.pins.value]

    def seated_lid(self, cell_shape=None):
        """The standard lid lowered onto cell_shape, or the no-battery lid
        onto the board."""
        c = self.case
        if cell_shape is None:
            # Lands on whatever is highest under the block: the laminate, or
            # copper where pads sit under it (J401's, on BitTag-shaped boards).
            prism = Pos(c.pogo.X, c.pogo.Y, 0) * Box(c.d.pogo_block_len, c.nb_pogo_block_width, 20,
                                                     align=FLOOR)
            tops = [h.bounding_box().max.Z for s in self.tag.solids()
                    if (h := prism & s) is not None and h.volume > 1e-6]
            seat = max(tops, default=self.board_top)
            return Pos(0, 0, seat + c.lid_nb_z - c.board_top) * c.lid_nb
        prism = Pos(c.pogo.X, c.pogo.Y, 0) * Box(c.d.pogo_block_len, c.pogo_block_width, 20, align=FLOOR)
        hit = prism & cell_shape
        seat = hit.bounding_box().max.Z if hit is not None else c.pogo_block_seat
        return Pos(0, 0, c.lid_z + (seat - c.pogo_block_seat)) * c.lid

    def far_gap(self, lid) -> float:
        """The far block to whatever it bears on: the board, or a part."""
        x0, x1, hw, _ = self.case.far_block
        block = lid & (Pos(x0 - 1, -hw - 1, -20) * Box(x1 - x0 + 1, 2 * hw + 2, 40, align=CORNER))
        under = self.tag & (Pos(x0 - 1, -hw - 1, -20) * Box(x1 - x0 + 1, 2 * hw + 2, 40, align=CORNER))
        return block.distance_to(under)

    # -- requirements --------------------------------------------------------

    def need(self, label, value, ok, note=""):
        self.results.append(Result(label, value, ok, note))

    def clear(self, label, a, b, min_gap=0.0):
        v = overlap(a, b)
        gap = a.distance_to(b)
        self.need(label, gap, v < TOL and gap >= min_gap - 1e-6,
                  ("overlap %.4f mm3" % v) if v >= TOL else ("min %.2f" % min_gap if min_gap else ""))

    def run(self):
        c = self.case
        base = c.base
        self.clear("base vs board and components", base, self.tag, 0.03)
        self.clear("pogo connector vs base", self.connector, base, 0.05)
        self.clear("pogo connector vs bottom components", self.connector, self.bottom)
        pads = [(c.pogo.X + dx, c.pogo.Y + dy) for dx in (-0.635, 0.635) for dy in (-1.27, 0, 1.27)]
        miss = max(min(((p.bounding_box().center().X - x) ** 2 + (p.bounding_box().center().Y - y) ** 2) ** 0.5
                       for x, y in pads) for p in self.plungers)
        self.need("plungers to J201 pad centres (worst)", miss, miss < 0.05)
        for i, d in enumerate(self.dowels):
            self.need("dowel %d press fit in base (mm3)" % i, overlap(d, base), overlap(d, base) > 0.1)
            self.clear("dowel %d vs tag" % i, d, self.tag)

        # Radial clearance: the base above the stop shelf, against the cell
        # body (the vertical gap over the shelf is reported separately).
        shelf = c.board_top - c.d.stop_below_top + 0.05
        above = base & (Pos(0, 0, shelf) * Box(100, 100, 20, align=FLOOR))
        for name, cell in self.cells:
            self.clear("base vs %s" % name, base, cell)
            body = cell & (Pos(0, 0, shelf) * Box(100, 100, 20, align=FLOOR))
            self.need("xy clearance, %s to relief wall" % name, above.distance_to(body),
                      above.distance_to(body) >= c.d.cell_clearance - 1e-3,
                      "min %.2f" % c.d.cell_clearance)
        for name, cell in [x for x in self.cells if x[0].endswith(" +0 deg")]:
            lid = self.seated_lid(cell)
            self.clear("lid on %s vs board and components" % name, lid, self.tag)
            gap = self.far_gap(lid)
            self.need("lid on %s: far block gap (%s)" % (name, c.far_block_bearing[3] or "board"), gap,
                      0.0 < gap <= 0.5, "seats pogo end first, closable by screws")
            for i, d in enumerate(self.dowels):
                self.clear("lid on %s vs dowel %d" % (name, i), lid, d)
        lid_nb = self.seated_lid(None)
        self.clear("no-battery lid vs board and components", lid_nb, self.tag)
        gap = self.far_gap(lid_nb)
        self.need("no-battery lid: far block gap (%s)" % (c.far_block_bearing[3] or "board"), gap,
                  0.0 < gap <= 0.5, "seats pogo end first")
        self.clear("no-battery lid vs base", lid_nb, base, 0.1)
        for i, d in enumerate(self.dowels):
            self.clear("no-battery lid vs dowel %d" % i, lid_nb, d, 0.3)
        # Every top-side part but the one the far block is meant to bear on,
        # whose gap is the far-block requirement above.
        x0, x1, hw, _ = c.far_block
        borne = c.far_block_bearing[0] == "parts"

        def under_far_block(s):
            ctr = s.bounding_box().center()
            return borne and x0 <= ctr.X <= x1 + c.d.part_clearance and abs(ctr.Y) <= hw + c.d.part_clearance

        tall = min(((lid_nb.distance_to(s), l) for l, s in self.components
                    if not l.endswith(("_PCB", "_pad")) and s.bounding_box().min.Z > self.board_top - 0.1
                    and not under_far_block(s)),
                   default=(None, None))
        self.need("no-battery lid to nearest top part (%s)" % tall[1], tall[0], tall[0] >= 0.3)
        for i, h in enumerate(x for x in c.board.harness_holes if x.at.X > 0):
            hole = Pos(h.at.X, h.at.Y, -0.5) * Cylinder(h.drill / 2, 2, align=FLOOR)
            self.clear("no-battery lid vs %s hole" % h.ref, lid_nb, hole, 0.2)

        # Positive stop: the base wall at the board's pogo end.
        xmax = c.board.bbox.xmax
        wall = base & (Pos(xmax - 0.1, -20, -10) * Box(15, 40, 20, align=CORNER))
        at_edge = wall & (Pos(xmax, -4, -10) * Box(0.3, 8, 20, align=CORNER))
        h = at_edge.bounding_box().max.Z if at_edge is not None else float("nan")
        self.need("end stop wall height (board top %.3f)" % self.board_top, h,
                  0 < h <= c.board_top + 1e-6, "at or below the board top")
        self.need("end stop gap", self.pcb.distance_to(wall), self.pcb.distance_to(wall) < 0.1)
        return all(r.ok for r in self.results)

    def table(self) -> str:
        out = []
        for r in self.results:
            out.append("  %-52s %8.3f  %-4s %s" % (r.label, r.value if r.value is not None else float("nan"),
                                                   "ok" if r.ok else "FAIL", r.note))
        out.append("  -> %s" % ("ALL CLEAR" if all(r.ok for r in self.results)
                               else "FAILED: %d" % sum(not r.ok for r in self.results)))
        return "\n".join(out)

    def export(self, path):
        c = self.case
        nominal = [s for n, s in self.cells if n.endswith(" +0 deg")]
        asm = Compound(label="%s_assembly" % c.board.name, children=[
            Compound(label="Tag", children=[s for _, s in self.components]),
            Compound(label="Cells", children=nominal),
            Compound(label="Base", children=[c.base]),
            Compound(label="Lid", children=[self.seated_lid(nominal[0]) if nominal else c.lid]),
            Compound(label="Lid_no_battery", children=[Pos(0, 30, 0) * self.seated_lid(None)]),
            Compound(label="TagBase", children=[self.base_pcb, self.connector] + self.dowels),
        ])
        export_step(asm, str(path))
