---
type: worklist
status: current
summary: Where the six tag boards' 3D model references point, and which of them resolve only on one machine.
---

# 3D Model Reference Audit

Taken 2026-10-08, ahead of adding board renders to the documentation. Every
`(model ...)` reference in the six documented tag boards, classified by how its
path is resolved.

This matters more for renders than for fabrication. **A model that cannot be
found does not raise an error — the part is simply not drawn.** A render can
look entirely plausible while missing the processor.

## Where the references point

| Board | Total | `KIPRJMOD` | `KISYS3DMOD` | `KICAD6` | `KICAD8` | `TAG_LIBRARIES` | absolute | bare |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `BitTagv7` | 15 | 3 | 12 | — | — | — | — | — |
| `BitTagNG` | 22 | 17 | — | 4 | — | — | — | 1 |
| `PresTag-v6` | 25 | 4 | 8 | 11 | 1 | — | — | 1 |
| `CompassTag` | 24 | 14 | — | 1 | 6 | 3 | — | — |
| `imutag-smps` | 28 | 5 | — | — | — | 3 | 1 | — |
| `BitPresTagBMP585` | 24 | 7 | 1 | 1 | — | — | — | — |

Only `${KIPRJMOD}` references can be checked from the repository alone. **All 50
of them resolve** — no in-repo model is missing. Everything else depends on the
machine.

| Board | References that cannot resolve from the repository alone |
| --- | --- |
| `PresTag-v6` | 21 of 25 (84%) |
| `imutag-smps` | 23 of 28 (82%) |
| `BitTagv7` | 12 of 15 (80%) |
| `BitPresTagBMP585` | 17 of 24 (71%) |
| `CompassTag` | 10 of 24 (42%) |
| `BitTagNG` | 5 of 22 (23%) |

## The five problems, in order of how quietly they fail

**1. `KISYS3DMOD` — 21 references.** This is the KiCad 5 path variable. It was
removed in KiCad 6, so on any current KiCad these resolve to nothing. BitTagv7
is the worst affected: 12 of its 15 models go through it, so a render of that
board would be very nearly a bare PCB.

**2. `TAG_LIBRARIES` — 6 references**, in CompassTag and imutag-smps. This
variable is **not defined anywhere in this repository** — it appears only inside
the PCB files themselves and in some obsolete analysis JSON. It must be a path
entry in a local KiCad "Configure Paths" setting, which means those six models
resolve on one machine and nowhere else.

**3. Version-specific stock paths — 24 references.** Boards mix
`${KICAD6_3DMODEL_DIR}` and `${KICAD8_3DMODEL_DIR}`, sometimes within one board:
PresTag-v6 has 11 of the first and 1 of the second. Whichever variable the
installed KiCad does not define silently drops those parts.

**4. An absolute path — 1 reference.** `imutag-smps` points at
`/Users/geobrown/Research/tag-designs/hardware/BoardDesigns/libraries/packages3D/LGA14-L_2P59X3P1X0P5_STM.step`.
Correct on exactly one computer.

**5. Two bare references.** `BitTagNG` has `:PROJ3d:C_0402_1005Metric.step`, a
KiCad alias form, and `PresTag-v6` has a plain `Diodes_DFN1006-3.step` with no
prefix at all.

## What would make renders trustworthy

Nothing here needs fixing to fabricate a board — gerbers do not use 3D models.
It needs fixing to trust a picture.

The in-repo convention already exists and already works: `${KIPRJMOD}/packages3D/`
and `${KIPRJMOD}/../../kicad_libraries/3d_models/`, 50 references, all resolving.
Four of the six boards have a populated `packages3D/` directory. Moving the
remaining references onto that convention would make renders reproducible for
anyone who clones the repository, and would make a missing model a visible
absence in version control rather than a machine-dependent surprise.

That edits the `.kicad_pcb` files, so it is recorded here rather than done.
