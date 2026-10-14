# BitPresTagBMP585 tag case

Base (adapter), standard lid and no-battery lid for
`BoardDesigns/Tags/BitPresTagBMP585`. Also fits `BitPresTagBMP585-alternate`:
its outline and every footprint position are identical.

```
make            # BitPresTagBMP585-base.stl, -lid.stl, -lid-nobattery.stl
make check      # quick OpenSCAD interference check against a box model of the tag
make assembly   # full fit check in FreeCAD against the real parts (see below)
```

To see the parts assembled, with the tag drawn as simple solids, run
`-D makeassembly=true`.

Coordinates are board-centred, with +x toward the pogo/battery end. Case
y = 108 − KiCad y, and z = 0 is the board underside.

## Relation to `Mechanical/BitPresTag`

That case was drawn on this board's 18 × 10 outline (x 140–158), with J201 at
x = 6.4 and the BMP585 board in its FreeCAD assembly. It does not fit the
17 mm `Tags/BitPresTag`. This case starts from it and from `IMUTag.scad`, and
changes the following, per `TAGCASES-general-principles.md`:

| | `BitPresTag.scad` | here | why |
|---|---|---|---|
| Alignment pins | (−8.5, ±10) only | (−5, ±6.5) | This adapter is for a single-pin-pair base (`6pin_tagpoints_new_offset`). The old pair exists only on the double-screw (lipo) base. `enable_lipo_alignment_pins` adds it back. |
| Pogo-end harness slot | x 5.79–8.29 | x 4.63–7.13 | The old slot missed J301/J302 (x 4.73–5.83) by all but 0.04 mm. Each slot now covers its holes completely. |
| Under-board pocket | board − 0.75 per side | B.Cu courtyards + 0.2 | Long-side ledges grow from 0.75 to 0.89/0.92, and a 1.14 mm support bar now sits between the pocket and the pogo-end slot. |
| Battery relief | Ø10.5 at x = 11.45, from z 0.4 | hull of MS621 and MS920 as soldered, from z 0.35, notched to 0.25 under the tabs | A full-width shelf beyond the board end gives the battery end a positive stop. |
| Lid far block | full width, x −8.54…−6.54 | 5.2 wide, x −8.75…−7.0 | Clears J303/J304 (harness thread) in y, and C7/C8 in x (it was 0.01 mm from C7). |
| Text | regular, 2.0, 0.5–0.6 deep | bold +0.05 stroke, 2.6 lid / 3.0 base, 0.8 deep | The old text printed too thin. |

The following are unchanged: base block and margins, pogo window and height
(6.27 − 0.70 mid stroke), posts, insert and screw hole sizes, alignment pin hole
size, the crossbar and boss reinforcement, and the lid crossbar and body.

## 2026-10-14: brought up to the UIUCTag standard

The case-design rules settled on `Mechanical/UIUCTag` were applied here. The
`.scad` was regenerated from `UIUCTag.scad` with this board's parameters
restored (outline, holes, cell centres, pogo position, B.Cu envelope, far block
and top-side parts all unchanged), so the two files differ only in those
parameters.

| | before | now | why |
|---|---|---|---|
| No-battery lid | none | `BitPresTagBMP585-lid-nobattery.stl` | For testing a board before its cell is fitted. Sits 2.3 lower; the pogo-end block (drop 2.6, 5.9 wide) bears on the board over J201 and the far block is 0.2 shorter. Keeps `BPT585` and adds `TEST` on the lid body. Same screws |
| Pogo-end pocket | stopped at the B.Cu envelope (x 3.49) | runs on to the slot centre | Removes the free-standing 1.14 × 1.5 bar between the pocket and the slot/pogo window, which does not print well |
| Base `*` | size 3 at (11.3, 7.0), glyph not recentred: reached y 8.52 against an 8.54 edge | size 3.5, recentred, 0.54 from the edge and the battery-relief arc | Printability |
| Lid `*` | size 4 at x 6.4: ran 0.17 past the lid end | size 5, recentred, 0.9 in from the lid end | Printability |
| `make check` | interference only | also fails on any OpenSCAD `WARNING` | An undefined variable once silently dropped a lid block |

## Derived geometry

- **Coin cell.** The cell sits wherever its tabs, soldered to the J401 pads,
  put it. The feet end 5.9 mm from the cell centre on the MS621F and 8.05 mm on
  the MS920SE-FL27E, so the centres land at x = 8.8 and 10.83. Both overhang
  the pogo-end board edge. The relief is a hull over the two, using the model
  rims (r 3.68 and 5.14) plus 0.4 clearance.
- **Positive stop.** Beyond the board end the base keeps a shelf up to z 0.35,
  so the board edge stops against a full-width wall. The under-cell tab leaves
  the board edge flat at board-top height. Where the tabs cross (|y| < 1.5) the
  shelf is therefore 0.25. The earlier draft raised the stop 0.1 above the
  board top, and the FreeCAD check showed the tab hitting it.
- **Bottom-side envelope.** x −7.21…3.29, y −3.95…3.92 (courtyards), up to 1.06
  deep (U2). The pocket depth of 1.5 leaves 0.44.
- **Lid.** The lid floats on its screws, as the earlier lids do. The pogo-end
  block bears on the cell's positive tab directly above the pogo pins, and sets
  the lid height. Its 2.1 drop is the old lid's, so the same screws reach. The
  far block is longer by the cell stack height (2.7, from the MS621F model) minus
  a 0.2 gap, so the pogo end always seats first and screw tension closes the gap.

## FreeCAD fit check

`make assembly` exports `tag-board.step` from the `.kicad_pcb` with
`kicad-cli`, which brings in the board, its components and the MS621F. It then
runs `assemble.py`, which builds `BitPresTagBMP585-assembly.FCStd` from these
parts:

- base and lid STLs, with the lid seated on the cell;
- the board, plus `MS920SE-FL27E.STEP` as the alternative cell on the same pads;
- the base side, single-pair `tag-pins.step` with the 855 connector placed from
  the drawing (tip 6.27 above the base PCB top);
- the dowel pins.

It reports overlaps and gaps. Last run, 2026-10-14: **ALL CLEAR**.

| | MS621 | MS920SE | no battery |
|---|---|---|---|
| base vs board and components | clear, 0.038 | clear, 0.038 | — |
| base vs cell | clear, 0.185 | clear, 0.185 | — |
| lid vs board and components | clear | clear | clear (pogo block seated, 0.000) |
| lid far block to board top | 0.285 | 0.435 | 0.200 |
| lid vs base | — | — | 0.288 |
| lid vs dowels | 2.880 | 2.880 | 0.595 |
| lid underside to U3 | — | — | 0.555 |
| lid pogo block to J301/J302 holes | — | — | 0.259 |

The pogo plungers land on the J201 pad centres, with 0.70 compression. The
connector clears the pogo window by 0.10. The dowels clear the tag (0.71) and
the lid (2.9). The battery-end stop wall reaches z 0.35, the board top in the
KiCad model.

## Settled

- **Lid far block gap.** It stops 0.29 short of the board with an MS621 fitted,
  and 0.44 short with an MS920. Screw tension closes the gap by tilting the
  lid slightly, which the lid screw-hole clearance allows. Accepted as is,
  2026-10-12.
- **No-battery lid block length** 2.6, not the standard lid's 2.1: at 2.1 the
  lowered lid clears U3 by 0.055 and the dowel tops by 0.095 (measured on
  UIUCTag, same geometry here). Settled 2026-10-14.
