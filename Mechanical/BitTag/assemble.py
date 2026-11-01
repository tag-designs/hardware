# Assemble the BitTag-family case with every board it serves and check the fit.
#
#   make assembly        (exports the tag STEPs from KiCad, then runs this)
#
# Run from this directory with freecadcmd. Builds BitTag-assembly.FCStd and
# prints interference volumes and gaps. Coordinates match BitTag.scad: centred
# on J201, +x toward the tongue/cell end, z = 0 at the board underside.
import os
import FreeCAD as App
import Import
import Mesh
import Part
from FreeCAD import Matrix, Placement, Rotation, Vector

HERE = os.getcwd()
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
COMPONENTS = os.path.join(REPO, "Mechanical", "Components")
PACKAGES = os.path.join(REPO, "BoardDesigns", "libraries", "packages3D")

# Mirrors BitTag.scad.
POGO_FREE_HEIGHT = 6.27            # 855 drawing: 4.72 + 1.55 above base PCB top
POGO_MAX_STROKE = 1.40
INSULATOR_BOTTOM = 0.51            # floats on the pin collars
INSULATOR_TOP = 0.51 + 3.78        # the STEP model's insulator is drawn too tall
INSULATOR = (3.0, 6.73)
POST_X = -5.0
POST_Y = 10.0
POST_TOP = 1.0                     # base_top_z
PIN_Y = 6.5
BASE_PCB_THICKNESS = 1.6
LID_NB_DROP = 2.4                  # lid_nb_pogo_block_drop
LID_DROP = 2.85 + 0.2              # lid_pogo_block_drop: MS920 stack + gap
BLOCK = ((-0.9, 0.9), (-2.375, 2.375))  # lid_pogo_block_x, +-lid_pogo_block_halfwidth
FAR_BLOCK = ((-10.885, -9.35), (-2.3, -1.43))
INSERT_PROUD_ALLOWANCE = 1.0

BASES = {
    "deep": ("BitTag-base.stl", 1.0),
    "prestagv6": ("BitTag-base-prestagv6.stl", 0.8),
}
# step, J401 x (cell tab pads), the bases it is checked on
BOARDS = [
    ("BitTagv7", "tag-BitTagv7.step", 0.17, ["deep", "prestagv6"]),
    ("BitTagNG", "tag-BitTagNG.step", 0.38, ["deep", "prestagv6"]),
    ("PresTag", "tag-PresTag.step", 0.17, ["deep", "prestagv6"]),
    ("PresTag_v5", "tag-PresTag-v5.step", 0.17, ["deep", "prestagv6"]),
    ("PresTag_v6", "tag-PresTag-v6.step", 0.17, ["prestagv6"]),
]

TOL = 1e-3                         # mm^3; boolean noise on meshed solids

doc = App.newDocument("BitTag_assembly")
fails = []


def add(name, shape, group=None):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    if group:
        group.addObject(o)
    return o


def add_mesh(name, mesh, group=None):
    o = doc.addObject("Mesh::Feature", name)
    o.Mesh = mesh
    if group:
        group.addObject(o)
    return o


def stl_part(path):
    # The checks need solids; the document gets the mesh (UIUCTag/assemble.py).
    m = Mesh.Mesh(path)
    s = Part.Shape()
    s.makeShapeFromMesh(m.Topology, 0.01)
    return m, Part.Solid(Part.Shell(s.Faces)).removeSplitter()


def moved_mesh(mesh, offset):
    m = mesh.copy()
    m.translate(*offset)
    return m


def step_shape(path):
    s = Part.Shape()
    s.read(path)
    return s


def transformed(shape, matrix):
    s = shape.copy()
    s.transformShape(matrix, True)
    return s


def axes_matrix(rows, offset):
    """rows[i] gives output axis i as a signed input-axis index (1=x, 2=y, 3=z)."""
    m = Matrix()
    vals = [[0.0] * 3 for _ in range(3)]
    for i, r in enumerate(rows):
        vals[i][abs(r) - 1] = 1.0 if r > 0 else -1.0
    m.A11, m.A12, m.A13 = vals[0]
    m.A21, m.A22, m.A23 = vals[1]
    m.A31, m.A32, m.A33 = vals[2]
    m.A14, m.A24, m.A34 = offset
    return m


def vol(a, b):
    return a.common(b).Volume


def must_clear(label, a, b, min_gap=0.0):
    v = vol(a, b)
    gap = a.distToShape(b)[0]
    ok = v < TOL and gap >= min_gap - 1e-6
    print("    %-48s overlap %8.4f mm3  gap %.3f  %s" % (label, v, gap, "ok" if ok else "FAIL"))
    if not ok:
        fails.append(label)
    return gap


def top_under(shape, rect):
    """Highest point of `shape` inside the xy rectangle ((x0, x1), (y0, y1))."""
    (x0, x1), (y0, y1) = rect
    c = shape.common(Part.makeBox(x1 - x0, y1 - y0, 40, Vector(x0, y0, -20)))
    return c.BoundBox.ZMax if c.Solids else None


# --- Case parts --------------------------------------------------------------

bases = {k: stl_part(os.path.join(HERE, f)) + (c,) for k, (f, c) in BASES.items()}
lid_mesh, lid_raw = stl_part(os.path.join(HERE, "BitTag-lid.stl"))
lid_nb_mesh, lid_nb_raw = stl_part(os.path.join(HERE, "BitTag-lid-nobattery.stl"))

base_pcb_raw = step_shape(os.path.join(COMPONENTS, "tag-pins.step"))
pogo_raw = step_shape(os.path.join(COMPONENTS, "mill-max-855-22-006-10-001101.step"))
dowel_raw = step_shape(os.path.join(COMPONENTS, "dowel_pin.step"))
ms920_raw = step_shape(os.path.join(PACKAGES, "MS920SE-FL27E.STEP"))


def base_side(seat):
    """Tag-base PCB, 855 connector, drawing insulator and dowels for a seat height."""
    pcb = base_pcb_raw.copy()
    pcb.Placement = Placement(Vector(0, 0, -seat), Rotation(Vector(0, 0, 1), -90))
    # Barrel shoulder (model y = -4.4196) on the base PCB top: tip at 6.27.
    pogo = transformed(pogo_raw, axes_matrix((3, 1, 2), (1.4986, -3.3655, -seat + 4.4196)))
    insulator = Part.makeBox(INSULATOR[0], INSULATOR[1], INSULATOR_TOP - INSULATOR_BOTTOM,
                             Vector(-INSULATOR[0] / 2, -INSULATOR[1] / 2, -seat + INSULATOR_BOTTOM))
    dowels = []
    for side in (-1, 1):
        d = dowel_raw.copy()
        d.translate(Vector(POST_X, side * PIN_Y, -seat - BASE_PCB_THICKNESS - dowel_raw.BoundBox.ZMin))
        dowels.append(d)
    return pcb, pogo, insulator, dowels


def load_tag(step):
    tmp = App.newDocument("tag_import")
    Import.insert(os.path.join(HERE, step), tmp.Name)
    parts = {}
    for o in tmp.Objects:
        if o.TypeId == "Part::Feature" and o.Shape.Solids:
            s = o.Shape.copy()
            s.Placement = o.getGlobalPlacement()
            parts[o.Label] = s
    App.closeDocument(tmp.Name)
    # KiCad puts the board body at z >= 0 with bottom copper below it. Shift so
    # the lowest board feature sits on z = 0.
    pcb_name = next(k for k in parts if k.endswith("_PCB"))
    pad_name = next(k for k in parts if k.endswith("_pad"))
    z_shift = -min(parts[pcb_name].BoundBox.ZMin, parts[pad_name].BoundBox.ZMin)
    for s in parts.values():
        s.translate(Vector(0, 0, z_shift))
    return parts, pcb_name, pad_name, z_shift


# --- Each board --------------------------------------------------------------

for name, step, j401_x, base_keys in BOARDS:
    parts, pcb_name, pad_name, z_shift = load_tag(step)
    group = doc.addObject("App::DocumentObjectGroup", name)
    pcb = parts[pcb_name]
    board_top = max(pcb.BoundBox.ZMax, parts[pad_name].BoundBox.ZMax)
    cells = [k for k in parts if k.startswith("Seiko_MS621F")]
    ms621 = parts[cells[0]]
    for k in cells:                # some footprints carry the model twice
        parts.pop(k)
    tag = Part.makeCompound(list(parts.values()))
    bottom = Part.makeCompound([s for k, s in parts.items()
                                if s.BoundBox.ZMax <= z_shift + 1e-3 and k != pad_name])
    # MS920SE on the same J401 pads (model: thickness +y, tabs -z, feet z
    # -8.05..-6.0 centred on x = 0).
    foot_mid = -(8.05 + 6.0) / 2
    ms920 = transformed(ms920_raw, axes_matrix((3, 1, 2), (j401_x - foot_mid, 0, ms621.BoundBox.ZMin)))

    for k, s in parts.items():
        add("%s_%s" % (name, k.replace("-", "_").replace(".", "_")), s, group)
    add(name + "_MS621", ms621, group)
    add(name + "_MS920SE", ms920, group)

    print("\n=== %s: board top %.3f, MS621 top %.3f, MS920 top %.3f"
          % (name, board_top, ms621.BoundBox.ZMax, ms920.BoundBox.ZMax))

    for bk in base_keys:
        base_mesh, base, compression = bases[bk]
        seat = POGO_FREE_HEIGHT - compression
        pcb_b, pogo, insulator, dowels = base_side(seat)
        print("  -- on %s base (seat %.2f, compression %.2f of %.2f max):"
              % (bk, seat, compression, POGO_MAX_STROKE))
        must_clear("base vs board and components", base, tag)
        must_clear("base vs MS621", base, ms621)
        must_clear("base vs MS920SE", base, ms920)
        must_clear("pogo insulator (drawing) vs bottom parts", insulator, bottom, 0.1)
        must_clear("pogo connector (model) vs base", pogo, base)
        for d in dowels:
            must_clear("dowel at y %+.1f vs tag" % d.BoundBox.Center.y, d, tag)
        dowel_top = max(d.BoundBox.ZMax for d in dowels)

        # Lids: each seats where its pogo block first meets the tag.
        poses = [("no-battery lid", lid_nb_raw, LID_NB_DROP, tag, None)]
        for cname, cell in (("MS621", ms621), ("MS920SE", ms920)):
            poses.append(("battery lid, %s" % cname, lid_raw, LID_DROP,
                          Part.makeCompound([tag, cell]), cell))
        for label, lid_raw_shape, drop, contact, cell in poses:
            seat_z = top_under(contact, BLOCK)
            z = seat_z + drop
            lid = lid_raw_shape.copy()
            lid.translate(Vector(0, 0, z))
            print("    %s: block on z %.3f, lid underside z %.3f, %.3f above the post tops"
                  % (label, seat_z, z, z - POST_TOP))
            must_clear("%s vs board and components" % label,
                       lid, tag.cut(Part.makeBox(1.8, 4.75, 40, Vector(-0.9, -2.375, -20))))
            if cell is not None:
                # The block rests on the cell's tab foot, and the tab rises to
                # the cell top by x ~1.5; leave that out so the gap reported is
                # the lid's clearance over the cell itself.
                must_clear("%s vs cell (tab excluded)" % label, lid,
                           cell.cut(Part.makeBox(3.6, 20, 40, Vector(-2.0, -10, -20))), 0.2)
            must_clear("%s vs base" % label, lid, base)
            for d in dowels:
                must_clear("%s vs dowel at y %+.1f" % (label, d.BoundBox.Center.y), lid, d)
            proud = Part.makeCompound([Part.makeCylinder(3.0, INSERT_PROUD_ALLOWANCE,
                                                         Vector(POST_X, s * POST_Y, POST_TOP))
                                       for s in (-1, 1)])
            must_clear("%s vs inserts %.1f proud" % (label, INSERT_PROUD_ALLOWANCE), lid, proud, 0.5)
            # Probe inset 0.05 from the block's faces: a box flush with them
            # gives an empty common.
            far = lid.common(Part.makeBox(FAR_BLOCK[0][1] - FAR_BLOCK[0][0] - 0.1,
                                          FAR_BLOCK[1][1] - FAR_BLOCK[1][0] - 0.1, 20,
                                          Vector(FAR_BLOCK[0][0] + 0.05, FAR_BLOCK[1][0] + 0.05, -5)))
            print("      %-46s %.3f" % ("far block to board top", far.BoundBox.ZMin - board_top))

        if bk == base_keys[0]:
            add_mesh("%s_Base_%s" % (name, bk), base_mesh, group)
            add_mesh("%s_Lid" % name, moved_mesh(lid_mesh, (0, 0, top_under(Part.makeCompound([tag, ms621]), BLOCK) + LID_DROP)), group)
            add("%s_BasePCB" % name, pcb_b, group)
            add("%s_Pogo" % name, pogo, group)
            for i, d in enumerate(dowels):
                add("%s_Dowel%d" % (name, i), d, group)
        print("    dowel tops z %.3f; insulator top z %.3f" % (dowel_top, -seat + INSULATOR_TOP))

    # Shoulder stop: the body shoulder at x 2.365 is the battery-end stop on
    # every board. Report its gap and wall height at the board edge.
    base = bases[base_keys[0]][1]
    wall = base.common(Part.makeBox(0.5, 4, 10, Vector(2.38, 2.6, -5)))
    print("  shoulder stop: board edge to wall %.3f, wall top z %.3f (board top %.3f)"
          % (pcb.distToShape(wall)[0], wall.BoundBox.ZMax, board_top))

doc.recompute()
doc.saveAs(os.path.join(HERE, "BitTag-assembly.FCStd"))
print("\n%s" % ("ALL CLEAR" if not fails else "FAILED: " + ", ".join(fails)))
