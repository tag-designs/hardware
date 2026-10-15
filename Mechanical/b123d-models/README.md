# b123d-models — tag cases in build123d (experimental)

One library derives a tag case (base, lid, no-battery lid) from the board's
`.kicad_pcb`, instead of a hand-edited `.scad` per board. It covers the rules in
`../TAGCASE-PROCESS.md`. Started 2026-10-15; not yet used for a printed case.
The OpenSCAD cases in `../<Tag>/` remain the reference.

```
make                   # every case: parts, report, fit check -> out/ (~70 s from clean)
make CASES=BitTagNG    # one case
make render            # PNGs of the parts and the fit, from the last build
make clean
python -m tagcase.kicad <board>.kicad_pcb    # what the case reads from a board
```

`out/` is not tracked: everything in it is regenerated from the board files.
`make` exits non-zero if any fit requirement fails. **When a case is printed,
copy its STLs into that tag's case folder and commit them there.** A rebuild
reproduces the design, but not necessarily the exact files: a different
build123d, OCCT or KiCad version, or a changed footprint model, can move the
geometry slightly.

Environment: `requirements.txt` pins the Python packages (`uv pip install -r
requirements.txt` into `~/cq-env`). Outside pip it needs:
- **KiCad 10.0.2 `kicad-cli`**, for the board's 3D export. Part heights come
  from it, so without KiCad the lids cannot be built, not just checked.
- **OpenSCAD 2021.01**, only for its bundled Liberation Sans Bold.

## Layout

| | |
|---|---|
| `tagcase/kicad.py` | s-expression reader (KiCad 6–9). The Edge.Cuts outline as a face (lines, arcs, circles, rects, polys; degenerate edges reported, not used), footprints with courtyards in case coordinates, J201/J401/J30x. Also the kicad-cli STEP export (cached in `out/cache/`), which supplies part heights to the case and the real parts to the fit check. |
| `tagcase/parts.py` | Common parts: `MIN_BOARD_THICKNESS` 0.4; the cell library (MS621F, MS920SE, positioned from J401; centre and rim radius read from the models); `BATTERY_FAMILIES`; `Pins.NARROW` / `WIDE`; tag bases `SINGLE_PAIR` / `LIPO`. |
| `tagcase/case.py` | `CaseDesign` (house rules, all overridable) and `TagCase` (features derived from the board). `report()` prints every derived number and flags anything that needs a decision. |
| `tagcase/fit.py` | Fit check against the real parts: kicad-cli STEP of the board, cells at nominal and ± skew, tag-base PCB, 855 connector, dowels. Lids are seated on the real geometry. |
| `cases/build.py` | One line per case. |

## Rules (designer, 2026-10-15)

- **Board groove**: the outline offset by 0.0015″ (0.038 mm) per edge, as in the
  OpenSCAD cases. It follows the real outline, so on BitTag/PresTag the tab and
  shoulders locate the board.
- **Board thickness**: every clearance uses the 0.4 mm minimum, whatever the
  file says.
- **Cells**: a board that can carry an MS920 is assumed to, for experiment
  lifetime. Every MS621 footprint is cased for both, and the lid seats on the
  taller.
- **Cell clearance**: the models' true rim radii (MS621F 3.40, MS920SE 4.75),
  plus explicit allowances: 0.4 clearance, 0.3 shift and ±5° skew about the
  pads, because cells are hand-soldered. The fit check tests each skew limit.
- **Pogo-end lid block**: pressing on the cell solder joints is acceptable;
  pressing above the pogo pins is the point. On BitTagNG, J201 sits behind
  J401, so the block lands on the cell feet (z 0.55).
- **Far lid block may bear on a component** when it must. With
  `far_block_bearing="auto"` (the default) it bears on the board if that
  leaves two feet at least 0.5 wide. Otherwise it is one full-width block
  sitting `far_block_gap` above the tallest part under it, with heights taken
  from the board's KiCad models. Both lids follow the rule, and the report
  names the part. Set `"board"` or `"parts"` to force either.
- **`*` markers**: they only show which way round the lid goes, so the base
  marker can go anywhere that does that. It must sit clearly on the pogo side
  of the screw axis, because the lid is symmetric under a 180° turn about it.
  It goes on the base top if there is room there, otherwise on the pogo-end
  face (both current boards).

## Status

| | UIUCTag | BitTagNG |
|---|---|---|
| fit check | ALL CLEAR | ALL CLEAR |
| far lid block | on the board, 0.135 / 0.285 gap | on C6 (0.80 tall), 0.20 gap |

UIUCTag reproduces the `.scad` derivations (base 27.076 × 17.076, posts x 1.9,
far block −9.25…−7.825, lid z 5.2) and the README's FreeCAD clearances. It
differs deliberately in three ways: the real harness-hole positions (the
`.scad` rounded them to ±3.75), the skew-aware cell relief, and the
end-face marker.

## Traps found

- An outline face can come out facing −z after the y flip, and `extrude()`
  then runs downward. On BitTagNG the groove was cut below the base top and the
  base overlapped the board by 11 mm³. Fixed in `kicad.py`, which asserts +z.
- kicad-cli silently drops parts that only have `.wrl` models, and exits 2.
  `--subst-models` fixes it; `fit.py` fails if any are still dropped.
- `a & Compound` is wrong when the compound's own solids overlap (the 855
  connector gave a phantom 4.5 mm³), so intersect solid by solid.
- The minimum distance between base and cell is the vertical gap over the stop
  shelf; radial clearance needs its own measurement.
- build123d 0.13 `offset()` fails on a face with holes (it calls a missing
  `Face.unwrap`); `case._erode()` works around it.
