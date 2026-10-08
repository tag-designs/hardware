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

## Proposed fix

**This is almost entirely a rewrite, not a vendoring exercise.** The models are
already in the repository; the references point outside it.

Across the six boards there are **48 distinct references that are not
`${KIPRJMOD}`**. Of those:

| | Count | Situation |
| --- | --- | --- |
| Already have an in-repo copy reachable from their own board | 38 | Pure path rewrite |
| File is in the repository, but not reachable from that board | 8 | Copy into the shared library, then rewrite |
| File is not in the repository at all | 2 | Fetch once from KiCad's stock library |

### `${TAG_LIBRARIES}` is not an external dependency

It resolves to `BoardDesigns/libraries`, which is in this repository. All four
references through it — `RV-3028-C8.step`, `lipo.step`, `BGA9_BMM350_BOS.step`
and `LGA14-L_2P59X3P1X0P5_STM.step` — are present in
`BoardDesigns/libraries/packages3D/`, which holds 72 models. The single absolute
`/Users/geobrown/...` path points into that same directory.

So from a board directory the portable spelling is already available:

```
${KIPRJMOD}/../../libraries/packages3D/<file>
```

matching the `${KIPRJMOD}/../../kicad_libraries/3d_models/<file>` convention
the boards already use successfully 50 times.

### The two models that are genuinely missing

- `D_SOT-23` — referenced by BitTagv7 via `KISYS3DMOD`
- `SOT-883` — referenced by BitTagNG and BitPresTagBMP585 via `KICAD6_3DMODEL_DIR`

Neither exists anywhere in the tree. They come from KiCad's stock library and
need copying in once.

### Target convention

Two spellings, both already proven in this repository:

| For | Spelling |
| --- | --- |
| A model specific to one board | `${KIPRJMOD}/packages3D/<file>` |
| A model shared between boards | `${KIPRJMOD}/../../kicad_libraries/3d_models/<file>` or `${KIPRJMOD}/../../libraries/packages3D/<file>` |

No version-specific variable, no user path configuration, no absolute paths.

### Suggested order of work

1. **One board at a time**, not a sweeping rewrite. Each board is independent
   and a mistake is then contained.
2. **Render before, rewrite, render after, compare the images.** This is the
   only check that actually works: a reference that fails to resolve draws
   nothing, so a part vanishing between the two renders is the failure signal.
   A diff of the `.kicad_pcb` will not tell you whether a path resolves.
3. **Start with CompassTag**, which needs no new files at all — all six of its
   external references already have a reachable copy. It proves the method
   with the least that can go wrong.
4. **Finish with BitTagv7**, which has the most to change relative to its size
   and needs one of the two missing models.
5. Leave PresTag-v6 until its incorrect model is sorted out, so the two changes
   do not get tangled.

### What it buys

Renders become reproducible from a clone rather than from one machine's KiCad
path configuration, which in turn makes CI rendering viable — at which point
the images no longer need committing and the `board-renders` target becomes a
check rather than a production step. It also makes a missing model a visible
absence in version control instead of a difference between two computers.

### What it does not buy

Nothing about fabrication. Gerbers do not use 3D models. This is entirely about
whether a picture of a board can be trusted and reproduced.
