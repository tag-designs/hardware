OPENSCAD ?= $(HOME)/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
SCAD := UIUCTag.scad
STLS := UIUCTag-base.stl UIUCTag-lid.stl UIUCTag-lid-nobattery.stl

.PHONY: all base lid lid-nobattery check assembly clean

all: $(STLS)

base: UIUCTag-base.stl

lid: UIUCTag-lid.stl

lid-nobattery: UIUCTag-lid-nobattery.stl

UIUCTag-base.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false $(SCAD)

# Exported at lid_preview_z=0, so the lid's underside is at z=0.
UIUCTag-lid.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D lid_preview_z=0 $(SCAD)

# For testing a board before its coin cell is fitted; same screws.
UIUCTag-lid-nobattery.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D lid_no_battery=true -D lid_preview_z=0 $(SCAD)

# Base/tag, lid/board and lid/base interference. Passes when OpenSCAD reports
# an empty top-level object and writes nothing.
# Also fails on any OpenSCAD WARNING: an undefined variable once dropped the
# no-battery lid's far block entirely and the interference check still passed.
check: $(SCAD)
	@rm -f check.stl check.log
	@$(OPENSCAD) -o check.stl -D makechecks=true $(SCAD) > check.log 2>&1; \
	if grep -q WARNING check.log; then grep WARNING check.log; echo "check: OPENSCAD WARNINGS"; exit 1; fi; \
	grep -q 'top level object is empty' check.log \
		&& echo "check: no interference" \
		|| { echo "check: INTERFERENCE (see check.stl)"; exit 1; }

# The tag as fabricated, centred on the board, from KiCad.
KICAD_CLI ?= /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FREECADCMD ?= /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
BOARD := ../../BoardDesigns/Tags/UIUCTag/UIUCTag.kicad_pcb

tag-board.step: $(BOARD)
	$(KICAD_CLI) pcb export step --include-pads --user-origin=148.5x108mm -f -o $@ $(BOARD)

# Base, lid, tag, both cells, base PCB, pogo connector and dowel pins in
# UIUCTag-assembly.FCStd, with an interference report.
assembly: $(STLS) tag-board.step assemble.py
	$(FREECADCMD) assemble.py

clean:
	rm -f $(STLS) check.stl check.log
