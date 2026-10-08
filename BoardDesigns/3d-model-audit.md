---
type: worklist
status: current
summary: Where the six tag boards' 3D model references point, which resolve, and why that is a reproducibility question rather than a rendering one.
---

# 3D Model Reference Audit

Taken 2026-10-08 while adding board renders, then **corrected against the
renders themselves**. The first version of this file predicted that unresolved
model paths would leave parts missing from the images. The renders disproved
that. What follows is what the evidence actually supports.

## Where the references point

138 `(model ...)` references across the six documented tag boards:

| Prefix | Count | What it is |
| --- | --- | --- |
| `${KIPRJMOD}` | 50 | In-repository, project-relative. Portable. |
| `${KICAD10_3DMODEL_DIR}` | 27 | KiCad 10 stock library |
| `${KISYS3DMOD}` | 21 | The KiCad 5 variable, removed in KiCad 6 |
| `${KICAD6_3DMODEL_DIR}` | 17 | KiCad 6 stock library |
| `${KICAD8_3DMODEL_DIR}` | 7 | KiCad 8 stock library |
| `${KICAD9_3DMODEL_DIR}` | 7 | KiCad 9 stock library |
| `${TAG_LIBRARIES}` | 6 | Not defined anywhere in this repository |
| bare filename | 2 | No prefix at all |
| absolute path | 1 | `/Users/geobrown/...` |

Per board:

| Board | Total | `KIPRJMOD` | Stock-library variables | Other |
| --- | --- | --- | --- | --- |
| `BitTagv7` | 15 | 3 | 12 (`KISYS3DMOD`) | — |
| `BitTagNG` | 22 | 17 | 4 (`KICAD6`) | 1 bare |
| `PresTag-v6` | 25 | 4 | 19 (`KISYS3DMOD` 8, `KICAD6` 11, `KICAD8` 1) | 1 bare |
| `CompassTag` | 24 | 14 | 7 (`KICAD6` 1, `KICAD8` 6) | 3 `TAG_LIBRARIES` |
| `imutag-smps` | 28 | 5 | 19 (`KICAD10` 12, `KICAD9` 7) | 3 `TAG_LIBRARIES`, 1 absolute |
| `BitPresTagBMP585` | 24 | 7 | 17 (`KICAD10` 15, `KICAD6` 1, `KISYS3DMOD` 1) | — |

**Five different KiCad version variables are in use**, one for each era a board
was drawn in, plus the KiCad 5 variable that three boards still carry.

## What the renders actually showed

All twelve renders came out complete. Spot-checking the parts most at risk:

| Part | Board | Model source | In the render? |
| --- | --- | --- | --- |
| `U302` STM32L432 | BitTagv7 | `${KISYS3DMOD}` | Yes, top |
| `U405` ADXL362 | BitTagv7 | `${KISYS3DMOD}` | Yes, bottom |
| `D401` Schottky | BitTagv7 | `${KISYS3DMOD}` | Yes, bottom |
| `Q501` transistor | BitTagv7 | `${KISYS3DMOD}` | Yes, bottom |

So the legacy and version-specific variables all resolve on the machine the
renders were made on — the path configuration there covers every era these
boards span. The only footprints without geometry are `J301`–`J304` and `J201`:
mounting holes and the pogo-pad programming header, which have no model
assigned and correctly show as bare pads.

**Nothing here is broken.** The earlier claim that BitTagv7 would render as a
near-bare board was wrong, and came from reading one render of a board that
simply carries most of its parts on the underside.

## A third failure class: the wrong model

A reference can resolve perfectly and still be wrong. `PresTag-v6` carries at
least one part whose 3D model is not the part that is fitted — reported
2026-10-08 from the render, which is exactly the kind of thing a render is good
for and a netlist is not.

This is worth separating from the two failures above. A **missing** model draws
nothing, so it is visible as a gap. An **unresolvable** model does the same, on
some machines only. A **wrong** model draws something plausible, so it passes
every automated check and is caught only by someone who knows the board.

## The real exposure

It is reproducibility, not correctness. 88 of 138 references resolve through
variables defined outside this repository — in one KiCad installation's path
configuration, in a `TAG_LIBRARIES` entry that exists nowhere in the tree, and
in one case in a specific home directory. That means:

- **A fresh clone renders differently.** Someone with only KiCad 10 installed
  has no `KISYS3DMOD`, `KICAD6`, `KICAD8` or `KICAD9`, and would lose the parts
  that depend on them — most of BitTagv7 and much of PresTag-v6.
- **CI rendering is not yet viable.** A `kicad/kicad` container defines the
  current version's variable only. Running renders in GitHub Actions would
  produce images missing exactly those parts, and nothing would report an
  error: a missing model is drawn as absence, not as a failure.
- **The absolute path in `imutag-smps` is correct on one computer.**

## What would change that

The in-repo convention already exists and already works: `${KIPRJMOD}/packages3D/`
and `${KIPRJMOD}/../../kicad_libraries/3d_models/`, 50 references, all resolving.
Four of the six boards already have a populated `packages3D/` directory.

Moving the remaining 88 onto that convention would make renders reproducible
from a clone, make CI rendering viable, and turn a missing model into a visible
absence in version control rather than a difference between two machines.

That edits the `.kicad_pcb` files, so it is recorded here rather than done.
