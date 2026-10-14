# UIUCTag tag case

Base (adapter), standard lid and no-battery lid for `BoardDesigns/Tags/UIUCTag`
(19 × 10 mm), for the single-pin-pair tag base (`6pin_tagpoints_new_offset`).

```
make            # UIUCTag-base.stl, UIUCTag-lid.stl, UIUCTag-lid-nobattery.stl
make check      # quick OpenSCAD interference check against a box model of the tag
make assembly   # full fit check in FreeCAD against the real parts (see below)
```

`make check` also fails on any OpenSCAD `WARNING`. To see the parts assembled,
with the tag drawn as simple solids, run `-D makeassembly=true`; add
`-D lid_no_battery=true` for the second lid.

Coordinates are board-centred, with +x toward the pogo/battery end. Case
x = KiCad x − 148.5, case y = 108 − KiCad y, and z = 0 is the board underside.

## Relation to `Mechanical/BitPresTagBMP585`

UIUCTag is BitPresTagBMP585 with the ADXL367 replaced by the larger ADXL362,
and the board's far (non-pogo) end extended 1 mm to make room for it. Relative
to J201 nothing else moved, so this case starts from that one and changes:

| | BitPresTagBMP585 | here | why |
|---|---|---|---|
| Board | 18 × 10, centre KiCad x 149 | 19 × 10, centre x 148.5 | Far edge moved 1 mm; J201 is now at case x 6.9, J401 at 4.3 |
| Far harness holes | x −7.57 | x −8.07 | J303/J304 moved with the edge |
| B.Cu envelope | x −7.21…3.29 | x −8.22…3.79 | ADXL362 (U2) is 3.25 × 3.0 × 1.06, its courtyard 0.65 past the body on the far side |
| Pogo-end pocket edge | B.Cu envelope + 0.2 (x 3.49 → bar to slot) | runs on to the slot centre | Removes a free-standing 1.14 × 1.5 bar between the pocket and the slot/pogo window that does not print well (designer, 2026-10-14) |
| Lid far block | x −8.75…−7.0 | x −9.25…−7.82 | 0.25 in from the board end, 0.25 clear of C7 (now x −7.57). The parent's position lands on C7 |
| Top-side parts model | — | C7, C404, C6 re-placed; Q501 on F.Cu; C8 gone | From `board_geometry.py` |
| `*` markers | size 3 base / 4 lid, glyph not recentred | size 3.5 base / 5 lid, recentred on the real glyph | The parent's base marker reached 0.02 from the base edge, its lid marker ran 0.17 past the lid end (designer, 2026-10-14) |
| No-battery lid | none | `UIUCTag-lid-nobattery.stl` | For testing a board before its cell is fitted; now standard on every case (designer, 2026-10-14) |
| Text | `BPT585` | `UIUC` on both lids; the no-battery lid adds `TEST` on the lid body | A `-T` suffix does not fit beside six characters; the lid body has room |

Unchanged: base block and margins, pogo window and height (6.27 − 0.70 mid
stroke), posts, insert and screw holes, alignment pins (−5, ±6.5), crossbar and
boss reinforcement, battery relief and positive stop, text font and depth.

## Derived geometry

- **Coin cell.** Centres from the tabs soldered to J401 (x 4.3): MS621F at
  x 9.3, MS920SE-FL27E at x 11.33. Relief is the hull of both rims + 0.4.
- **Far-end ledge.** The board rests on 0.78 mm of base between the board
  groove (x −9.54) and the far harness slot (x −8.72), as on the parent. With
  the pocket sized from U2's courtyard it would have been 1.08; the slot is the
  limit.
- **Bottom-side parts.** Envelope x −8.22…3.79, y −3.95…3.92, up to 1.06 deep
  (U2; its KiCad model is 1.14). The 1.5 pocket depth leaves 0.36.
- **Markers.** The base `*` (size 3.5) is centred between the battery-relief
  arc (y 5.54) and the base edge (y 8.54), 0.54 from each and 1.1 from the
  base end. The lid `*` (size 5) sits 0.9 in from the lid's pogo end, about 1
  clear of the lid text. `marker()` recentres the glyph: with `valign="center"`
  an asterisk spans y −0.04s…+0.50s.
- **Standard lid.** Floats on its screws; the pogo-end block (drop 2.1) bears on
  the cell's positive tab above the pogo pins; the far block is longer by the
  2.7 cell stack minus a 0.2 gap, so the pogo end seats first.
- **No-battery lid.** Sits 2.3 lower, so both end blocks are short: the
  pogo-end block (drop 2.6) bears on the board top directly above J201, and the
  far block is 0.2 shorter. 2.6 rather than the standard 2.1, because at 2.1
  the lid underside cleared U3 (BMP585) by 0.055 and the dowel tops by 0.095.
  The pogo-end block is narrowed to |y| < 2.95 to stay clear of the J301/J302
  harness holes. Same screws; they run 2.3 further into the through-inserts.

## Checks

`make check` passes (both lids, no warnings). Negative controls, each of which
must produce geometry:

| override | result |
|---|---|
| `battery_stop_height=1.0` (stop above the board top) | collides |
| `lid_far_block_x=[-8.75,-7.0]` (the parent's far block) | collides with C7 |
| `lid_nb_pogo_block_drop=1.9` (no-battery lid lowered) | collides with U3 |
| `-D lid_nb_far_block_drop=nope` (undefined value) | fails on the WARNING |

`under_pocket_min` at the parent's −7.41 does **not** collide, and that is
correct: the far harness slot (x −8.72…−6.22, from z −1.5) already clears the
region where U2 overhangs the old pocket.

`make assembly` (FreeCAD, against KiCad's STEP of the board with every
component, both cells, the base PCB, the 855 connector and the dowels). Last
run, 2026-10-14: **ALL CLEAR**.

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

U2 clears the base by 0.315, C7 the standard lid's far block by 0.445, C404 by
1.295. The pogo plungers land on the J201 pad centres with 0.70 compression;
the connector clears the pogo window by 0.10. The battery-end stop wall is
0.038 from the board edge and reaches z 0.35, the board top in the KiCad model.

## Settled

- **Lid far block gap.** 0.29 (MS621) and 0.44 (MS920) above the board; screw
  tension closes it by tilting the lid, as on BitPresTagBMP585 (accepted there
  2026-10-12).
- **No-battery lid block length.** 2.6, not 2.1, for the U3 and dowel
  clearances above. The designer asked for end blocks "more like the battery
  end length" of the standard lid; 2.6 against the standard lid's 2.1 / 4.6.
- **Footprint on the tag base.** The base block extends 1 mm further from the
  pogo pins at the far end than the BitPresTagBMP585 case did (the board is
  1 mm longer). Not checked against the tag bases' own layouts.
