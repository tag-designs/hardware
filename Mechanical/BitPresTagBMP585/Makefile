OPENSCAD ?= $(HOME)/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
SCAD := BitPresTagBMP585.scad
STLS := BitPresTagBMP585-base.stl BitPresTagBMP585-lid.stl

.PHONY: all base lid check assembly clean

all: $(STLS)

base: BitPresTagBMP585-base.stl

lid: BitPresTagBMP585-lid.stl

BitPresTagBMP585-base.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false $(SCAD)

# Exported at lid_preview_z=0, so the lid's underside is at z=0.
BitPresTagBMP585-lid.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D lid_preview_z=0 $(SCAD)

# Base/tag, lid/board and lid/base interference. Passes when OpenSCAD reports
# an empty top-level object and writes nothing.
check: $(SCAD)
	@rm -f check.stl
	$(OPENSCAD) -o check.stl -D makechecks=true $(SCAD) 2>&1 | grep -q 'top level object is empty' \
		&& echo "check: no interference" \
		|| { echo "check: INTERFERENCE (see check.stl)"; exit 1; }

# The tag as fabricated, centred on the board, from KiCad.
KICAD_CLI ?= /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FREECADCMD ?= /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
BOARD := ../../BoardDesigns/Tags/BitPresTagBMP585/BitPresTagBMP585.kicad_pcb

tag-board.step: $(BOARD)
	$(KICAD_CLI) pcb export step --include-pads --user-origin=149x108mm -f -o $@ $(BOARD)

# Base, lid, tag, both cells, base PCB, pogo connector and dowel pins in
# BitPresTagBMP585-assembly.FCStd, with an interference report.
assembly: $(STLS) tag-board.step assemble.py
	$(FREECADCMD) assemble.py

clean:
	rm -f $(STLS) check.stl
