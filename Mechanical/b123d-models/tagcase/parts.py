"""The parts every tag case is built around: coin cells, the tag base it mates
to, and the alignment-pin options.

Everything here is common to all tags. A board contributes only positions
(J201, J401, the J30x holes), which come from its .kicad_pcb.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache, cached_property
from pathlib import Path

from build123d import Box, Location, Pos, Shape, Vector, import_step
from OCP.gp import gp_Trsf

REPO = Path(__file__).resolve().parents[3]          # Mechanical/b123d-models/tagcase/
PACKAGES = REPO / "BoardDesigns" / "libraries" / "packages3D"
COMPONENTS = REPO / "Mechanical" / "Components"

# Boards are designed to this; the thinnest board sets every clearance.
MIN_BOARD_THICKNESS = 0.4


def _axes(rows, offset) -> Location:
    """rows[i]: output axis i as a signed input-axis index (1=x, 2=y, 3=z)."""
    v = [[0.0] * 3 for _ in range(3)]
    for i, r in enumerate(rows):
        v[i][abs(r) - 1] = 1.0 if r > 0 else -1.0
    t = gp_Trsf()
    t.SetValues(*v[0], offset[0], *v[1], offset[1], *v[2], offset[2])
    return Location(t)


# ---------------------------------------------------------------------------
# Coin cells
# ---------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class CoinCell:
    """A tabbed coin cell, described in KiCad's footprint frame for J401:
    origin at the footprint origin, z = 0 on the board top, the cell lying
    toward -x (so a J401 at 180 degrees puts it toward +x, off the pogo end).
    """
    name: str
    step: Path
    to_footprint: Location      # vendor model axes -> footprint frame
    tab_halfwidth: float        # under-cell tab, where it crosses the board edge

    @cache
    def model(self) -> Shape:
        return self.to_footprint * import_step(self.step)

    def placement(self, j401, board_top=MIN_BOARD_THICKNESS) -> Location:
        return Location((j401.at.X, j401.at.Y, board_top), (0, 0, j401.rotation))

    def placed(self, j401, board_top=MIN_BOARD_THICKNESS) -> Shape:
        return self.placement(j401, board_top) * self.model()

    @cached_property
    def _body(self):
        """The cell body, from a mid-height slice of the model (the tabs are
        thin and sit at the top and bottom): its centre and true rim radius.
        Clearance is the case's business, not the cell's."""
        m = self.model()
        slab = m & (Pos(0, 0, self.height / 2) * Box(60, 60, 0.01))
        b = max(slab.solids(), key=lambda s: s.volume).bounding_box()
        return ((b.min.X + b.max.X) / 2, (b.min.Y + b.max.Y) / 2), (b.max.Y - b.min.Y) / 2

    @property
    def centre(self) -> tuple:
        return self._body[0]

    @property
    def radius(self) -> float:
        return self._body[1]

    def centre_on(self, j401) -> Vector:
        return (self.placement(j401, 0) * Location((*self.centre, 0))).position

    @property
    def height(self) -> float:
        """Board top to the top of the positive contact."""
        return self.model().bounding_box().max.Z


MS621F = CoinCell(
    name="MS621F",
    step=PACKAGES / "BatteryHolder_Seiko_MS621F.step",   # already in footprint frame
    to_footprint=Location(),
    tab_halfwidth=1.0,
)

# Vendor model: thickness along +y, tabs toward -z, feet z -8.05..-6.0 about
# x = 0. Map it so the feet sit on the footprint origin and the cell lies
# toward -x, as the MS621F does.
MS920SE = CoinCell(
    name="MS920SE",
    step=PACKAGES / "MS920SE-FL27E.STEP",
    to_footprint=_axes((-3, -1, 2), (-(8.05 + 6.0) / 2, 0, 0)),
    tab_halfwidth=1.25,
)

# Which cells a board may carry, by its J401 footprint. A board that can take
# an MS920 is assumed to fly with one (experiment lifetime), so every MS621
# board is cased for both; the lid seats on the taller.
BATTERY_FAMILIES = {
    "MS621": (MS621F, MS920SE),
}


def cells_for(board) -> tuple:
    j = board.battery_pads
    if j is None:
        return ()
    try:
        return BATTERY_FAMILIES[j.name]
    except KeyError:
        raise KeyError("%s: no battery family for J401 footprint %r; declare cells= explicitly"
                       % (board.name, j.name)) from None


# ---------------------------------------------------------------------------
# Tag base: pogo pins, posts, alignment pins
# ---------------------------------------------------------------------------


class Pins(Enum):
    """Alignment-pin pairs, relative to J201, in case coordinates."""
    NARROW = ((-5.0, -6.5), (-5.0, 6.5))     # on every tag base
    WIDE = ((-8.5, -10.0), (-8.5, 10.0))     # double-screw (lipo) base only


@dataclass(frozen=True)
class TagBase:
    name: str
    pins: frozenset
    footprint: str
    # The 855-22-0XX-10-001101 drawing: tip 4.72 + 1.55 above the base PCB,
    # compressed by its 0.70 mid stroke.
    pogo_free_height: float = 6.27
    pogo_compression: float = 0.70
    pogo_window: tuple = (3.2, 7.0)
    screws: tuple = ((-5.0, -10.0), (-5.0, 10.0))
    insert_r: float = 1.65                    # press fit, 2-56 insert
    screw_r: float = 1.3                      # 2-56 clearance, in the lid
    pin_r: float = 0.75                       # press fit, 1/16" dowel
    pcb_thickness: float = 1.6

    @property
    def board_underside(self) -> float:
        """Height of the tag's underside above the base PCB top."""
        return self.pogo_free_height - self.pogo_compression

    @cache
    def pcb(self):
        return import_step(COMPONENTS / "tag-pins.step")

    @cache
    def connector(self):
        # Pins along model x, rows along model z, plungers along model +y;
        # the barrel shoulder (model y = -4.4196) sits on the base PCB top.
        return _axes((3, 1, 2), (1.4986, -3.3655, 4.4196)) * import_step(
            COMPONENTS / "mill-max-855-22-006-10-001101.step")

    @cache
    def dowel(self):
        return import_step(COMPONENTS / "dowel_pin.step")


SINGLE_PAIR = TagBase("single pair", frozenset({Pins.NARROW}),
                      "6pin_tagpoints_new_offset")
LIPO = TagBase("double screws (lipo)", frozenset({Pins.NARROW, Pins.WIDE}),
               "6pin_tagpoints_double_screws")
