# Hardware

This site documents the physical side of the tag project: the circuit boards,
the printed and machined parts they sit in, and the bench work that turns a
fabricated board into a tag ready for a bird.

| Section | Covers |
| --- | --- |
| [Board Designs](boards/index.md) | KiCad designs for tags, bases, chargers and bench equipment, and how fabrication outputs are generated |
| [Mechanical Designs](mechanical/index.md) | Printed cases, adapters and jigs, and the parametric model behind the tag cases |
| [Board Assembly](assembly/index.md) | Preparing a fabricated BitTag board: programming, labelling, battery, conformal coating |

The project overview, the tag families and the field guides are on the
[project home](https://tag-designs.github.io/). The host applications,
firmware and command-line tools are documented in the
[software documentation](https://tag-designs.github.io/software/).

## Getting the designs

Everything here lives in the
[`hardware` repository](https://github.com/tag-designs/hardware). It builds on
its own; you do not need the software repository to work on a board.

Fabrication outputs are generated from the design files rather than committed,
so a board you want to order is a build away rather than a file to find.
