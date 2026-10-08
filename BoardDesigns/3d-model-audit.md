---
type: worklist
status: current
summary: Where the six tag boards' 3D model references point, which resolve, and why that is a reproducibility question rather than a rendering one.
---

# 3D Model Reference Audit

**Resolved 2026-10-08.** All six documented tag boards resolve every 3D model
from this repository: 135 references, every one `${KIPRJMOD}`, none external,
none unresolved. A fresh clone renders what the authoring machine renders.

This file is kept for the reasoning, because two of its conclusions were wrong
in instructive ways and the method that caught them is the part worth keeping.

## What the final state is

| Board | Model references | All in-repo |
| --- | --- | --- |
| BitTagv7 | 14 | yes |
| BitTagNG | 21 | yes |
| PresTag-v6 | 25 | yes |
| CompassTag | 24 | yes |
| imutag-smps | 28 | yes |
| BitPresTagBMP585 | 23 | yes |

Two spellings, both already long-established here:

| For | Spelling |
| --- | --- |
| A model specific to one board | `${KIPRJMOD}/packages3D/<file>` |
| A model shared between boards | `${KIPRJMOD}/../../kicad_libraries/3d_models/<file>` or `${KIPRJMOD}/../../libraries/packages3D/<file>` |

## The three things that made this hard

**1. A missing model is drawn as nothing, not reported as an error.** Neither
the build, nor ERC, nor DRC, nor `kicad-cli` says a word. A board with every
model missing and a board with none missing produce identical output on every
channel except the image.

**2. So the probe written to detect it could not.** `model_resolution.py` ran
over ten boards and reported zero problems, which looked like good news until
`--self-test` pointed one model at a path that cannot exist and `kicad-cli`
stayed equally silent. Comparing rendered images is the only check that works.
That is why the probe keeps its self-test: a tool that cannot fail cannot pass.

**3. Reading path prefixes is inference, not evidence.** The first version of
this audit predicted BitTagv7 would render as a near-bare board because 12 of
its 15 models went through `KISYS3DMOD`. The renders disproved it — that
variable resolved fine, and the board simply carries most of its parts
underneath. The audit had also undercounted, testing for `KICAD6` and `KICAD8`
only, so `KICAD9` and `KICAD10` fell into a bucket printed as zero while the
row totals quietly failed to add up.

## What the method did catch

**The October reorganization had broken `TAG_LIBRARIES`.** Defined as
`${KIPRJMOD}/../libraries`, it reached `BoardDesigns/libraries` when boards sat
one level higher and `BoardDesigns/Tags/libraries` — which does not exist —
afterwards. Six models were resolving to nothing: CompassTag's RTC,
accelerometer and magnetometer, and imutag-smps's RTC, magnetometer and
battery. Nothing anywhere reported it.

**The verification that settled each step** was rendering before, changing,
rendering after, and diffing. After the 68-reference rewrite, ten of twelve
images were unchanged bar noise, and the two that moved were explained by
unrelated deliberate edits — a hidden battery model and a corrected diode
package. No part vanished, which is what would have revealed a basename in the
shared library naming a different model from the one KiCad had been resolving.

## What it bought

Renders are reproducible from a clone rather than from one machine's KiCad
path configuration. That makes rendering in CI viable: a `kicad/kicad`
container would now produce the same images, so the twelve PNGs could stop
being committed and `board-renders` could become a check rather than a
production step. Worth doing as its own piece of work.

Nothing here affects fabrication. Gerbers do not use 3D models. This was
entirely about whether a picture of a board can be trusted and reproduced.
