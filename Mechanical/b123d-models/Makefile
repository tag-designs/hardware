SHELL := /bin/bash
# Tag cases from the board files. Everything in out/ is regenerated.
#
#   make                  build every case: parts, report, fit check
#   make CASES=BitTagNG   one case (names are the keys of CASES in cases/build.py)
#   make render           PNGs of the parts and the fit, from the last build
#   make clean            remove out/
#
# `make` exits non-zero if any fit requirement fails.

PYTHON ?= $(HOME)/cq-env/bin/python
CASES ?=

.PHONY: all check render clean

all:
	$(PYTHON) -m cases.build $(CASES) | tee out.log; status=$${PIPESTATUS[0]}; \
		mkdir -p out && mv out.log out/build.log; exit $$status

# The fit check runs on every build; this is the same target under the name
# the OpenSCAD case folders use.
check: all

render:
	$(PYTHON) render.py $(CASES)

clean:
	rm -rf out
