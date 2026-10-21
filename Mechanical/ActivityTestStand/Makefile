# Activity-detector tilt stand. See DESIGN-NOTES.md.
#   make plates   DXF (in + mm) and SVG for the two acrylic plates
#   make model    FreeCAD assembly, STEP, fit and tilt-range checks (out/checks.txt)
#   make renders  PNGs of the assembly and plates (needs pyvista: ~/cq-env)
#   make all      all three
FREECADCMD ?= /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
RENDER_PY  ?= $(HOME)/cq-env/bin/python

.PHONY: all plates model renders check clean
all: plates model renders

check:
	python3 teststand.py | tail -1

plates: check
	python3 make_plates.py

model: check
	$(FREECADCMD) -c "import runpy; runpy.run_path('build_model.py', run_name='__main__')" > out-build.log 2>&1 || (tail -30 out-build.log; false)
	@mv out-build.log out/build.log
	@cat out/checks.txt

renders: model plates
	$(RENDER_PY) render.py
	for f in plates/*.svg; do qlmanage -t -s 1000 -o renders $$f > /dev/null 2>&1 || true; done

clean:
	rm -rf out *.FCBak
