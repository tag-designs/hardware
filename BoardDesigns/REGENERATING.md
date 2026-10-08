---
type: guide
status: current
summary: How to regenerate the board renders and schematic PDFs the documentation uses, what guards them, and what to do when one complains.
---

# Regenerating the board figures

Every documented board contributes two kinds of figure to the hardware
documentation site:

| Figure | Where it lands | Drawn from |
| --- | --- | --- |
| 3D render, top (and bottom, for tags) | `docs/src/images/boards/<board>-<side>.png` | `<board>.kicad_pcb` |
| Schematic PDF | `docs/src/schematics/<board>.pdf` | every `*.kicad_sch` in the board's directory |

Both are generated with `kicad-cli`, which ships inside KiCad, and both are
**committed to the repository**. They have to be: the workflow that publishes
the site installs Python and MkDocs only, and has no KiCad to draw with. That
is also why the guards below exist — a committed figure can fall behind the
design it came from, and nothing about a PNG says which layout drew it.

## Regenerating

You need KiCad (for `kicad-cli`) and Pillow. From the repository root:

```sh
cmake -S BoardDesigns -B build-boards
cmake --build build-boards --target board-docs
```

Check the configure line. It prints what it is about to use:

```
-- kicad-cli: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
-- Board renders: zoom 0.5, frame 2400 square, preset follow_pcb_editor
```

If that line says something you did not expect, believe it rather than this
document: it is the settings actually in force.

Three targets, in case you want less than everything:

| Target | Does |
| --- | --- |
| `board-docs` | renders and schematics, for every board whose sources changed |
| `board-renders` | the 3D renders only |
| `board-schematics` | the schematic PDFs only |
| `<board>-renders`, `<board>-schematic` | one board |

Nothing is part of the default build. A plain `make` should not rewrite files
that are under version control.

A full regeneration takes a few minutes locally and about 17 in a container,
most of it raytracing: roughly 45 seconds per render, with the PDFs nearly
free. Only boards whose sources changed are redrawn, so the usual cost after
editing one board is a render or two.

## The guards, and what they are telling you

Three checks, all pure Python, no KiCad needed. Run them from the repository
root.

### `check_models.py` — can every 3D model be found?

```sh
python3 BoardDesigns/kicad-helpers/check_models.py
```

This is the one that matters most, because **`kicad-cli` says nothing when it
cannot load a model**. It draws it as nothing and reports success, so a board
can lose a quarter of its parts with a clean build and a green tick. That has
happened twice here: once when a path variable went stale during a
reorganization and took six models with it, and once when a board that had
never been normalized was about to be published with 27 broken references.

A reference is only safe if it goes through `${KIPRJMOD}`, which is relative to
the board. The script fails on anything else:

- an **absolute path**, which resolves only on the machine that wrote it
- `${KICAD10_3DMODEL_DIR}`, which needs KiCad installed where the render runs
- a **user-defined variable** such as `${TAG_LIBRARIES}`, which resolves only
  where someone has defined it — and silently points at nothing if the tree is
  later rearranged

`--fix` repairs what it can, rewriting the reference relative to the board:

```sh
python3 BoardDesigns/kicad-helpers/check_models.py --fix
```

**Run this after any KiCad session in which you picked a 3D model through the
file dialog.** KiCad substitutes a path variable only when the chosen file sits
underneath that variable's directory, and will not invent `../..`. The shared
library at `BoardDesigns/kicad_libraries/3d_models` is outside every board's
project directory, so nothing covers it and KiCad writes an absolute path. That
is not a mistake made once; it is what the dialog does.

### `check_renders.py` — are the committed figures still of the committed designs?

```sh
python3 BoardDesigns/kicad-helpers/check_renders.py
```

Each time CMake draws a board it writes a stamp under
`BoardDesigns/.render-stamps/` holding the SHA-256 of what it drew from —
`<board>.sha256` for the layout behind the renders, `<board>.sch.sha256` for
every sheet behind the PDF. This hashes the sources again and compares. It is a
file comparison, not an image comparison, so there is nothing to go flaky.

The `Check board figures` job in `.github/workflows/docs.yml` runs it on every
push. It reports; it does not block the deploy, because only a machine with
KiCad can redraw a figure and an unrelated typo fix should still publish.

`--stale-targets` prints the CMake targets that need rebuilding, one per line,
which is how the container job decides what to generate — a clone does not
preserve file timestamps, so CMake alone would redraw everything.

### `compare_figures.py` — does another machine draw the same pictures?

```sh
python3 BoardDesigns/kicad-helpers/compare_figures.py <directory of generated figures>
```

Byte comparison answers nothing here: the renders are raytraced and two runs on
one machine already differ. This reports three things instead — the trimmed
image dimensions, which track what was actually drawn; a pixel difference over
a coarse grid, which averages the noise away; and the schematic PDFs' text,
word for word, which is where a missing font would show up exactly.

## When something complains

| It says | It means | Do |
| --- | --- | --- |
| `an absolute path, which resolves only on the machine that wrote it` | KiCad wrote a model path through the file dialog | `check_models.py --fix`, then regenerate that board |
| `${TAG_LIBRARIES} is not guaranteed outside a workstation` | a reference through a variable only your machine defines | `check_models.py --fix` |
| `no such file` | a model was moved or renamed | put it back, or point the footprint at the shared library |
| `the layout has changed since its renders were drawn` | you edited a board and did not redraw it | `cmake --build build-boards --target <board>-renders` |
| `the drawing has changed since its PDF was exported` | a schematic sheet changed | `... --target <board>-schematic` |
| `the board runs off the ... of a NNNNxNNNN frame` | a part overhangs further than the camera allows | lower `RENDER_ZOOM`; a bigger frame does not help, the board scales with it |
| `clears a ... frame by only N%` | the margin is nearly gone | lower `RENDER_ZOOM` before it clips |
| `kicad-cli not found` | KiCad is not where CMake looked | `-Dkicad_cli_EXECUTABLE=/path/to/kicad-cli` |
| `Pillow is not installed for ...` | the interpreter CMake found lacks it | install it there, or `-DPython3_EXECUTABLE=...` |

## Framing, and why it is set the way it is

`kicad-cli` fits the board outline to the frame, and `--zoom` scales that fit.
Two consequences, both learned the hard way:

- **A bigger frame alone buys no margin.** The board grows with it. A render at
  2400 square clipped every board exactly as a render at 1200 did.
- **`--zoom` below 1 is what pulls the camera back.** It is set to `0.5`, a
  value measured rather than interpolated, which leaves the board at about half
  the frame — a quarter of it clear on every side. The frame is then only about
  resolution.

After drawing, `fit_render.py` trims the result back to the board with a fixed
proportional margin and turns anything that is not taller than it is wide 90°
clockwise, so every figure is portrait and a top/bottom pair sits side by side
in the documentation grid. That is what rights the bases and the square
prototype carriers.

`BoardDesigns/kicad-helpers/probe_render_framing.py` re-answers the framing
question by measurement if a KiCad release ever changes it.

Settings can be overridden for an experiment without editing anything:

```sh
cmake -S BoardDesigns -B build-boards -DRENDER_ZOOM=0.4
```

`RENDER_ZOOM`, `RENDER_FRAME` and `RENDER_PRESET` are deliberately named
differently from the variables they set, so nothing of ours can be left stale
in a CMake cache. An override sticks for every later reconfigure of that build
directory, so the configure line says when one is in force.

## Why generation is not done in CI

It was tried. `.github/workflows/board-figures.yml` is what remains of the
trial: it runs weekly, regenerates everything in a KiCad container, compares
the result with what is committed, and publishes nothing.

The trial found that the container reproduces the **schematic PDFs exactly** —
all thirteen, word for word — but **not the renders**. Two differences, both
real and both explainable: models on footprints marked `dnp` were not drawn, so
CompassTag's coin cell vanished entirely, and the board stackup's `Black`
solder mask came out green. Those are appearance and visibility defaults, not a
broken repository; every model resolved and every filename matched.

So the figures are still drawn on a workstation, and the container job earns
its keep as a drift detector instead: it is the only thing that would notice a
KiCad release quietly changing how these boards are drawn. The hash stamps
cannot see that — they know whether a figure is older than its design, not
whether redrawing it today would produce the same picture.

**Until the preset difference is settled the weekly job will report
differences**, which is it working correctly. See `TODO.md`.
