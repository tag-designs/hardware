OPENSCAD ?= $(HOME)/Software/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
SCAD := IMUTag.scad
DXF := IMUTag-Edge_Cuts.dxf
STLS := IMUTag-base.stl IMUTag-lid.stl

.PHONY: all base lid clean

all: $(STLS)

base: IMUTag-base.stl

lid: IMUTag-lid.stl

IMUTag-base.stl: $(SCAD) $(DXF)
	$(OPENSCAD) -o $@ -D makebase=true -D makelid=false -D makelidshort=false $(SCAD)

IMUTag-lid.stl: $(SCAD) $(DXF)
	$(OPENSCAD) -o $@ -D makebase=false -D makelid=true -D makelidshort=false $(SCAD)

clean:
	rm -f $(STLS)
