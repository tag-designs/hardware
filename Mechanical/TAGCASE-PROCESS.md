# Making a tag case — process

How to make a base (adapter) and lid for a new tag. This is the process used
for `BitPresTagBMP585/` on 2026-10-12, written down so the next case can follow
it. Read `TAGCASES-general-principles.md` first: it says what a case must do.
This document says how to get there.

Start from `UIUCTag/`. It is the most complete case: it has interference
checks, a FreeCAD assembly of the real parts, the standard no-battery lid, and
a README that records every derived number. (`BitPresTagBMP585/` predates the
no-battery lid, the merged pogo-end pocket and the recentred markers.) Copy
the folder, rename the files, and work through the steps below.

## Tools

| | path |
|---|---|
| OpenSCAD 2021.01 | `~/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD` |
| FreeCAD 1.1 (headless) | `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd` |
| kicad-cli | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` |

None of these is on `PATH`. The Makefile in the case folder sets all three.

## 1. Identify the board and what already exists

- Check for sibling boards that share the outline. A `-alternate` or a
  revision may have identical geometry, in which case one case serves both.
  Compare the `board_geometry.py` output (step 2) of each.
- Check the existing cases in `Mechanical/*/`. **A case may already have been
  drawn for this board under another name.** `BitPresTag/BitPresTag.scad` turned
  out to be the BMP585 board, not the 17 mm BitPresTag. Compare the
  `board_nominal_len` and `pogo_center` values against the board.
- Note which tag base the case is for. If the case is for a single-pin-pair
  base, the alignment pins must be the (−5, ±6.5) pair (see step 3).

## 2. Extract the board geometry

```bash
python3 Mechanical/tools/board_geometry.py BoardDesigns/Tags/<board>/<board>.kicad_pcb
```

It prints the outline size, centre and thickness, and every footprint's origin
and courtyard extents, in **case coordinates**:

- x = KiCad x − centre, y = centre − KiCad y (KiCad's y runs down);
- +x should be the pogo/battery end. If J201 comes out at negative x, the
  board is drawn the other way round.
- z = 0 is the board underside.

What to take from it:

| scad parameter | from |
|---|---|
| `board_nominal_len`, `_width`, `board_thickness` | outline and thickness |
| `pogo_center` | J201 origin |
| `corner_hole_x`, `corner_hole_y` | J301–J304 origins (harness holes) |
| `bottom_parts_min`, `_max` | "B.Cu parts envelope" line |
| lid far-block x range | F.Cu extents near the far end (keep ≥ 0.25 clear) |
| J401 origin | where the cell's tabs are soldered (step 5) |

## 3. Mate to the base

The base side is fixed by two footprints in `BoardDesigns/kicad_libraries/lib_fp.pretty`.
In case coordinates, relative to `pogo_center`:

| feature | `6pin_tagpoints_new_offset` (single pair) | `_double_screws` (lipo) |
|---|---|---|
| screws / inserts | (−5, ±10) | (−5, ±10) |
| alignment pins | (−5, ±6.5) | (−5, ±6.5) and (−8.5, ±10) |

The mapping from footprint to case coordinates is case = pogo + (−fy, fx).

The (−5, ±6.5) pair exists on **every** base. The (−8.5, ±10) pair is
lipo-only, and the earlier `BitPresTag.scad` and `IMUTag.scad` used only that
pair. A board wider than about 11 mm puts (−5, ±6.5) inside the board groove;
that is what the second pair is for.

Keep these sizes, which are proven to press-fit:

- insert hole r 1.65;
- lid screw hole r 1.3;
- alignment pin hole r 0.75 (1/16″ dowel);
- pogo window 3.2 × 7.

**Pogo height.** The board underside sits at `6.27 − 0.70` above the base PCB
top. The 855-22-0XX-10-001101 drawing (`BoardDesigns/libraries/datasheets/855_10_001101_0.svg`)
gives the tip 4.72 + 1.55 = 6.27 above the PCB, and 0.70 is the datasheet
mid-stroke. The STEP model's insulator is drawn too tall, so do not take
heights from it.

## 4. Size the base around the tag

- **Board groove.** The board outline plus 0.038 (1.5 mil) per edge, to
  `base_extra_height` (1) above the underside.
- **Under-board pocket.** The B.Cu envelope plus 0.2, not "board minus a
  fixed ledge". This makes the ledges as wide as the parts allow.
  Depth 1.5 (tallest bottom part here 1.06).
- **Harness slots.** Each slot must fully cover its corner holes. Put the
  slot's −x edge just past the holes' −x edge (`harness_slot_margin` 0.1). At
  the far end that keeps the end ledge wide. Slots run the full base width
  (the thread may cross under the board).
- **No free-standing bar at the pogo end.** Run the pocket on into the pogo-end
  slot (`under_pocket_max` x = the slot centre). Stopping the pocket at the B.Cu
  envelope leaves a thin bar (1.14 × 1.5 on BitPresTagBMP585) between the
  pocket and the slot/pogo window, which does not print well and supports
  nothing. Designer, 2026-10-14.

## 5. The coin cell and the positive stop

The cell's position comes from its **tabs**, not from the footprint, which has
only two pads.

| cell (model in `BoardDesigns/libraries/packages3D`) | tab tip to cell centre | centre from J401 pad centre | rim radius in model |
|---|---|---|---|
| MS621F (`BatteryHolder_Seiko_MS621F.step`) | 5.9 | 5.0 | 3.68 |
| MS920SE-FL27E (`MS920SE-FL27E.STEP`) | 8.05 | 7.03 | 5.14 |

Both overhang the board end on BitPresTagBMP585. Size the relief for every cell
the board may carry: unregulated boards can take an MS920. Make it a hull over
the cells as soldered.

The **under-cell tab leaves the board edge flat at board-top height**. The
end-wall stop must therefore sit at or below the board top, and lower again
where the tabs cross (`battery_tab_notch_*`). A stop raised above the board top
collides with the tab. The FreeCAD check found this; the box model in the
OpenSCAD check did not.

## 6. The lid

The lid **floats on its screws**. It does not sit on the base posts, whose
tops are at z = 1, well below the lid.

- **Pogo-end block.** Bears on the cell's positive tab above the pogo pins,
  and sets the lid height. A drop of 2.1 keeps the screw stack the same as
  earlier lids.
- **Far block.** Bears on the board. Its drop is
  `pogo drop + cell stack height − gap`, with a gap of 0.2, so the pogo end
  always seats first. Gaps up to ~0.5 are fine, because the lid screw holes
  allow the tilt. Keep it clear of the corner holes (harness thread) and of
  F.Cu parts.
- **No-battery lid — standard on every case** (designer, 2026-10-14). Boards
  are tested on the base before their cell is fitted, so each case ships a
  second lid (`-D lid_no_battery=true`, `<case>-lid-nobattery.stl`). It keeps
  the version text on the crossbar and adds `TEST` on the lid body, between
  the far block and the crossbar; a suffix on the version text does not fit
  beside six characters. It sits a cell stack height lower than the standard
  lid, so **both end blocks are short**: the pogo-end block keeps the standard
  2.1 drop and bears on the board top directly over the pogo pads; the far
  block is 0.2 shorter so the pogo end seats first. Narrow the pogo-end block
  to stay 0.25 clear of the pogo-end harness holes, which it would otherwise
  cover. The screws run deeper into the through-inserts. Check it in both
  `make check` and `make assembly`, including its clearance to the tallest
  top-side part and to the dowel tops, which the lower lid comes close to.
  See `UIUCTag/UIUCTag.scad`.
- **Tag without a coin cell by design.** Both blocks bear on the board. See
  `IMUTag.scad` for the lipo case: the battery end must accommodate the
  battery thickness.

## 7. Text

Use Liberation Sans **Bold**, with `offset(delta=0.05)`, 0.8 deep. Earlier
regular-weight 2 mm text at 0.5 deep printed too thin.

The lid crossbar's flat top runs only |y| < 7 before the screw bosses rise, so
**about 13 mm of text fits**. At 2.6 mm bold that is six characters. Measure a
candidate string by exporting it to DXF:

```bash
echo 'offset(delta=0.05) text("BPT585", size=2.6, font="Liberation Sans:style=Bold", halign="center");' > t.scad
OpenSCAD -o t.dxf t.scad      # then take the x extent of the DXF points
```

Engrave the base text on the underside, mirrored with `mirror([1,0,0])` so it
reads from below.

**The `*` pogo-end markers.** The asterisk sits high in its em box: with
`valign="center"` it spans y −0.04s…+0.50s at size s, so a marker "centred" at
y = 7.0 actually ran to within 0.02 of the base edge. Recentre it on its real
extent (`translate([0, -0.229 * size])`), and place it by measured clearance:
keep ≥ 0.5 from every edge, including the battery-relief arc that cuts into the
base top beyond the board end, and from the lid's pogo end. Use size ≥ 3.5 on
the base and ≥ 5 on the lid. See `marker()` in `UIUCTag/UIUCTag.scad`.

## 8. Verify

Run both checks, in this order.

```bash
make check      # OpenSCAD: base/lid against a box model of the tag; fast
make assembly   # FreeCAD: base/lid against the real board, cells, base PCB,
                # pogo connector and dowel pins; prints overlaps and gaps
```

**`make check`** intersects the case with simple solids. It passes when OpenSCAD
reports "top level object is empty". **Run a negative control once** to prove
the check can fail. Override a parameter so a part must collide:

```bash
OpenSCAD -o neg.stl -D makechecks=true -D 'battery_stop_height=1.0' <case>.scad
```

**`make assembly`** is the real check. It runs `kicad-cli pcb export step
--include-pads --user-origin=<cx>x<cy>mm`, which gives the actual board with
every component model and the MS621. Then `assemble.py` builds the `.FCStd`
and reports. To reuse it for another board, change the constants at its top:

- `POGO`, `PIN_Y`, `J401_X`, `J201_PADS`;
- the cell list;
- the `--user-origin` in the Makefile.

Gotchas found while writing it:

- `Import.insert` gives each part its **local** placement. Use
  `o.getGlobalPlacement()`. `Part.read` flattens correctly but loses the part
  names.
- KiCad's STEP board body is thinner than nominal (0.31 + copper for a 0.4
  board), and bottom copper sits below z = 0. Shift so the lowest feature is
  at z = 0.
- Vendor models use arbitrary axes (the MS920 is y-up with tabs toward −z).
  Find the feet with a script before placing them, and check the placed bbox
  lands where expected. A sign error first put the MS920 over the board.
- OpenSCAD 2021 cannot export STEP, and the checks (`common`, `distToShape`)
  need solids, not meshes. Convert the STLs with `makeShapeFromMesh`, then
  `Part.Solid(Part.Shell(...))`, but use the result only for the checks: it
  has one planar face per triangle (6088 for the UIUCTag no-battery lid), so
  it is slow to draw and bloats the `.FCStd`. Put the case parts in the
  document as `Mesh::Feature` objects, moved exactly as the solids are, which
  is what a direct import gives.
- The lid's contact with the cell is zero-volume by construction, so report it
  but do not fail on it.

Then look at it. Render the parts:

```bash
OpenSCAD -o top.png --render --imgsize=1200,900 --camera=0,0,0,40,0,20,70 -D makelid=false <case>.scad
OpenSCAD -o bot.png --render --imgsize=1200,900 --camera=0,0,0,180,0,0,60 -D makelid=false <case>.scad
OpenSCAD -o lid.png --render --imgsize=1200,900 --camera=0,0,0,40,0,200,60 -D makebase=false -D lid_preview_z=0 <case>.scad
```

Renders caught the text running into the lid bosses and off the base. They
also caught the battery relief shaving a sliver off a side wall. Neither check
flags those.

## 9. Record it

The case README should have:

- the table of changes from the case it started from;
- every derived number with its source;
- the last `make assembly` results;
- a **Settled** section for decisions the designer has accepted, so the next
  review does not re-raise them.
