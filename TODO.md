---
type: worklist
status: current
summary: Open work on the hardware documentation and board designs: design reviews that name the wrong board, boards with no review, retired KiBot files, and a directory-name collision.
---

# Hardware Worklist

Delete an item when it is done.

## Design reviews

- **The u375 breakout review is the wrong board's.**
  `BoardDesigns/Bases/tag-breakout-u375-smps-v1/` carries
  `tag-breakout-l432-u375-lipo-v1-design-review.md`, copied from a sibling. It
  is not just misnamed: it analyses `SiP32432` (three mentions) and
  `TPS7A0218`, which is the LDO design. `-v1` actually carries a `TPS62840YBGR`
  and a 2.2 µH inductor, which is what the `-smps` in its name refers to. The
  page `docs/src/bases/tag-breakout-u375-smps-v1.md` was corrected to match the
  board; the review has not been. Rerunning it is the fix, not renaming the
  file.
- **The LiPo tag base review calls the board `tagbase-jlcpcb-v7`.** Four times
  in `BoardDesigns/Bases/tagbase-lipo-v1/tagbase-lipo-v1-design-review.md`, and
  again in `.kicad-happy.json` and `tagbase-lipo-v1.xml` beside it. Prose only
  — the file names and the analysis are right.
- **Seven documented boards have no design review.** `BitTagv7`, `PresTag-v6`,
  `CompassTag`, `tagbase-jlcpcb-v3`, `tag-breakout-l432v2`,
  `IMUTagNandBMP581-breakout` and `steval-daughter-v2`. Each page says so
  rather than linking one, so nothing is broken; it is a gap, not a fault.
  `BitTagv7` and `CompassTag` are the ones most worth having, being the tags
  most built.

## Board designs

- **The tag base figures are still the wrong board's.** The identification is
  settled — `Bases/tagbase-v7` is the fabricated design (`R6` 100 Ω,
  `production/gerber.zip`), the 82 Ω revision is retired to
  `Obsolete/tagbase-jlcpcb-v7`, and the pages now describe the right board. But
  `docs/src/images/boards/tagbase-v7-top.png` and
  `docs/src/schematics/tagbase-v7.pdf` were generated from the 82 Ω copy and
  renamed, not regenerated: the render's silkscreen legend reads 82 where the
  board reads 100. They are deliberately left unstamped so the `Check board
  figures` job reports them. One `board-docs` build fixes both. **Do not push
  before that build.**
- **Fifty-six `.kibot.yaml` files are still in the tree.** KiBot no longer
  drives anything from CMake. They were left to run by hand if wanted; if that
  is not wanted, they are dead weight, and several are named for the board they
  were copied from rather than the one they sit beside.
- **Copied-directory artefacts more generally.** `CMakeLists.txt`, `kibot.yaml`
  and review files named for a sibling turned up repeatedly while the thirteen
  documented boards were being normalized. Only the documented boards were
  swept; the rest of `BoardDesigns/` has not been.

## Documentation

- **The umbrella's hardware link is still the placeholder.** `mkdocs.yml` in
  `tag-designs.github.io` points at `https://tag-designs.github.io/hardware/`
  under a single "Hardware Documentation" entry, agreed when the hardware site
  did not yet exist. It now has Tag Designs, Base Boards and Prototype Boards
  sections worth pointing at directly.
- **Tag assembly and `building/hardware/` have not moved** from the umbrella
  into the hardware site, which the umbrella strategy has as step 5.
- **The Licenses page has no citation.** `docs/license/index.md` carries a
  "Citation pending" admonition asking readers to get in touch. It needs the
  real preferred citation.

## Generated figures

- **Regenerating figures needs KiCad and Pillow locally.** `cmake --build
  build-boards --target board-docs` redraws the renders and re-exports the
  schematic PDFs; both are committed, because the workflow that publishes the
  site has no KiCad. The `Check board figures` job reports when a figure has
  fallen behind its design but cannot fix it. Running this in CI, in a
  `kicad/kicad` container, would remove the committed binaries and the manual
  step — it was deferred, not rejected.
