# b123d-models — tag cases in build123d (experimental)

One library derives a tag case (base, lid, no-battery lid) from the board's
`.kicad_pcb`, instead of a hand-edited `.scad` per board. It covers the rules in
`../TAGCASE-PROCESS.md`, and checks every case against the real parts before
calling it done. Started 2026-10-15; not yet used for a printed case. The
OpenSCAD cases in `../<Tag>/` remain the reference.

## How to use it

### 1. Set up (once)

- **Python.** A virtual environment with the pinned packages. The commands
  below assume it is `~/cq-env`:

  ```bash
  uv venv ~/cq-env && source ~/cq-env/bin/activate
  uv pip install -r requirements.txt
  ```

- **KiCad 10** (`kicad-cli`). The case reads part heights from the board's 3D
  export, so without KiCad the lids cannot be built at all, not just checked.
  On macOS it is found inside `KiCad.app` automatically.
- **OpenSCAD 2021.01**, at `~/Software/OpenSCAD-2021.01.app`, but only for its
  bundled Liberation Sans Bold, the engraving font.

### 2. Build the cases

From this folder, with make:

```bash
make                     # every case: parts, report, fit check -> out/  (~70 s)
make CASES=BitTagNG      # one case
make render              # PNGs of each part and of the fit, from the last build
make clean
```

Or with CMake, from the repository root. Only cases whose board or library
changed are rebuilt:

```bash
cmake -S Mechanical/b123d-models -B build-tagcases
cmake --build build-tagcases --target tagcases           # every case
cmake --build build-tagcases --target tagcase-BitTagNG   # one case
cmake --build build-tagcases --target tagcase-renders
```

CMake writes to `build-tagcases/out/`; make writes to `out/` here. The top-level
configure (`cmake -S . -B build`) includes this folder too. Configure options:
`-DTAGCASE_PYTHON=/path/to/python` if the environment is not `~/cq-env`, and
`-DTAGCASES=OFF` to skip these cases in a checkout without it.

Either way, the build fails if any fit requirement fails. Under CMake a failed
case stays out of date, so the next build tries it again.

### 3. Read the result

For each case the build prints two blocks:

- **The report**: every number derived from the board (base size, slot and
  pocket positions, cell relief, lid heights, far block, marker position).
  **A line ending in `**` is a decision for you**, not an error. Example:
  `FEWER THAN TWO USABLE FEET`.
- **The fit table**: one requirement per line, with the measured value, `ok` or
  `FAIL`. Examples: base to board 0.038, each cell at nominal and ±5° skew,
  each lid on each cell, the no-battery lid, pogo pins on their pads, the
  dowels, the end stop. It ends `ALL CLEAR` or `FAILED: n`.

A `CaseError` before either block means the rules cannot handle the board
without a decision. The message says why. Examples: no harness holes at one
end, J201 not at 90°, pins the base does not have.

`out/` then holds, per case: `<Case>-base`, `-lid` and `-lid-nobattery` as STL
and STEP, and `<Case>-assembly.step`. The assembly has the board, both cells,
the tag-base PCB, the pogo connector, the dowels and the case, so you can look
at the fit in FreeCAD or `ocp_vscode`. `make render` adds PNGs; look at them,
because the checks do not see everything (see step 4).

### 4. Add a case

Add one line to `CASES` in `cases/build.py`: the board, then the label engraved
on the parts.

```python
CASES = {
    ...
    "PresTag": (TAGS / "PresTag-v6/PresTag-v6.kicad_pcb", dict(label="PT6")),
}
```

Then `make CASES=PresTag` and `make render CASES=PresTag` (CMake picks the new
case up on its own). Everything else comes from the board. Add these to the
`dict` only when the default is wrong for this tag:

| argument | default | when to change it |
|---|---|---|
| `tag_base=` | `SINGLE_PAIR` | `LIPO` for the double-screw tag base |
| `pins=` | `Pins.NARROW` | `Pins.WIDE` for a board too wide for the narrow pins (needs `LIPO`) |
| `cells=` | from J401's footprint (MS621 → MS621F and MS920SE) | a tag that should be cased for other cells |
| `design=` | `CaseDesign()` | a one-off rule change, e.g. `replace(CaseDesign(), far_block_bearing="board")` |

What the board must have, because the reader finds parts by name: `J201` for
the pogo pads (at 90°, on the +x end), `J401` for the battery pads, and
`taghole` footprints for the harness holes at both ends.

Check these by eye in the renders, because nothing tests them yet:
- **The label fits the lid.** About six bold characters fit between the screw
  bosses.
- **A new cell lands on its pads**, if you added one (below).

A **new battery footprint** needs a `CoinCell` in `tagcase/parts.py`: the STEP
path, the remap from the vendor model's axes into J401's footprint frame, and
the tab half-width. Map the footprint name in `BATTERY_FAMILIES`. The cell's
centre and radius are read from the model. **LiPo tags** (IMUTag-style) are not
supported yet.

### 5. Print a case

Build it, read the report and fit table, and look at the renders. Then **copy
its three STLs into that tag's case folder (`../<Tag>/`) and commit them
there**. `out/` is not tracked, and a rebuild reproduces the design but not
necessarily the exact files: a different build123d, OCCT or KiCad version, or a
changed footprint model, can move the geometry slightly. Note the commit of
this folder the parts came from.

### 6. Change a house rule

The house rules are the defaults of `CaseDesign` in `tagcase/case.py`:
clearances, skew allowance, block drops, text sizes and the far-block bearing
rule. A change there changes every case, so rebuild all of them (`make`) and
read every report. Record the decision under **Rules** below.

To see what the library reads from a board without building anything:

```bash
~/cq-env/bin/python -m tagcase.kicad ../../BoardDesigns/Tags/<Tag>/<Tag>.kicad_pcb
```

## Layout

| | |
|---|---|
| `tagcase/kicad.py` | s-expression reader (KiCad 6–10). The Edge.Cuts outline as a face (lines, arcs, circles, rects, polys; degenerate edges reported, not used), footprints with courtyards in case coordinates, J201/J401/J30x. Also the kicad-cli STEP export (cached in `out/cache/`), which supplies part heights to the case and the real parts to the fit check. |
| `tagcase/parts.py` | Common parts: `MIN_BOARD_THICKNESS` 0.4; the cell library (MS621F, MS920SE, positioned from J401; centre and rim radius read from the models); `BATTERY_FAMILIES`; `Pins.NARROW` / `WIDE`; tag bases `SINGLE_PAIR` / `LIPO`. |
| `tagcase/case.py` | `CaseDesign` (house rules, all overridable) and `TagCase` (features derived from the board). `report()` prints every derived number and flags anything that needs a decision. |
| `tagcase/fit.py` | Fit check against the real parts: kicad-cli STEP of the board, cells at nominal and ± skew, tag-base PCB, 855 connector, dowels. Lids are seated on the real geometry. |
| `cases/build.py` | The case list, one line per case; `--list` and `--out` for CMake. |
| `Makefile`, `CMakeLists.txt`, `render.py` | Build, CMake targets, renders. |

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
