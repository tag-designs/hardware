"""Render the built parts to out/<case>-<view>.png.

    ~/cq-env/bin/python render.py [UIUCTag BitTagNG ...]   # default: every case

Run `python -m cases.build` first; this reads its STL and assembly output.
"""
import sys

import pyvista as pv
from build123d import export_stl, import_step

from cases.build import CASES, OUT

pv.OFF_SCREEN = True
BASE, LID = "#d9b36c", "#9cc3d9"
VIEWS = [
    ("base-top", "base", BASE, (40, -60, 70), (0, 0, 1)),
    ("base-plan", "base", BASE, (0, 0, 90), (0, 1, 0)),
    ("base-pogo-end", "base", BASE, (80, -25, 20), (0, 0, 1)),
    ("lid-under", "lid", LID, (40, -50, -50), (0, 0, 1)),
    ("lid-nb-top", "lid-nobattery", LID, (0, 0, 80), (0, 1, 0)),
]
# The fit render: base with the real board, cells and tag base in place.
FIT_COLOURS = {"Tag": "#2e7d32", "Cells": "#9e9e9e", "Base": BASE, "TagBase": "#555555"}


def render(name):
    for view, part, colour, cam, up in VIEWS:
        p = pv.Plotter(off_screen=True, window_size=(1100, 800))
        p.add_mesh(pv.read(OUT / ("%s-%s.stl" % (name, part))), color=colour, specular=0.3)
        p.camera_position = [cam, (0, 0, 0), up]
        p.reset_camera()
        p.camera.zoom(1.3)
        p.screenshot(OUT / ("%s-%s.png" % (name, view)))

    p = pv.Plotter(off_screen=True, window_size=(1200, 850))
    tmp = OUT / "cache" / "_render.stl"
    tmp.parent.mkdir(exist_ok=True)
    for child in import_step(OUT / ("%s-assembly.step" % name)).children:
        if child.label in FIT_COLOURS:
            export_stl(child, str(tmp), tolerance=0.01, angular_tolerance=0.2)
            p.add_mesh(pv.read(tmp), color=FIT_COLOURS[child.label], specular=0.3)
    tmp.unlink(missing_ok=True)
    p.camera_position = [(45, -55, 45), (2, 0, 0), (0, 0, 1)]
    p.reset_camera()
    p.camera.zoom(1.5)
    p.screenshot(OUT / ("%s-fit.png" % name))
    print("rendered %s" % name)


if __name__ == "__main__":
    for n in sys.argv[1:] or CASES:
        render(n)
