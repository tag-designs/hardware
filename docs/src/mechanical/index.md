# Mechanical Designs

A bare board is not a tag. `Mechanical/` holds the printed and cut parts that
carry the board on the bird and hold it on the bench: cases, base adapters,
and jigs.

| Directory | Holds |
| --- | --- |
| `BitTag/`, `PresTag/`, `IMUTag/`, `CompassTag/`, `BitPresTag/` | Per-tag cases, as printable STLs with the models they came from |
| `Components/` | Shared parts used across designs: pogo pins, dowel pins, screws, the populated base model |
| `Acrylic/` | Laser-cut parts, currently the MultiCharger faceplate |

Most tag directories carry both a printable result and its source — an `.stl`
beside the `.scad` or `.FCStd` that produced it, and a `.dxf` of the board
outline the case was built around.

## The parametric case model

The pogo-pin cases are not independent models. `Mechanical/tagcase_param.py`
builds the base and lid for a board from a JSON variant file, so a new board is
a new variant file rather than a new model:

```shell
freecadcmd tagcase_param.py -- --params CompassTag/CompassTagv1.json --stl
freecadcmd tagcase_param.py -- --params BitPresTag/BitPresTag.json --stl
```

Inside the FreeCAD GUI, `exec(open('.../tagcase_param.py').read())`, then
`build(*load_variant('.../CompassTagv1.json'))`.

A variant file is spreadsheet cells plus, under `_`-prefixed keys, the output
settings, so one file fully describes a board:

```json
{ "_doc_name": "CompassTagv1_param",
  "_out": "CompassTagv1-param.FCStd",
  "_stl_prefix": "CompassTagv1-fc",
  "name": "CTagV1",
  "board_nominal_len": "17.9 mm" }
```

`_out` is resolved relative to the variant file, so each board's document lands
in its own folder. An unknown parameter name is rejected rather than silently
ignored.

Values are cell contents, which is what makes this more than a table of
numbers: `"17.9 mm"` is a quantity, `"=0.002 * 25.4 mm"` a formula. A variant
can therefore override a *relationship* as well as a value.

### Optional features

Boards differ in structure, not only in dimensions, so features that only some
cases need are bound to flag cells rather than decided in the script. Flipping
a cell in the GUI makes a feature appear or disappear without a rebuild.

| Flag | What it adds |
| --- | --- |
| `enable_base_crossbar` | A solid bar joining the two post bosses |
| `enable_post_boss_aux` | A second boss pair |
| `enable_post_web` | A web between the boss pairs |
| `enable_battery_pocket` | The round battery relief |
| `enable_battery_end_pocket` | A rectangular pocket at the battery end |

`TAGCASE-README.md` in the repository records how far parameterization got on
its first real test and which differences turned out to be genuine topology
rather than numbers.

## Tools

- [FreeCAD](https://www.freecad.org/) for the parametric case model
- [OpenSCAD](https://openscad.org/) for the older `.scad` designs
- A 3D printer for cases and adapters; a laser cutter for the acrylic parts
