OPENSCAD ?= $(HOME)/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
SCAD := BitTag.scad
# Two bases from one source: 1.0 mm pogo compression for BitTagv7, BitTagNG/v8
# and PresTag (v3); 0.8 mm for PresTag-v6, whose C4 hangs over the pogo
# insulator. Two lids, each fits both bases.
STLS := BitTag-base.stl BitTag-base-prestagv6.stl BitTag-lid.stl BitTag-lid-nobattery.stl

.PHONY: all check assembly clean

all: $(STLS)

BitTag-base.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false -D pogo_compression=1.0 $(SCAD)

BitTag-base-prestagv6.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false -D pogo_compression=0.8 $(SCAD)

# Exported at lid_preview_z=0, so the lid's underside is at z=0.
BitTag-lid.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D lid_preview_z=0 $(SCAD)

BitTag-lid-nobattery.stl: $(SCAD)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D lid_no_battery=true -D lid_preview_z=0 $(SCAD)

# Each base against the boards it serves, both lids, the pogo insulator,
# inserts standing 1.0 proud and the dowel tops. Passes when OpenSCAD reports
# an empty top-level object; also fails on any OpenSCAD WARNING (an undefined
# variable can silently drop a part and still "pass").
check: $(SCAD)
	@for c in 1.0 0.8; do \
		rm -f check.stl check-$$c.log; \
		$(OPENSCAD) -o check.stl -D makechecks=true -D pogo_compression=$$c $(SCAD) > check-$$c.log 2>&1; \
		if grep -q WARNING check-$$c.log; then grep WARNING check-$$c.log; echo "check $$c: OPENSCAD WARNINGS"; exit 1; fi; \
		grep -q 'top level object is empty' check-$$c.log \
			&& echo "check (compression $$c): no interference" \
			|| { echo "check (compression $$c): INTERFERENCE (see check.stl)"; exit 1; }; \
	done

# The tags as fabricated, from KiCad, each with its origin at J201 so the STEP
# lands in case coordinates. --subst-models swaps VRML references (BitTagv7's
# MS621F) for the STEP of the same name. PresTag v3 names eight stock models
# (U302 and seven 0201/0402 passives) through ${KISYS3DMOD}, which kicad-cli
# does not resolve from --define-var or the environment; they are missing
# from its STEP, and covered by the box model in `make check` (README.md).
KICAD_CLI ?= /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
FREECADCMD ?= /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
TAGS := ../../BoardDesigns/Tags
STEP_EXPORT = $(KICAD_CLI) pcb export step --subst-models --include-pads -f

tag-BitTagv7.step: $(TAGS)/BitTagv7/BitTagv7.kicad_pcb
	$(STEP_EXPORT) --user-origin=151.03x108.441mm -o $@ $<
tag-BitTagNG.step: $(TAGS)/BitTagNG/BitTagNG.kicad_pcb
	$(STEP_EXPORT) --user-origin=150.415x108.441mm -o $@ $<
tag-PresTag.step: $(TAGS)/PresTag/PresTag-v3.kicad_pcb
	$(STEP_EXPORT) --user-origin=150.431876x108.400589mm -o $@ $<
tag-PresTag-v6.step: $(TAGS)/PresTag-v6/PresTag-v6.kicad_pcb
	$(STEP_EXPORT) --user-origin=150.431876x108.400589mm -o $@ $<
# PresTag v5, the fabricated PresTag, lives in the ultralight-tags repository.
PRESTAG_V5 ?= $(HOME)/Research/ultralight-tags/hardware/PresTagv5/PresTag-v5.kicad_pcb
tag-PresTag-v5.step: $(PRESTAG_V5)
	$(STEP_EXPORT) --user-origin=150.431876x108.400589mm -o $@ $<

TAG_STEPS := tag-BitTagv7.step tag-BitTagNG.step tag-PresTag.step tag-PresTag-v5.step tag-PresTag-v6.step

# Bases, lids, every tag with both cells, the base PCB, pogo connector and
# dowel pins in BitTag-assembly.FCStd, with an interference report.
assembly: $(STLS) $(TAG_STEPS) assemble.py
	$(FREECADCMD) assemble.py

clean:
	rm -f $(STLS) check.stl check-*.log
