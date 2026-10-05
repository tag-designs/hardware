# tagcase_param.py — one core model for the pogo-pin tag cases

`Mechanical/tagcase_param.py` builds the base + lid case for a board from a
JSON variant file. It covers `BitPresTag.scad` and `CompassTagv1.scad` from the
same feature tree; a new board is a new variant file.

```
freecadcmd tagcase_param.py -- --params CompassTag/CompassTagv1.json --stl
freecadcmd tagcase_param.py -- --params BitPresTag/BitPresTag.json --stl
```

Inside the GUI: `exec(open('.../tagcase_param.py').read())`, then
`build(*load_variant('.../CompassTagv1.json'))`.

A variant file is spreadsheet cells plus, under `_`-prefixed keys, the output
settings — so one file fully describes a board:

```json
{ "_doc_name": "CompassTagv1_param",
  "_out": "CompassTagv1-param.FCStd",
  "_stl_prefix": "CompassTagv1-fc",
  "name": "CTagV1",
  "board_nominal_len": "17.9 mm", ... }
```

`_out` is resolved relative to the variant file, so each board's document lands
in its own folder. An unknown parameter name is rejected rather than silently
ignored. Values are cell contents: `"17.9 mm"` is a quantity,
`"=0.002 * 25.4 mm"` a formula, so a variant can override a *relationship* as
well as a number (CompassTag does exactly that for `battery_x`).

## Was parameterization enough for CompassTag?

Almost. Roughly 25 values differ and were already parameters or trivially
became ones. But three things were genuine topology differences, and one was a
formula that had constants baked into it. All four are now part of the core
model:

**1. The base crossbar.** `CompassTag.scad` uses the plain `makeCrossBar` — a
solid bar joining the two post bosses. `BitPresTag.scad` has that bar
commented out and instead adds a second boss pair plus a web between them.
Same role, different structure. The core model has all three as separate pads.

**2. A rectangular battery-end relief.** CompassTag cuts a 5 × 7 pocket next
to the round battery relief; BitPresTag has no equivalent. Added as
`battery_end_pocket`.

**3. Which of those exist is now a spreadsheet value, not a script decision.**
PartDesign's `Suppressed` property accepts an expression, so each optional
feature is bound to a flag cell:

| flag | BitPresTag | CompassTag |
|---|---|---|
| `enable_base_crossbar` | 0 | 1 |
| `enable_post_boss_aux` | 1 | 0 |
| `enable_post_web` | 1 | 0 |
| `enable_battery_pocket` | 1 | 1 |
| `enable_battery_end_pocket` | 0 | 1 |

Flip a cell in the GUI and the feature appears or disappears — no rebuild. The
build log reports what got suppressed.

**4. The lid end blocks had constants folded into their Z formulas.** In the
`.scad` sources the two blocks are positioned with literal offsets that differ
between the designs, so these are now named:

| | BitPresTag | CompassTag |
|---|---|---|
| `lid_left_end_drop` | 2.1 (was `eps + 2`) | 1.8 |
| `lid_pogo_end_z_shift` | −0.1 (was `-eps`) | +0.5 |
| `lid_pogo_end_extra` | +0.1 (was `+eps`) | −1 |

The pogo end block sits `-lid_end_height/2 + z_shift` and is
`lid_end_height + extra` tall; the left block hangs `lid_left_end_drop` below
`-lid_end_height/2`. `eps` no longer appears in either, so the two designs are
now the same formula with different numbers.

Also newly named, because they were literals that differ:
`base_extra_height` (base height above the board underside: 1 vs 2),
`base_crossbar_width`, and the battery-relief position formula.

## What is identical between the two boards

Everything else, which is most of it: the base block and its margins, the
under-board pocket and ledges, the harness slots and their placement formula,
the PCB clearance sweep, the pogo window, the alignment-pin pair, the insert
and screw holes, the post bosses, the whole lid body/crossbar/end-block
topology, and all four engravings. Two things that looked like differences
turned out not to be: `CompassTag`'s `makePCB()` subtracts two `lip_rad`
cylinders that are exactly tangent to the PCB cube and remove zero volume (the
`lip` code they belonged to is commented out), and both designs' harness-slot
"cleanup" fillets sit outside the base wall and remove nothing.

## Adding a board

Copy a variant file, change the identity and the numbers, run it. In practice
what you need from a new PCB is: `board_nominal_len` / `_width`,
`board_edge_clearance`, `pogo_center_x/y`, `alignment_pin_dx/dy`, the battery
relief position and size, and `base_extra_height` for the board stack. Then
decide the five feature flags. If a board needs geometry that is in neither
design, add the pad/pocket to `build_base` / `build_lid` with an `enable=`
flag — existing boards are unaffected because their flag defaults to 0.

## Verification

Both variants were compared against their OpenSCAD STLs by vertical-ray column
integration on a 0.15 mm grid — per-column symmetric difference, not just
total volume.

| | volume (OpenSCAD → FreeCAD) | bbox | differing columns | exceeding engraving depth |
|---|---|---|---|---|
| BitPresTag base | 2678.166 → 2678.085 | identical | 348 / 30 102 | 0 |
| BitPresTag lid | 858.989 → 858.894 | identical | 550 / 18 338 | 0 |
| CompassTag base | 2498.772 → 2498.735 | identical | 303 / 29 929 | 0 |
| CompassTag lid | 816.452 → 816.461 | identical | 430 / 18 857 | 2, investigated below |

Every difference is a per-column thickness difference at or below the engraving
depth, where the glyph outlines differ — expected, since OpenSCAD defaults to
Liberation Sans and `font_file` here points at Arial. Point it at a Liberation
Sans TTF for parity.

The two CompassTag lid columns above the engraving depth are at
(1.824, 7.025) and (1.074, 7.025), both differing by exactly 1.0 mm
= `lid_end_height − lid_body_height`. They sit 1.3 and 1.6 µm inside the post
cylinder wall, near its tangent point at y = 7, where `$fn=120`'s inscribed
polygon runs up to 1.0 µm inside the true circle. So they are a faceting
artifact in a ~1.5 µm band, worth 0.045 mm³, or 0.005% of the lid — not a
geometry error. Checked by exact `isInside` / `distToShape` queries against the
BRep, not inferred.

## Notes carried over from the BitPresTag conversion

Details of the base/lid feature order, the sketch-constraint scheme, why the
engraving is a `Part::Cut` rather than a Pocket, and the three
faithful-but-odd behaviors inherited from the `.scad` sources are in
`BitPresTag/BitPresTag-param-NOTES.md`. Two are worth repeating here:

- The base `*` marker only cuts when `base_height` reaches it. With
  `base_extra_height` = 1 (BitPresTag) it floats clear and removes nothing,
  exactly as in the `.scad`; with 2 (CompassTag) it engraves the top face. Not
  a bug in the conversion, but probably not what BitPresTag intended.
- The lid version string overhangs the lid body in Y on both boards — at
  `text_size` 2 the string is ~12.8 mm long and the body is 9–10 mm wide.

`BitPresTag/bitprestag_param.py` is the earlier single-board generator and is
now superseded by this one; it produces an identical `BitPresTag-param.FCStd`
and can be deleted.

Headless runs write no view state, so re-saving from `freecadcmd` leaves the
sketches and engraving cutters visible when the file is next opened in the GUI.
Rebuild from inside the GUI, or call `_show_only(doc, {"Base", "Lid"})`, if
that matters.
