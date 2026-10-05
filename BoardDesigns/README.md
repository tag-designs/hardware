This directory contains the design files for the various PCBs and mechanical components.

Tools needed to build the boards

*   Kicad v6
*   kibot

Tools needed to build base adapter plastic

*   openscad

Boards are grouped by role; each board is `<Group>/<board>/`:

* Tags/ -- the animal-borne tags themselves (BitTag, PresTag, CompassTag, IMUTag, TorporTag, ...)
* Bases/ -- boards a tag plugs into: tagbase-* production baseboards and the MCU-carrying tag-breakout-* boards
* Prototypes/ -- tag circuits laid out as breakouts, ST eval daughter cards, imutag-daughtercard, UIUCBreakout
* Chargers/ -- MultiCharger and its JLCPCB variant
* Development/ -- bench and test equipment (TagPwrMonitor, js320-faceplate)

Shared infrastructure stays at this level: libraries/, kicad_libraries/,
kicad-helpers/, Kibot-config/, Templates/. Retired boards live in Obsolete/.
Board files reach these through `${KIPRJMOD}/../../`, so moving a board to a
different depth means rebasing its lib tables, 3D-model paths, kibot include
and datasheets symlink.

To build the various PCB files including pdf schematic, png 3d model, and fabrication files

build BitTagv5-pcb

or more generally

build [somedesign]-pcb