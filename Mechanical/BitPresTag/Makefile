OPENSCAD ?= $(HOME)/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
SCAD := BitPresTag.scad
DXF := BitPresTag-Edge_Cuts.dxf
STLS := BitPresTag-base.stl BitPresTag-lid.stl

.PHONY: all base lid clean

all: $(STLS)

base: BitPresTag-base.stl

lid: BitPresTag-lid.stl

BitPresTag-base.stl: $(SCAD) $(DXF)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false $(SCAD)

BitPresTag-lid.stl: $(SCAD) $(DXF)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true $(SCAD)

clean:
	rm -f $(STLS)
