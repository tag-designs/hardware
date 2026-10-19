# Activity-detector tilt stand

A servo-driven stand that tilts a **tagbase-v7**, with a tag in its case, through
programmed angles. It exercises the ADXL362/ADXL367 activity and inactivity
detectors with known, repeatable changes in the gravity vector. It is built from
off-the-shelf Hiwonder parts plus two laser-cut 1/8" acrylic plates.

```
 tagbase-v7 (+ tag in its case)
 ── 1/16" nylon spacers ──
 adapter plate (acrylic, cross)           ┐
 straight U bracket                       ├ rotor: tilts about a horizontal axis
 LX-16A horn / rear bearing  ─────────────┘
 LX-16A servo (upright) on a shim, held by
 the bottom bracket, cut in half and reversed (two L-angles, tabs outward)
 base plate (acrylic) + BusLinker V3.0 on 1/8" spacers
 rubber feet
```

![assembly](renders/iso-0deg.png)

| | |
|---|---|
| ![tilted 60°](renders/iso-tilt60.png) | ![end view, -90°](renders/end--90deg.png) |

## Evaluation of the plan

**The stack is sound, and the bracket choice gives the right motion.** In the
bottom bracket the LX-16A stands upright with its output shaft horizontal. The
U bracket therefore swings the tagbase through gravity (a tilt), not around a
vertical axis (a yaw). That matters. A yaw move changes the accelerometer
reading only through centripetal and tangential terms, about 0.1 g at best. A
tilt of θ changes one axis by sin θ and another by 1 − cos θ, up to the full
±1 g. The detector thresholds can therefore be mapped directly to angles:

| threshold | tilt from level that crosses it (sin θ) |
|---|---|
| 100 mg | 5.7° |
| 250 mg | 14.5° |
| 500 mg | 30° |
| 1 g | 90° |

The LX-16A resolves 0.24° per count (0–1000 over 240°), with 0.3° rated
accuracy. Near level that is about 4–5 mg per step, fine enough to bracket a
threshold.

Things the plan has to live with, in rough order of importance:

1. **Dynamic acceleration from the lever arm.** The tag sits about 44 mm above
   the axis. At the servo's top speed (0.19 s/60° at 7.4 V, ≈ 5.5 rad/s) the
   centripetal term ω²r is ≈ 0.14 g, and there are start/stop spikes on top of
   that. That makes fast moves a good *activity* stimulus and a poor
   quasi-static one. For threshold calibration, use the move-time parameter: 90°
   over 2 s gives ω²r ≈ 3 mg, and over 1 s ≈ 11 mg.
2. **Servo hold jitter.** A position servo hunting around its set point puts
   mg-level vibration into the tag, which can keep an inactivity timer from
   expiring at low thresholds. After each move, consider unloading the motor
   (LX-16A `SERVO_LOAD_OR_UNLOAD_WRITE`). The gravity torque on the rotor is
   small, about 0.2 kg·cm at 90°, so the gear train should hold position
   unpowered. Confirm that on the real servo.
3. **Cable drag.** The tagbase's USB and JST cables ride on the rotor. Give them
   a slack loop along the tilt axis. Cable whip on a fast move is another
   acceleration source.
4. **Levelling.** No surface on the stand is a reliable reference. Set the
   servo to its centre position (500) before bolting on the U, then trim with
   the servo's angle-offset adjustment until the tag's own accelerometer reads
   0 g on the in-plane axes.
5. **Magnetics.** The servo motor sits about 40 mm from the tag. That is fine
   for accelerometer tests; do not trust magnetometer data (CompassTag) taken
   on this stand.
6. **Servo supply.** The LX-16A is rated **6–8.4 V**. The BusLinker accepts up
   to 14 V and Hiwonder suggests a 12 V adapter, which suits its higher-voltage
   servos. Assume the BusLinker passes its input straight to the servo bus and
   feed it 7.4–7.5 V (≥ 2 A; LX-16A stall current is 1.1–1.9 A).

## Two tagbase orientations

The adapter plate carries the tagbase's four-hole pattern (H1–H4, 42 × 19 mm,
taken from `tagbase-v7.kicad_pcb`) twice, rotated 90°, one per arm of the
cross:

| | board long axis | swings | tilt range (model) |
|---|---|---|---|
| **A** (holes at x ±9.5, y ±21) | along the tilt axis; USB end away from the BusLinker | the 50.8 mm width | **±100.8°** |
| **B** (holes at x ±21, y ±9.5) | across the axis | the 70 mm length, 51 mm on one side of the holes | +106.5° / **−70.8°** |

In both cases the first contact is the tagbase meeting the base plate. A tilts
the tag about the board's long axis and B about its short axis, so between
them both in-plane accelerometer axes see a full ±1 g. B reaches only −70.8° on
its long-overhang side. To go further, raise the servo: a thicker shim, with
the L tabs on matching spacers.

The plate is a cross, not a square, because it only needs to support its four
holes. A full square reaches J1's leads in both orientations.

## Fasteners and inserts

All inserts are **McMaster 94615A111** (E-Z LOK 260-002BR): 2-56, 0.156"
long, flange 0.187" × 0.020". **Laser the holes at 0.118" and drill them to
1/8" afterwards**, as on the multicharger, then **press the inserts from the
top**, flange up. The one exception is the four bracket-tab inserts, which go
in from below (see the table). The 0.011" of body that stands proud underneath
is fine, because the base plate sits on rubber feet. Flange up does three
things:

- the spacers bear on the flanges;
- the board gains 0.5 mm of clearance;
- nothing on the underside of the adapter plate can rock it on the U bracket.
  The B-pattern holes overhang the U's bent edges by about 1 mm.

| joint | hardware | why |
|---|---|---|
| bottom bracket → base plate | Bracket **cut in half across the floor**, and each half turned 180° about the vertical. 4 × 2-56 × 3/16" pan head down through #31 holes in the tabs into inserts at (±24, ±7), **pressed in from below**, flange down. | The bracket is sheet metal too thin to tap, and its Ø2.0 holes are too small to pass a 2-56 screw. They are also under the servo, which sits on the floor, so there is no room for heads or nuts. Reversed, each half is an L-angle: its flange still holds a servo face with the original M2 holes, and its tab points outward, clear of the servo. Flange down, because the screw pulls the insert upward; the tabs then sit on the bodies, 0.28 mm proud. |
| servo → plate | a **shim** under the servo, about sheet thickness + 0.28 mm | The servo used to stand on the floor, one sheet thickness up, and the flange holes are still at that height. Shim until the servo's holes line up with the flange holes. Any flat material will do. |
| U bracket → adapter plate | 4 × 2-56 × 5/16" 82° flat head, countersunk from the top, nut (or nylock) inside the U | J101's pogo tails and the tag case screws sit directly over these four holes, so the plate top there must be flush. That rules out insert flanges. There is about 20 mm of room above the servo for the nuts. |
| tagbase → adapter plate | 4 × 2-56 × 1/4" pan head, 4 × **1/16"** nylon spacers, inserts | 1/4" ends 0.8 mm short of the bottom of the insert, so it cannot reach the U bracket. |
| BusLinker → base plate | 4 × 2-56 × 5/16" pan head, 4 × **1/8"** nylon spacers, inserts | Taller than the tagbase spacers, for the board's untrimmed DC-jack and terminal-block leads. The BusLinker's holes are 3 mm (measured), which passes 2-56 with about 0.4 mm of play per side. |
| feet | 4 inserts at the corners, optional | For screw-on bumpers; ignore them for adhesive feet. |

**Tagbase underside.** The KiCad 3D export of tagbase-v7 puts its lowest feature,
J1's (JST-XH) leads, 1.81 mm below the board. That is more than the 1/16"
spacer. The cross outline keeps J1 off the plate in both orientations. The
board file carries J101's Mill-Max 855 model hidden, so kicad-cli leaves it
out; `build_model.py` adds it from `BoardDesigns/libraries/packages3D/`. Its
tails end 1.02 mm below the board, which leaves a 1.08 mm gap over the plate,
which is flat there (no flanges or screw heads). The fit check against the
export plus the connector reports clear in both orientations. Case-screw heads
and dowels under J101 are not modelled; on the multicharger the same 1/16"
works.

## Parts list

| qty | part | source |
|---|---|---|
| 1 | LX-16A serial bus servo (includes horn, rear bearing and screws) | Hiwonder |
| 1 | LX-16A bracket set; uses the **bottom** and **straight U** brackets | Hiwonder |
| 1 | BusLinker V3.0 debug board | Hiwonder |
| 1 | 7.4–7.5 V, ≥ 2 A supply, 5.5 × 2.1 mm plug | — |
| 1 | tagbase-v7 | this repo |
| 2 | 1/8" acrylic plates (`plates/`) | laser cut |
| 20 | 2-56 press-in inserts, 94615A111 (8 adapter, 4 BusLinker, 4 bracket tabs, 4 feet) | McMaster |
| 4 | 2-56 × 3/16" pan head (bracket tabs) | — |
| 1 | shim, about sheet thickness + 0.28 mm, servo footprint 33 × 24.7 mm | on hand |
| 4 + 4 | 2-56 × 5/16" 82° flat head + hex or nylock nuts | — |
| 4 | 2-56 × 1/4" pan head | — |
| 4 | 2-56 × 5/16" pan head | — |
| 4 + 4 | #2 nylon spacers, 1/16" and 1/8" | on hand |
| 4 | rubber feet | — |

## Assembly

1. Cut the plates. Countersink the four central adapter holes from the top (the
   engraved axis ticks are on the top face). Leave the four bracket-tab pilots
   (at x = ±24) at 0.118" for now.
2. Cut the bottom bracket in half across the floor, midway between the
   flanges, and deburr. Turn each half 180° about the vertical, so its tab
   points away from the servo. Screw the two flanges to the servo's horn and
   back faces with the original M2 screws, standing the servo on its shim so
   the holes line up.
3. Use the base plate as the jig for the tabs. Stand the servo on its shim in
   the engraved footprint, horn facing away from the BusLinker (+x), tabs in
   their engraved rectangles. Clamp, turn the whole thing over, and drill #31
   (0.120") up through the four tab pilots into the tabs. Then drill all the
   red (`CUT_PILOT`) holes to 1/8".
4. Press the inserts: the four tab inserts from below, every other insert from
   the top. Screw the tabs down from the top. Connect the servo to the
   BusLinker and command position 500.
5. Bolt the adapter plate to the U base, then the U to the horn and the rear
   bearing, with the plate level.
6. Mount the tagbase on pattern A or B. The single engraved tick marks the A
   arm, the double tick the B arm.
7. Mount the BusLinker in its engraved rectangle, servo ports toward the servo.

## Plate drawings

`plates/teststand-{base,adapter}-plate-{in,mm}.dxf`. The inch files match
`Acrylic/multicharger-acrylic.dxf`; both carry `$INSUNITS`. Layers:

- `CUT` (white): outline and 2-56 clearance holes, cut to final size;
- `CUT_PILOT` (red): insert holes at 0.118", drilled to 1/8" after cutting;
- `ENGRAVE` (blue): placement rectangles (servo/shim footprint, the two L
  tabs, the BusLinker), the tilt axis, and the A/B keys.

| base plate, 150 × 120 mm | adapter plate, 51 × 51 mm cross |
|---|---|
| ![](renders/teststand-base-plate.svg.png) | ![](renders/teststand-adapter-plate.svg.png) |

Coordinates in mm. The base plate's origin is the servo/bracket centre; the
adapter plate's is the U-bracket ring centre. x is along the tilt axis.

| plate | x | y | laser | final | role |
|---|---|---|---|---|---|
| base | ±24 | ±7 | 0.118" | 0.125" | bracket-tab inserts, pressed from below; the pilots first guide #31 into the tabs |
| base | −69, −41 | ±18 | 0.118" | 0.125" | BusLinker inserts (36 × 28 pattern, from Hiwonder) |
| base | −75, 55 | ±50 | 0.118" | 0.125" | foot inserts, optional |
| adapter | ±5 | ±5 | 0.106" | 0.106" | U bracket, countersunk from the top |
| adapter | ±9.5 | ±21 | 0.118" | 0.125" | tagbase pattern A |
| adapter | ±21 | ±9.5 | 0.118" | 0.125" | tagbase pattern B |

## Sources for the numbers

- **Brackets:** Hiwonder's dimension drawings on the [bracket product
  page](https://www.hiwonder.com/products/servo-bracket-compatible-with-lx-16a).
  - Bottom bracket: 35 × 25 floor, 14 mm flanges, eight Ø2 holes on a Ø14 ring.
  - Straight U: 40 × 22 base, 38 mm arms, 2 mm sheet. The base has four Ø3
    holes at (±5, ±5), four Ø2 on-axis and a Ø7 centre. The horn centre is
    34 mm below the base's outer face.
  - Hole positions were measured off the drawings, consistent with the 10 and
    14 mm dimensions. The designer checked this reading against the drawing,
    2026-10-19.
- **LX-16A:** 45.22 × 24.72 × 36.3 mm, 6–8.4 V, 0–240°, 0.19 s/60° at 7.4 V
  ([Hiwonder](https://www.hiwonder.com/products/lx-16a)).
- **BusLinker V3.0:** 42 × 33 × 15 mm, holes 36 × 28, 5–14 V; holes 3 mm on 28 × 36 mm centres, both measured by the designer 2026-10-19
  ([manual](https://docs.hiwonder.com/projects/BusLinker/en/latest/docs/1_BusLinker_V3.0_Servo_Debugging_Board_User_Manual.html)).
- **Insert:** McMaster's table row for 94615A111. Its page cannot be fetched
  automatically, so the cross-reference to E-Z LOK 260-002BR (0.125" hole)
  comes from [Olander](https://www.olander.com/items/260-002BR).
- **tagbase-v7:** read from `BoardDesigns/Bases/tagbase-v7/tagbase-v7.kicad_pcb`
  (holes, outline) and from its `kicad-cli` 3D export (underside fit). The
  board is 50.8 × 69.85 mm, with H1–H4 2.5 mm holes at (±21, ±9.5) about their
  centroid.

### VERIFY: inferred, not read off a drawing

Apart from the last row, none of these affect the plates; they move the 3D
model and the tilt limits, which have a large margin over the ±90° the tests
need. Measure them when the servo and brackets arrive, before cutting; each is
one parameter in `teststand.py`, and `make all` rebuilds and rechecks.

| parameter | value | assumed | affects |
|---|---|---|---|
| `SHAFT_FROM_TOP` | servo shaft below the servo top | 11.5 mm | axis height (35.0 mm above the base plate) |
| `BOT_T` | bottom-bracket sheet thickness | 1.0 mm | servo depth between the flanges (35 − 2t), the shim, where the flanges sit |
| `HORN_PROUD` | horn beyond the body; the rear bearing takes the rest of the U's 36 mm | 2.5 mm | where the U is centred |
| `U_BRKT["bend_r"]` | U bracket outer bend radius | 3 mm (anything ≥ 1.6 clears the B inserts) | the B-pattern insert tails |
| `TAB_INSERTS` | tab inserts at (±24, ±7) | the tabs reach x ≈ ±34 | **the base plate.** Check that ±24 lands on the flat of the tab, clear of the bend. |

The servo, horn, brackets and BusLinker are envelope solids in the model. The
GrabCAD LX-16A model needs a login, so it was not used. Dropping it into
FreeCAD over the `LX16A` envelope would settle the first and third rows.

## Files and how to rebuild

```
teststand.py       parameters and plate geometry; the one source of truth
make_plates.py     plates/*.dxf, *.svg
build_model.py     teststand.FCStd, out/teststand-assembly.step, out/checks.txt
render.py          renders/*.png
```

`make all`, or `make plates` / `make model` / `make renders`. The model step
needs FreeCAD 1.1 (`freecadcmd`) and KiCad (`kicad-cli`, for the tagbase's 3D
export). Renders need pyvista (`~/cq-env`). Both plates are checked for edge
distance (≥ 2.5 mm) and webs (≥ 1.5 mm) on every build. The DXFs were
re-imported into FreeCAD and all 24 holes matched.

In `teststand.FCStd`, the `Rotor` App::Part tilts about the line
x, through (0, 0, 35.0). Pose it by editing Rotor → Placement → Angle.
`TagbaseB` and `TagSpacersB` are hidden; swap visibility with the A parts to
see orientation B.
