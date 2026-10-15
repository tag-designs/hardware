# Assemble the UIUCTag case with its key parts and check the fit.
#
#   make assembly        (exports the tag STEP from KiCad, then runs this)
#
# Run from this directory with freecadcmd. Builds UIUCTag-assembly.FCStd
# and prints interference volumes and gaps. Coordinates match the .scad:
# board-centred, +x toward the pogo/battery end, z = 0 at the board underside.
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

# Mirrors UIUCTag.scad.
POGO_FREE_HEIGHT = 6.27            # 855 drawing: 4.72 + 1.55 above base PCB top
POGO_H = POGO_FREE_HEIGHT - 0.7    # pogo_pin_height_at_board
POGO = (6.9, 0.0)
POST_X = POGO[0] - 5.0
PIN_Y = 6.5                        # single-pair base
LID_POGO_BLOCK_DROP = 2.1
BATTERY_STACK_HEIGHT = 2.7
LID_NB_POGO_BLOCK_DROP = 2.6       # lid_nb_pogo_block_drop: no-battery lid block, on the board
BASE_PCB_THICKNESS = 1.6

J401_X = 152.8 - 148.5             # J401 origin, case x; the cell lies toward +x
J201_PADS = [(POGO[0] + dx, dy) for dx in (-0.635, 0.635) for dy in (-1.27, 0, 1.27)]

TOL = 1e-3                         # mm^3; boolean noise on meshed solids

doc = App.newDocument("UIUCTag_assembly")


def add(name, shape, group=None, color=None, visible=True):
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
    # The fit checks need solids: common() and distToShape() do not work on a
    # mesh, and OpenSCAD 2021 cannot export STEP. Converting a mesh makes one
    # planar face per triangle, which is heavy to draw and to store, so the
    # document gets the mesh and only the checks use the solid.
    # removeSplitter() merges coplanar triangles (4992 faces to 1251 for the
    # UIUCTag base) without changing volume or distance, and halves the time
    # the checks take; curved walls stay faceted.
    m = Mesh.Mesh(path)
    s = Part.Shape()
    s.makeShapeFromMesh(m.Topology, 0.01)
    return m, Part.Solid(Part.Shell(s.Faces)).removeSplitter()


def moved_mesh(mesh, offset, matrix=None):
    # Mirrors the translate (and transformed()) applied to a case solid.
    m = mesh.copy()
    m.translate(*offset)
    if matrix is not None:
        m.transform(matrix)
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


# --- Tag: board, components and MS621 from KiCad ---------------------------

tmp = App.newDocument("tag_import")
Import.insert(os.path.join(HERE, "tag-board.step"), tmp.Name)
tag_parts = {}
for o in tmp.Objects:
    if o.TypeId == "Part::Feature" and o.Shape.Solids:
        s = o.Shape.copy()
        s.Placement = o.getGlobalPlacement()
        tag_parts[o.Label] = s
App.closeDocument(tmp.Name)

# KiCad puts the board body at z >= 0 with bottom copper below it. Shift so
# the lowest board feature sits on z = 0.
pcb_name = next(k for k in tag_parts if k.endswith("_PCB"))
pad_name = next(k for k in tag_parts if k.endswith("_pad"))
z_shift = -min(tag_parts[pcb_name].BoundBox.ZMin, tag_parts[pad_name].BoundBox.ZMin)
for k in tag_parts:
    tag_parts[k].translate(Vector(0, 0, z_shift))
board_top = tag_parts[pcb_name].BoundBox.ZMax

ms621 = tag_parts.pop("Seiko_MS621F")
tag_group = doc.addObject("App::DocumentObjectGroup", "Tag")
for k, s in tag_parts.items():
    add(k.replace("-", "_").replace(".", "_"), s, tag_group)
add("MS621", ms621, tag_group)
tag = Part.makeCompound(list(tag_parts.values()))
cell_floor = ms621.BoundBox.ZMin   # bottom of the solder feet

# --- MS920SE, soldered to the same J401 pads -------------------------------

# Model: thickness along +y, tabs toward -z, feet z -8.05..-6.0 centred on
# x = 0. Centre the feet on the J401 pads with the cell toward +x.
ms920_raw = step_shape(os.path.join(PACKAGES, "MS920SE-FL27E.STEP"))
foot_mid = -(8.05 + 6.0) / 2
ms920 = transformed(ms920_raw, axes_matrix(
    (3, 1, 2), (J401_X - foot_mid, 0, cell_floor)))
add("MS920SE_alternative", ms920, tag_group)

# --- Case -------------------------------------------------------------------

base_mesh, base = stl_part(os.path.join(HERE, "UIUCTag-base.stl"))
lid_mesh, lid_raw = stl_part(os.path.join(HERE, "UIUCTag-lid.stl"))
lid_nb_mesh, lid_nb_raw = stl_part(os.path.join(HERE, "UIUCTag-lid-nobattery.stl"))


def lid_z(cell):
    # The lid floats on its screws; the pogo-end block lands on the cell.
    return cell.BoundBox.ZMax + LID_POGO_BLOCK_DROP


def lid_on(cell):
    lid = lid_raw.copy()
    lid.translate(Vector(0, 0, lid_z(cell)))
    return lid


lid = lid_on(ms621)
add_mesh("Base", base_mesh)
add_mesh("Lid", moved_mesh(lid_mesh, (0, 0, lid_z(ms621))))

# No-battery lid, for a board without its cell: the pogo-end block lands on
# the board top. Shown displaced in y so it does not hide the standard lid.
lid_nb = lid_nb_raw.copy()
lid_nb.translate(Vector(0, 0, board_top + LID_NB_POGO_BLOCK_DROP))
add_mesh("Lid_no_battery", moved_mesh(lid_nb_mesh, (0, 0, board_top + LID_NB_POGO_BLOCK_DROP),
                                      axes_matrix((1, 2, 3), (0, 30, 0))))

# --- Base side: single-pair footprint PCB, pogo connector, dowel pins -------

base_group = doc.addObject("App::DocumentObjectGroup", "TagBase")
base_pcb = step_shape(os.path.join(COMPONENTS, "tag-pins.step"))
base_pcb.Placement = Placement(Vector(POGO[0], POGO[1], -POGO_H),
                               Rotation(Vector(0, 0, 1), -90))
add("BasePCB_6pin_tagpoints_new_offset", base_pcb, base_group)

# Pins along model x (columns), rows along model z, plunger axis model +y.
# The barrel shoulder (model y = -4.4196) sits on the base PCB top; the tip
# is then at POGO_FREE_HEIGHT above it, as the drawing gives.
pogo_raw = step_shape(os.path.join(COMPONENTS, "mill-max-855-22-006-10-001101.step"))
pogo = transformed(pogo_raw, axes_matrix(
    (3, 1, 2), (POGO[0] + 1.4986, POGO[1] - 3.3655, -POGO_H + 4.4196)))
add("Pogo_855_22_006", pogo, base_group)
plungers = [s for s in pogo.Solids if abs(s.BoundBox.ZMax - pogo.BoundBox.ZMax) < 1e-3]

dowel_raw = step_shape(os.path.join(COMPONENTS, "dowel_pin.step"))
dowels = []
for side in (-1, 1):
    d = dowel_raw.copy()
    d.translate(Vector(POST_X, side * PIN_Y,
                       -POGO_H - BASE_PCB_THICKNESS - dowel_raw.BoundBox.ZMin))
    dowels.append(d)
    add("DowelPin_%s" % ("neg" if side < 0 else "pos"), d, base_group)

doc.recompute()
doc.saveAs(os.path.join(HERE, "UIUCTag-assembly.FCStd"))

# --- Checks -----------------------------------------------------------------

fails = []


def vol(a, b):
    return a.common(b).Volume


def must_clear(label, a, b):
    v = vol(a, b)
    gap = a.distToShape(b)[0]
    ok = v < TOL
    print("  %-44s overlap %8.4f mm3  gap %.3f  %s" % (label, v, gap, "ok" if ok else "FAIL"))
    if not ok:
        fails.append(label)


print("\nBoard top %.3f (underside 0). Lid on MS621 at z %.3f, on MS920 at z %.3f."
      % (board_top, ms621.BoundBox.ZMax + LID_POGO_BLOCK_DROP,
         ms920.BoundBox.ZMax + LID_POGO_BLOCK_DROP))

for cell_name, cell in (("MS621", ms621), ("MS920SE", ms920)):
    bb = cell.BoundBox
    print("\n%s: x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f"
          % (cell_name, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    lid_c = lid_on(cell)
    must_clear("base vs board and components", base, tag)
    must_clear("base vs %s" % cell_name, base, cell)
    must_clear("lid vs board and components", lid_c, tag)
    v = vol(lid_c, cell)
    print("  %-44s overlap %8.4f mm3  (seated by construction)" % ("lid vs %s" % cell_name, v))
    far = lid_c.distToShape(tag_parts[pcb_name])[0]
    print("  %-44s %.3f" % ("lid far block to board top", far))

print("\nNo-battery lid, seated on the board top at z %.3f:" % (board_top + LID_NB_POGO_BLOCK_DROP))
must_clear("lid (no battery) vs board and components", lid_nb, tag)
must_clear("lid (no battery) vs base", lid_nb, base)
for d in dowels:
    must_clear("lid (no battery) vs dowel at y %+.1f" % d.BoundBox.Center.y, lid_nb, d)
u3 = next(s for k, s in tag_parts.items() if "BMP585" in k.upper() or "LGA9" in k.upper())
print("  %-44s %.3f" % ("lid (no battery) underside to U3 top", lid_nb.distToShape(u3)[0]))
pogo_zone = Part.makeBox(2.4, 12, 10, Vector(POGO[0] - 1.2, -6, board_top))
print("  %-44s %.3f" % ("pogo-end block to board top",
                         lid_nb.common(pogo_zone).distToShape(tag_parts[pcb_name])[0]))
print("  %-44s %.3f" % ("far block to board top",
                         lid_nb.common(Part.makeBox(3, 12, 10, Vector(-9.5, -6, board_top))).distToShape(tag_parts[pcb_name])[0]))
holes = [Part.makeCylinder(0.55, 2, Vector(5.78, s * 3.75, -0.5)) for s in (-1, 1)]
print("  %-44s %.3f" % ("pogo-end block to J301/J302 holes",
                         min(lid_nb.distToShape(h)[0] for h in holes)))

print("\nPogo pins (855, tip %.2f above board underside uncompressed):" % pogo.BoundBox.ZMax)
for p in plungers:
    c = p.BoundBox.Center
    dx, dy = min(((c.x - px, c.y - py) for px, py in J201_PADS),
                 key=lambda d: d[0] ** 2 + d[1] ** 2)
    print("  plunger at (%.3f, %.3f): %.3f from nearest J201 pad centre"
          % (c.x, c.y, (dx * dx + dy * dy) ** 0.5))
must_clear("pogo connector vs base", pogo, base)
must_clear("pogo connector vs bottom components", pogo,
           Part.makeCompound([s for k, s in tag_parts.items()
                              if s.BoundBox.ZMax <= z_shift + 1e-3 and k != pad_name]))

print("\nAlignment pins:")
for d in dowels:
    print("  dowel at y %+.1f: press-fit overlap with base %.3f mm3"
          % (d.BoundBox.Center.y, vol(d, base)))
    must_clear("dowel vs tag", d, tag)
    must_clear("dowel vs lid", d, lid)

# Positive stop: gap from the board's battery-end edge to the end wall, and
# how high that wall stands at the board edge.
BOARD_END_X = 9.5                  # half of the 19 mm board
end_zone = Part.makeBox(10, 40, 20, Vector(BOARD_END_X - 0.1, -20, -10))
end_wall = base.common(end_zone)
print("\nBattery-end stop: board edge to end wall %.3f, wall top z %.3f (board top %.3f)"
      % (tag_parts[pcb_name].distToShape(end_wall)[0],
         end_wall.common(Part.makeBox(0.3, 8, 20, Vector(BOARD_END_X, -4, -10))).BoundBox.ZMax,
         board_top))

print("\n%s" % ("ALL CLEAR" if not fails else "FAILED: " + ", ".join(fails)))
