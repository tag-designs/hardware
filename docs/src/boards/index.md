# Board Designs

All boards are KiCad designs under `BoardDesigns/`, grouped by the role the
board plays. Each board is its own directory, `<Group>/<board>/`.

| Group | Holds |
| --- | --- |
| `Tags/` | The animal-borne tags themselves — BitTag, PresTag, BitPresTag, CompassTag, IMUTag and their revisions |
| `Bases/` | Boards a tag plugs into: the `tagbase-*` production baseboards and the MCU-carrying `tag-breakout-*` boards |
| `Prototypes/` | Tag circuits laid out as breakouts, ST evaluation daughter cards, and the IMUTag daughtercard |
| `Chargers/` | MultiCharger and its JLCPCB variant |
| `Development/` | Bench and test equipment: `TagPwrMonitor`, `js320-faceplate` |

Superseded designs are kept rather than deleted — retired tags in
`Tags/Obsolete/`, older boards elsewhere in `Obsolete/`. A board that was built
and flown is part of the record for the data it produced.

## Tools

- [KiCad](https://www.kicad.org/) v6 for schematic capture and layout
- [KiBot](https://github.com/INTI-CMNB/KiBot) to generate fabrication outputs

## Building a board

Fabrication outputs are not committed. Each board has a CMake target that runs
KiBot over its design files and produces the schematic PDF, a 3D render, and
the gerber and drill files a fabricator needs:

```shell
build BitTagv5-pcb
```

or more generally

```shell
build <design>-pcb
```

Fabricator-specific settings live in `Kibot-config/` — `JLCPCB.kibot.yaml` and
`PCBWay.kibot.yaml` — so a board can be ordered from either house without
editing the board itself.

## Shared infrastructure

Symbol and footprint libraries, 3D models, board templates and the KiBot
configuration are shared across boards and sit at the top of `BoardDesigns/`:
`libraries/`, `kicad_libraries/`, `kicad-helpers/`, `Kibot-config/` and
`Templates/`.

!!! warning "Board files reach shared infrastructure by relative path"

    Each board reaches these through `${KIPRJMOD}/../../`, which assumes a
    board sits exactly two levels down. Moving a board to a different depth
    means rebasing its library tables, 3D-model paths, KiBot include and
    datasheets symlink.

`kicad-helpers/` holds design-rule scripts that check things KiCad's own DRC
does not — decoupling per rail, edge clearance, I2C rise time, SPI pin
mapping, STM32 pin assignment, test point and fiducial placement, and the
battery path.

## Design reviews

Several boards carry a written design review alongside the KiCad files,
recording what was checked and what was found before fabrication. These are
the most useful starting point when picking up an unfamiliar board.
