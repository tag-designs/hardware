"""Render the assembly from build_model.py's meshes to renders/*.png.

    ~/cq-env/bin/python render.py

Needs pyvista (the b123d-models environment has it). The rotor is posed by
rotating its meshes about the tilt axis, so one build serves every angle.
"""
import os

import pyvista as pv

import teststand as ts

pv.OFF_SCREEN = True
STL = os.path.join(ts.HERE, "out", "stl")
OUT = os.path.join(ts.HERE, "renders")
ACRYLIC = dict(color="#bfe3f2", opacity=0.55)
COLOURS = {
    "BasePlate": ACRYLIC, "AdapterPlate": ACRYLIC,
    "Feet": dict(color="#222222"), "BottomBracket": dict(color="#3a3a3a"),
    "UBracket": dict(color="#3a3a3a"), "LX16A": dict(color="#141414"),
    "LX16A_horn": dict(color="#555555"), "BusLinker": dict(color="#2a5d9f"),
    "BusLinkerSpacers": dict(color="#f0f0e0"), "TagSpacersA": dict(color="#f0f0e0"),
    "BaseInserts": dict(color="#c9a227"), "BracketScrews": dict(color="#9a9a9a"), "AdapterInserts": dict(color="#c9a227"),
    "TagbaseA": dict(color="#2e7d32"),
}
ROTOR = {"UBracket", "AdapterPlate", "AdapterInserts", "TagSpacersA", "TagbaseA"}


def scene(deg, cam, name, size=(1300, 950)):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("white")
    for part, style in COLOURS.items():
        m = pv.read(os.path.join(STL, part + ".stl"))
        if part in ROTOR and deg:
            m = m.rotate_vector((1, 0, 0), deg, point=(0, 0, ts.AXIS_Z))
        p.add_mesh(m, specular=0.2, smooth_shading=False, **style)
    p.camera_position = cam
    p.reset_camera()
    p.camera.zoom(1.25)
    p.screenshot(os.path.join(OUT, name))


def main():
    os.makedirs(OUT, exist_ok=True)
    c = (0, 0, 45)
    iso = [(260, -300, 230), c, (0, 0, 1)]
    end = [(400, 0, 45), c, (0, 0, 1)]          # looking down the tilt axis from +x
    scene(0, iso, "iso-0deg.png")
    scene(-60, iso, "iso-tilt60.png")
    for deg in (-90, 0, 90):
        scene(deg, end, "end-%+ddeg.png" % deg if deg else "end-0deg.png", size=(1000, 900))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
