# imutag-nand-bmp581 Design Review

## Review 2 — 2026-09-01: PCBWay production release

Scope: the PCBWay fabrication package, which did not exist at the 2026-08-26 review
("Gerber review: not performed"). The review ran across four rounds of fixes and closed against
`pcbway_production/2026-09-01-10-01-52/`, the only export kept — the six superseded ones were
pruned. The schematic conclusions in Review 1 stand and are not re-litigated here.

Datasheets: `BoardDesigns/libraries/datasheets`.

### Verdict — ready to fabricate

**Order it.** Every blocker is fixed and the final export is verified against the board on disk.

The review opened with one genuine blocker: both inner planes ran flush to the routed profile,
with `+1V8` on In1 and `GND` on In2 separated by 0.08 mm of core, invisible to DRC because
`min_copper_edge_clearance` was 0. That is fixed at 0.3005 mm. Along the way the CRST capacitor
was re-sourced (Bosch's recommended part is obsolete and was never the right case size), and
the via annular ring was raised from 4.00 to 6.00 mil to meet PCBWay's published minimum.

Order as **4 layers, 0.4 mm finished thickness, immersion silver**, confirming copper weight for
a thin 4-layer stack. Immersion silver is the one non-obvious call: it gives BGA-suitable
flatness without ENIG's electroless nickel, which would otherwise sit 0.62 mm from the BMM350
under J201 — a real cost on a board whose entire purpose is magnetic cleanliness.

**Three of the ten findings were withdrawn as raised in error** (4, 5 and 8). All three came from
trusting my own derivation over the fact that these boards have been built successfully, and one
rested on a straight arithmetic mistake. They are kept in place rather than deleted so the
reasoning is on record and the next review does not re-raise them.

### What I verified as correct

These were checked and are fine — recorded so the next review does not redo them.

- **Gerbers match the board on disk.** The uncommitted zone refill moved an `In1.Cu` vertex
  from `(146.716888, 111.715622)` to `(146.628375, 111.627108)`. The shipped `In1_Cu.gbr`
  contains the new vertex (`X6628375Y1372892`) and not the old one. The export is current.
- **Drill reconciles exactly.** PTH = 3 holes @ 0.2032 mm + 41 @ 0.254 mm = 44, matching the
  44 vias in the PCB. NPTH = 4 @ 1.1 mm, matching mounting holes J301–J304.
- **BOM/CPL completeness.** 30 placed parts over 16 BOM lines, every line carrying both MPN
  and LCSC. The six `J*` references absent from both files are all explicitly
  `exclude_from_pos_files exclude_from_bom`: J301–J304 (mounting holes), J401 (battery pads),
  J201 (6 test pads). Nothing is missing.
- **CPL coordinate frame is what PCBWay expects.** Origin at the board lower-left, Y up,
  bottom-side parts *not* mirrored. Verified numerically: U302's CPL position
  `(13.097913, 5.633429)` and U6's `(5.745, 5.85)` are exactly the centroids of their
  exposed-pad paste apertures in `B_Paste.gbr`.
- **Exposed pads are on GND and in-pad vias are GND-on-GND.** U302 pad 33 and U6 pad 9 are
  both `GND`, and all four vias landing inside them are `GND` — the house expectation for
  via-in-pad under a QFN holds again here.
- **Vias are tented everywhere else.** Neither mask layer contains a 0.4064 or 0.4572 circular
  aperture, so no via outside the exposed pads is opened.
- **Paste is correctly withheld** from J401's battery pads and J201's six test pads — both have
  copper and mask but no paste aperture.
- **Silk is knocked out around pads** using clear polarity, so no silk lands on a solderable
  surface.
- **Mask dams clear the fab minimum.** The tightest is under U2 (BMM350) at 0.4 mm pitch with
  0.2286 mm openings, leaving a 0.1714 mm web against a 0.1 mm minimum.
- **Two apertures that look alarming are not defects.** `C,0.010000` in `F_Paste` (992 draws,
  19 flashes) and `C,0.000000` in `F_SilkS` are KiCad stroking custom-pad and pin-1-marker
  polygon outlines alongside `G36` regions. Standard output; CAM handles it.

### Findings

#### 1. Both inner planes are flush with the board profile — fix before ordering

Severity: **high** · Confidence: high · **Fixed 2026-09-01, but see the 0.3 mm note below** ·
Evidence: `In1_Cu.gbr`, `In2_Cu.gbr`, geometric test against the Edge_Cuts profile

`In1.Cu` carries the `+1V8` plane and `In2.Cu` carries the `GND` plane. Measuring every region
vertex against the actual rounded-rectangle profile (21.5 × 11.5 mm, r = 1.0 mm):

```text
In1_Cu (+1V8):  min copper-to-edge = 0.0005 mm   (129 vertices sitting on the profile)
In2_Cu (GND):   min copper-to-edge = 0.0005 mm   (126 vertices sitting on the profile)
F_Cu:           pulled back 1.06-1.95 mm   (fine)
B_Cu:           pulled back 1.08-1.95 mm   (fine)
```

The pours are clipped to the outline exactly, so the router cuts through live copper on both
inner layers around the entire perimeter of every board. The two exposed nets are `+1V8` and
`GND`, on adjacent layers separated by 0.08 mm of core. A routing burr or copper smear along
the cut face therefore has a credible path to short the regulated rail to ground — on a
battery-powered tag with no series protection on `+1V8`.

This is invisible to DRC because the project sets `min_copper_edge_clearance = 0.0`, so KiCad
will never flag it no matter how many times it is run. That is why Review 1's clean DRC did
not catch it.

Fix: set copper-to-edge clearance to 0.2–0.3 mm (PCBWay's guidance is 0.3 mm) and refill. On a
21.5 × 11.5 mm board with the outer layers already pulled back over 1 mm, losing 0.3 mm of
plane perimeter costs essentially nothing electrically. PCBWay's CAM *may* clip this for you,
but they may equally build exactly what you sent, and it is not worth the coin flip.

**Update 2026-09-01 — fixed, but set it to 0.3 mm.** `min_copper_edge_clearance` is now 0.2 mm
and the zones were refilled. Measured against the profile in the 08-53-22 Gerbers:

```text
In1_Cu (+1V8):  0.2005 mm   (was 0.0005)
In2_Cu (GND):   0.2005 mm   (was 0.0005)
F_Cu / B_Cu:    1.0000 mm
```

DRC is clean and now actually enforces the rule. One thing to change before ordering:
**PCBWay's own guidance is copper ≥ 0.3 mm from the board edge.** 0.2 mm clears the physical
risk but sits under their stated figure, so it is still a candidate for an engineering query.
Bumping the rule to 0.3 mm and refilling costs nothing here — the outer layers are already
pulled back 1.0 mm, and the inner planes lose 0.1 mm of perimeter.

#### 2. Surface finish is unspecified — and the obvious choice fights the magnetometer

Severity: **medium** · Confidence: high · Evidence: `.kicad_pcb` stackup block, placement
geometry, BMM350 datasheet §5.1

The stackup block ends with `(copper_finish "None")`. Nothing in the package tells PCBWay what
finish to apply, so this will be decided by whatever you pick on the order form.

The two pressures point in opposite directions:

- U2 is a 9-ball BGA at 0.4 mm pitch with 0.2286 mm pads, and U302/U6 are 0.5 mm-pitch
  leadless parts. That combination normally argues for **ENIG** — flat, solderable, good shelf
  life.
- ENIG deposits 3–6 µm of **electroless nickel**, which is ferromagnetic. J201's six 0.762 mm
  contact pads sit **0.62 mm** from the BMM350 — the closest object on the board to the sensor,
  directly beneath it on the opposite side.

Nickel there is a soft-iron distortion source: it perturbs the ambient field rather than adding
a fixed offset, so it is calibratable, but the calibration becomes assembly-specific and
temperature-dependent — which is exactly the cost this LDO revision was meant to avoid paying
elsewhere. Nickel-free alternatives (immersion silver, OSP) remove the problem but trade away
some fine-pitch assembly margin and shelf life.

I am flagging the tension rather than picking for you, because it depends on how much
per-unit calibration effort you are willing to carry. What is not optional is *making the
choice explicitly on the order* — leaving it blank guarantees you get whatever is cheapest.

#### 3. Stackup is 0.38 mm, which is not PCBWay's default

Severity: **medium** · Confidence: high · Evidence: `.kicad_pcb` stackup block

```text
F.Cu 0.035 | prepreg 0.08 | In1.Cu 0.035 | core 0.08 | In2.Cu 0.035 | prepreg 0.08 | B.Cu 0.035
                                                        => 0.38 mm finished (+ ~0.02 mm mask)
```

PCBWay's default 4-layer board is 1.6 mm. A 0.38 mm 4-layer build is available but is a
specified option, not a default, and the difference is not something CAM will infer from the
Gerbers. If this is not stated explicitly on the order you will receive a board four times too
thick for the enclosure. Drill aspect ratio at this thickness is a comfortable 1.9:1.

#### 4. ~~Solder mask expansion is zero board-wide~~ — WITHDRAWN, not a defect

Severity: **none — I got this wrong** · Evidence: U2 footprint pad definitions,
`pad_to_mask_clearance` across all 30 boards in this repo, designer's build history

I originally raised zero mask expansion as a medium finding, calling the BMM350 land
"degenerate — neither SMD nor NSMD." That was wrong on the facts. Recording why, so it does
not get re-raised.

**The footprint is fine.** `libraries:BGA9_BMM350_BOS` is an UltraLibrarian part and defines
nine 0.2286 mm circular pads on a 0.40005 mm pitch, every one with
`solder_mask_margin = inherit`. Leaving mask margin to inherit is *correct* behaviour for a
footprint generator — mask expansion is a fab/process choice, not a property of the land
pattern. UltraLibrarian is not asserting zero expansion; it is declining to assert anything.

**The zero is KiCad's default, not a decision.** `pad_to_mask_clearance 0` appears in
**29 of the 30 boards** in this repo (only MultiCharger differs, at 0.11 mm). It is what every
KiCad board carries unless someone deliberately changes it.

**And zero in the file is not zero on the board.** Fab CAM applies its own minimum mask
expansion — typically ~0.05 mm per side — because an opening exactly equal to the pad is not
manufacturable against registration tolerance. So the delivered part is NSMD, with the mask
openings larger than the metal pads and the land defined by the copper. Re-reading Bosch §5.1
against that: NSMD is one of the two cases it explicitly sanctions, and the 0.2286 mm pads
*are* the land definition. The design does what the datasheet asks.

**Empirically settled.** The designer has built this footprint successfully several times. That
is the strongest evidence available and it agrees with the analysis above.

What I mistook for a defect was the pre-CAM state of the Gerber. Reading equal pad and mask
apertures and concluding the land geometry is uncontrolled ignores that every fab expands the
mask itself. No action.

#### 5. ~~Unplugged vias inside both exposed pads, against low paste coverage~~ — WITHDRAWN

Severity: **none — I got this wrong too** · Evidence: recomputed Gerber apertures, footprint
paste definitions, via-in-EP survey across the imutag family, PCBWay 0.4 mm defaults

Both halves of this finding were wrong. Recording the correction and the reason, because the
measurement error is an easy one to repeat.

**The paste coverage claim was a units error on my part.** I reported 25.3% (U302) and 27.8%
(U6) by reading the `RoundRect` aperture macro's corner coordinates as the outer extents of the
aperture. They are not — they are the *centres of the corner circles*, so the rounding radius
extends a further 0.25 mm beyond them on each side. Recomputed correctly:

```text
U302  4 x (1.41 x 1.41 mm, r=0.25)  = 7.74 mm2 over a 12.25 mm2 pad  ->  63.2%
U6    4 x (1.73 x 1.37 mm, r=0.25)  = 9.27 mm2 over a 14.62 mm2 pad  ->  63.4%
```

That is squarely inside the usual 50–80% band, and it matches the footprints, which define
1.41 mm square paste apertures directly. It also matches the rest of the family: imutag-nand,
imutag-smps, imutag-4layer and imutag all sit at 64.9–65.4% on U302. There was never a paste
shortfall.

**The via-in-pad concern is the house pattern, not a defect.** Every board in this family puts
GND vias inside the exposed pads:

```text
imutag-nand         5 vias in EPs (U302, U6)
imutag-smps         5 vias in EPs (U302, U6)
imutag-4layer       3 vias in EPs (U302)
imutag              3 vias in EPs (U302)
imutag-nand-bmp581  4 vias in EPs (U302, U6)
```

Four of those boards have been built. The vias are GND-on-GND into a GND exposed pad, and with
paste at 63% rather than the 25% I miscalculated, there is ample solder volume relative to the
barrels. **PCBWay also tents vias by default on 0.4 mm boards**, which settles the other 40
vias on this board outright.

The one technically-true observation that survives — that mask tenting cannot close a via lying
inside a pad's mask opening — is a fact about KiCad and about mask artwork, not a defect in this
design. If you ever *do* want those four closed, it is a fab process (filled + capped, POFV)
ordered explicitly, or move the vias. Neither is warranted here. No action.

#### 6. CRST capacitor: Bosch's recommended part is obsolete and never fitted this board

Severity: **low-medium** · Confidence: high · **Fixed 2026-09-01** · Evidence: BMM350
datasheet §5.3 and §13, BOM, courtyard geometry, TDK/DigiKey listings

> **Resolved.** C4 is now `GRM155Z71A225KE01D` (LCSC `C2997286`) in schematic, PCB and BOM,
> on the unchanged `C_0402_1005Metric` land.

C4 is `GRM155R6YA225KE11D` — a standard Murata 0402 X5R — 2.37 mm from the magnetometer.
Bosch asks for more than the right value:

> 2.2uF capacitor to CRST, 200mA peak current, need low resistance, low inductance type and
> **non-magnetic properties**.

and §13 names TDK `CGB4B3X7R0J225K055AB`. Two things about that recommendation:

- **It is obsolete.** DigiKey lists it as no longer manufactured, so it is not a route forward
  regardless.
- **It is an 0805.** C4's land is 0402 (1005 metric), so Bosch's part was never a drop-in here.

And a caution on reading §13 as the fix for §5.3: CGB is TDK's *soft-termination* line — a
conductive-resin layer for flex-crack resistance. Soft termination is not the same as
nickel-free, and §13 justifies the part as "low-inductance low-ESR", not as non-magnetic. So
the named part probably does not satisfy the non-magnetic bullet either.

**The layout constrains this heavily.** C4 is boxed in — courtyard gaps of 0.090 mm to C506,
0.070 mm to R2 and 0.130 mm to R3. There is no room to grow to 0603 (let alone 0805) without
moving all three neighbours.

**What actually matters here, in order:**

1. **Effective capacitance under DC bias.** The magnetic reset fires *every ODR tick* in normal
   and forced mode, each time pulling 400 mA for under a microsecond out of this cap. A 0402
   2.2 µF derates hard under bias; that is precisely why Bosch reached for an 0805 X7R.
2. **Low ESR/ESL.** Routing is already good — `Net-(U2-CRST)` is 2.96 mm total, entirely on
   F.Cu. Widening the 0.1016 mm portion to a uniform 0.254 mm would trim a little more.
3. **X7R over X5R.** The fitted part is X5R (−55…+85 °C); X7R holds to +125 °C and is flatter
   over the tag's range.
4. **Non-magnetic.** Genuinely Ni-free MLCCs (Knowles/Syfer, Presidio) are a specialty class —
   larger cases, long lead times, and not offered at 2.2 µF in anything near 0402.

**On the non-magnetic point specifically — check the budget before spending effort.** C4 is
only the *fourth* closest passive to the BMM350: C506 sits at 1.44 mm, C505 at 1.75 mm and R3
at 1.76 mm, all with the same nickel-barrier terminations, and thick-film resistors have them
too. Since a dipole's field falls as 1/r³, C506 alone contributes several times what C4 does.
And per finding 2, choosing ENIG would put far more nickel at 0.62 mm. Singling out C4 while
leaving those alone does not move the needle — *unless* the reason is the pulse current rather
than proximity, which is the one thing that genuinely distinguishes C4. That is a plausible
reading of why Bosch flags this cap and not the decoupling caps, but the datasheet does not say
so outright, so treat it as inference.

**Recommendation — a 0402, i.e. a drop-in for the existing land. Do not fit an 0805; the
only 0805 mentioned above is Bosch's obsolete part, which does not fit this board.** Keep the
existing `C_0402_1005Metric` footprint and upgrade the dielectric and voltage rating, which
buys most of the real benefit (bias retention, temperature stability) at zero layout cost:

```text
Murata GRM155Z71A225KE01D  -  2.2 uF +/-10%, 10 V, X7R, 0402 (1005 metric)
                              LCSC C2997286
```

Listed as X7R 0402 by DigiKey, TME, Arrow, TTI and LCSC, and in stock. It also carries an LCSC
number, which matters here — every other line in this BOM has one. The higher voltage rating is the point: it derates far
less at the CRST bias than a 6.3 V part, so the *effective* capacitance backing the reset pulse
is closer to the nameplate 2.2 µF.

If the magnetic reset later proves marginal on the bench, the next step is a local re-layout to
free space for a 0603 X7R — not a specialty non-magnetic part, which only makes sense as part
of a wider decision to drop ENIG and address the closer passives too.

#### 7. Silkscreen strokes below fab minimum

Severity: **low** · Confidence: high · Evidence: silk aperture usage counts

PCBWay's minimum silkscreen line width is 0.15 mm. Actual dark strokes:

```text
F_SilkS:  0.100 mm x 2,  0.120 mm x 6,  0.140357 mm x 2,  (0.15 / 0.1524 / 0.20 fine)
B_SilkS:  0.120 mm x 31, 0.150 mm x 54
```

The 31 sub-minimum strokes on the bottom are the notable ones — they will print thin, broken,
or be dropped in CAM. Cosmetic only, but the board's own default is already
`silk_line_width = 0.15`, so these are footprint-local overrides worth normalizing.

#### 8. ~~No `.gbrjob` in the archive~~ — WITHDRAWN, optional

Severity: **none** · Evidence: CompassTag's shipped fab packages, five PCBWay plugin exports

A `.gbrjob` carries layer order, board thickness, copper finish and board size — metadata that
otherwise reaches the fab only via the order form. It is generated by KiCad's Plot dialog
("Generate Gerber job file"), by `kicad-cli pcb export gerbers` automatically, or by kibot with
`create_gerber_job_file: true`. It belongs alongside the Gerbers inside the zip.

You do not need one here:

- **CompassTag was fabbed without it.** Its `pcbway_production` (31 files) and `jlcpcb`
  (29 files) packages both contain no `.gbrjob`, and that board went to fab.
- **The PCBWay KiCad plugin never emits one** — 86 files across five export runs on this board,
  zero `.gbrjob`.
- The layer filenames here are unambiguous (`F_Cu`, `In1_Cu`, `In2_Cu`, `B_Cu`), and thickness
  and finish must be stated on the order form regardless.

Getting one would mean exporting through a different path than the plugin, which would also
change aperture macros, X2 attributes and file extensions — disturbing a working flow for a file
the fab does not need. No action.

#### 9. Stale BitTagNG files corrupted the last analysis run

Severity: **medium** (for review integrity, not for the board) · Confidence: high · **Resolved 2026-09-01**

You flagged these as obsolete, and they did real damage. The directory still holds:

```text
BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pcb
BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro
BitTagNG.kibot.yaml
BitTagNG.kicad_sym
```

`analysis/2026-08-26_1027-2/pcb.json` records:

```json
"project_settings":        { "source":       "BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro" }
"design_rule_compliance":  { "rules_source": "BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro" }
```

The PCB analyzer picked up BitTagNG's project file instead of `imutag-nand-bmp581.kicad_pro`,
so **every rule-derived number in Review 1's PCB section was measured against the wrong rule
set.** The visible symptom is a reported violation:

> Min Via Diameter 0.406mm violates project minimum (0.457mm)

imutag's own rules set `min_via_diameter = 0.4064`, so the three small vias are compliant. That
finding was an artifact of the wrong project file.

`analysis/manifest.json` also still records `"project": "BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro"`,
and `CMakeLists.txt` contains `add_pcb_outputs(BitTagNG)`. Deleting the four files and
correcting those two references makes the next analysis run trustworthy.

**Resolved.** `BitTagNG-LIS2DU12.kicad_pcb-back.{kicad_pcb,kicad_pro}` and `BitTagNG.kicad_sym`
are deleted; `BitTagNG.kibot.yaml` is renamed `imutag-nand-bmp581.kibot.yaml` and
`CMakeLists.txt` now reads `add_pcb_outputs(imutag-nand-bmp581)` — that target had been dead,
since it depended on a `BitTagNG.kicad_sch`/`.kicad_pcb` pair that does not exist here.
`analysis/manifest.json` now names `imutag-nand-bmp581.kicad_pro`.

`BitTagNG.kicad_sym` was **not** simply deleted: it defined `RV-3028-C7-AccelTag`, U501's live
symbol. U501 was repointed to `libraries:RV-3028-C7` from `tag_library.kicad_sym`, whose pin
numbers and names are identical. Net connectivity was verified unchanged — 37 nets, 145 pin
connections, zero differences before and after. The one behavioural difference is that the old
symbol typed pin 5 (GND) as `power_out`, which had been silently satisfying ERC's
power-driven check for the whole GND net; the `tag_library` symbol types it `input`, which
exposed a `power_pin_not_driven` error on U1. A `PWR_FLAG` was added on GND (`#FLG0103`,
wired to the GND symbol at 243.84, 115.57), restoring ERC to its single accepted `VBAT`/`VIN`
warning. That is a latent modeling error fixed, not a workaround.

**This is repo-wide.** The same stale `BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro` sits in
about ten other board directories — BitPresTagBMP585, CompassTag, CompassTagMMC5603, imutag,
imutag-smps, imutag-4layer, imutag-nand, BitPresTag, TorporTag. Any analyzer run in those
directories is liable to pick it up as the project file the same way, so their rule-derived
findings deserve the same scepticism until the file is removed.

#### 10. The fab package was built from uncommitted work

Severity: **low** · Confidence: high

`imutag-nand-bmp581.kicad_pcb` has an uncommitted zone-refill change, and finding "Gerbers
match the board" above confirms the shipped Gerbers were plotted from that working-tree state.
The package about to be manufactured therefore corresponds to no commit. Commit before
ordering so the boards that come back are traceable.

### Before-order checklist

All items closed.

1. ~~Set copper-to-edge clearance, refill both inner zones, re-plot.~~ **Done** — 0.3005 mm.
2. **Surface finish: immersion silver** — see finding 2. Must be stated on the order.
3. **State 0.4 mm finished thickness explicitly** — PCBWay's default is 1.6 mm.
4. ~~Decide SMD vs NSMD for U2 and set a non-zero mask expansion.~~ **Withdrawn** — finding 4.
5. ~~Tent or plug the four vias inside the U302/U6 exposed pads.~~ **Withdrawn** — finding 5.
6. ~~Re-source C4.~~ **Done** — `GRM155Z71A225KE01D`, 2.2 µF 10 V X7R 0402, LCSC `C2997286`.
7. ~~Normalize sub-0.15 mm silk strokes.~~ **Accepted by designer.** `libraries:RV-3028-C8` was
   fixed to 0.15 mm; 27 strokes at 0.12 mm remain in KiCad stock footprints. Cosmetic.
8. ~~Include the `.gbrjob` in the archive.~~ **Withdrawn** — finding 8.
9. ~~Delete the BitTagNG files; fix `analysis/manifest.json` and `CMakeLists.txt`.~~ **Done** —
   finding 9, and swept across the other nine board directories.
10. ~~Raise the via annular ring to meet PCBWay's minimum.~~ **Done** — 6.00 mil on all 44.
11. **Commit, then order from the committed state.** The package still corresponds to no commit.

### Final pre-order state — 2026-09-01 10:01

Everything raised in Review 2 is now either fixed or withdrawn. Verified against
`pcbway_production/2026-09-01-10-01-52`, which I confirmed matches the board on disk.

| Item | State |
|---|---|
| Inner copper to board edge | **0.3005 mm** (was 0.0005) — meets PCBWay's 0.3 mm |
| Via annular ring | **0.1524 mm (6.00 mil)** on all 44, single drill tool |
| C4 CRST capacitor | `GRM155Z71A225KE01D`, 2.2 µF 10 V X7R 0402, LCSC `C2997286` |
| KiCad DRC | 0 violations, 0 unconnected, 0 parity |
| KiCad ERC | 1 warning — the accepted `VBAT`/`VIN` merge |
| Drill reconciliation | PTH 44 = via count; NPTH 4 = J301–J304 |
| BOM / CPL | 15 lines, 30 placements, exact CPL match, every line has MPN + LCSC |
| Silk under 0.15 mm | 27 strokes remain, **accepted by designer**; `RV-3028-C8` fixed to 0.15 |

Withdrawn as raised in error: mask expansion (finding 4), exposed-pad vias and paste
(finding 5), missing `.gbrjob` (finding 8).

**Order as:** 4 layers, 0.4 mm finished thickness, immersion silver, and confirm the copper
weight for a thin 4-layer stack. Nothing else needs flagging in the order notes — the annular
ring now meets their published minimum.

One residual foot-gun: the predefined via-size dropdown still lists 0.4064/0.2032 and
0.4572/0.254, both 4 mil. The net classes and `min_via_annular_width` are correct, so DRC will
catch a slip, but picking one of those presets by hand would reintroduce a sub-spec via.

### PCBWay order sheet — 4-layer, 0.4 mm

Checked against PCBWay's published capability set for the 2026-09-01 08:53:22 package.

**Clears their limits comfortably:**

| Parameter | This board | PCBWay 4-layer min |
|---|---|---|
| Trace width | 0.1016 mm | 0.09 mm |
| Trace spacing | ~0.1052 mm | 0.09 mm |
| Via drill | 0.2032 mm (×3), 0.254 mm (×41) | 0.15 mm |
| Board size | 21.5 × 11.5 mm | 3 × 3 mm |
| Thickness | 0.4 mm | 0.2–3.2 mm range |

**Annular ring — fixed 2026-09-01.** The board was at 0.1016 mm (4 mil) on all 44 vias, below
PCBWay's published 0.15 mm minimum. Now:

```text
41 vias  pad 0.5048 / drill 0.20  -> annular 0.1524 mm (6.00 mil)
 3 vias  pad 0.4548 / drill 0.15  -> annular 0.1524 mm (6.00 mil)
```

DRC clean, 0 unconnected, zones refilled, copper-to-edge still 0.3005 mm.

The insight worth keeping: **shrinking the drill is what buys the annular ring on this board,
not growing the pad.** Pad-growth options all fail — 0.51/0.20 and 0.55/0.20 give 4 clearance
violations, single-size 0.50/0.20 gives 1 — because the zones use a 0.508 mm `connect_pads`
clearance. And zones **must** be refilled after any via resize: without a refill DRC reports up
to 71 phantom clearance violations against the stale fill, which is enough to make a workable
option look impossible.

For the record, 4 mil was not actually unsafe here: **CompassTag shipped to PCBWay on
2026-05-11 with the identical 0.4572/0.254 via at 4.00 mil.** The change buys margin against
PCBWay's stated spec, not a fix for a defect.

**Settings that must be set explicitly (none are defaults):**

| Field | Set to | Why |
|---|---|---|
| Layers | 4 | — |
| Thickness | **0.4 mm** | PCBWay's default is 1.6 mm |
| Surface finish | **Immersion silver** — see below | nickel-free, BGA-flat |
| Copper weight | confirm inner/outer for a 0.4 mm stack | thin 4-layer often wants 0.5 oz inner |

**Surface finish — this resolves finding 2.** PCBWay offers immersion silver, immersion tin
and OSP alongside ENIG/ENEPIG. **Immersion silver is the answer to the tension in finding 2:**
it is flat and fine-pitch/BGA-friendly like ENIG, but deposits *no nickel*, so nothing
ferromagnetic ends up 0.62 mm from the BMM350 under J201. The trade is shelf life — immersion
silver tarnishes and dislikes sulphur-rich storage — which is a non-issue for boards assembled
soon after arrival, and a real one if they sit on a shelf for a year. ENIG remains the
fallback if storage time matters more than magnetic cleanliness.

**Still open in the 08-53-22 package** (all unchanged, all cheap to fix):

- Copper-to-edge is 0.2 mm; PCBWay wants ≥ 0.3 mm (finding 1 update).
- Silk still under the 0.15 mm minimum: 0.10 mm ×2, 0.12 mm ×6, 0.1404 mm ×2 on F.SilkS;
  0.12 mm ×31 on B.SilkS (finding 7).

**If ordering assembly rather than bare boards:**

- Minimum order is 5 boards.
- Turnkey sources by **MPN**, and all 15 BOM lines carry both MPN and LCSC — good.
- PCBWay's BOM wants `Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type`.
  The plugin's export uses different headers, so it needs reformatting.
- PCBWay's rotation convention can differ from KiCad's. The CPL frame itself is verified
  correct (origin lower-left, Y up, bottom parts unmirrored), but with a 0.4 mm-pitch BGA and
  0201 passives an assembly drawing is worth including.
- Assembly is **manually quoted, 1–2 business days** — not instant like JLCPCB. Budget for it.

### Carried forward unchanged from Review 1

Still true and not re-examined: the LDO-versus-SMPS architecture call, the `VBAT`/`VIN` merge
being intentional, the BOOT0/`/SDA` option-byte production step, panel fiducials in place of
board-level ones, `/clkout` as a 32 kHz low-risk clock, and the analyzer's plane-island and
plane-gap reports being layout geometry rather than disconnected copper.

As of 2026-09-01 all of that is machine-readable: this board now has a `.kicad-happy.json`
carrying the power profile, the mating/firmware contract, 13 rule suppressions with reasons,
the recurring analyzer false positives, what was verified correct on 2026-09-01, and the open
items above. `track_in_git` is set to `true` and there is no `analysis/.gitignore`, so future
analyzer runs and the hand-authored `deep_review.json` will be preserved.

---

## Review 1 — 2026-08-26: schematic and layout

Review date: 2026-08-26  
Project: `BoardDesigns/imutag-nand-bmp581`  
Primary design files: `imutag-nand-bmp581.kicad_sch`, `imutag-nand-bmp581.kicad_pcb`, `imutag-nand-bmp581.kicad_pro`  
Datasheet source used: `BoardDesigns/libraries/datasheets`  
Current analysis run: `analysis/2026-08-26_1027-2`

### Verdict

The latest revision is materially cleaner than the earlier LDO pass. D401 is now gone from both schematic and PCB, U5 and U6 metadata now match the schematic/BOM intent, KiCad DRC is clean, and KiCad ERC is down to one warning: `VBAT` and `VIN` are attached to the same net, with KiCad using `VBAT` in the netlist.

For the magnetometer question, this remains the lower-risk architecture versus `imutag-smps`: there is no local SMPS inductor or switching node near the BMM350. Given your current conclusion that forced-mode SMPS efficiency is essentially LDO-like, the LDO version is the better magnetic/noise choice. The cost is linear-regulator battery efficiency; at your stated 1-2.2 mA average current, the heat is negligible but the energy penalty is real.

I would treat this revision as close to fab-ready electrically. The direct `VBAT`/`VIN` merge is intentional for this LiPo-based design; the joined pins are inherited from a fixed interface that previously supported tiny coin cells with separate charging/feed paths, but that separation is not needed here. The remaining ERC warning is therefore schematic hygiene rather than an electrical concern.

The analyzer's "plane split", "island", and "plane gap" language remains manually downgraded as in the SMPS review. You clarified that the GND and +1V8 planes are connected and that many apparent holes occur where vias and layer changes require antipads. I am therefore treating those reports as local reference-continuity/geometry advisories, not as evidence of disconnected planes. `/clkout` is also treated as a 32 kHz low-risk clock.

### Review Basis

Tools and files checked:

- KiCad ERC: 1 warning, `multiple_net_names` for `VBAT` and `VIN` on the same net.
- KiCad DRC: 0 violations, 0 unconnected items.
- Schematic analyzer: 21 findings: 3 errors, 3 warnings, 15 info. The 3 errors are analyzer false positives or modeling limitations discussed below.
- PCB analyzer: 46 findings: 2 errors, 31 warnings, 13 info. The 2 errors are missing local fiducials; your fab-house panel-fiducial process makes those non-blocking.
- Cross-analysis: 10 findings: 4 errors, 6 warnings. These are all plane/reference-gap findings, manually downgraded per your layout explanation.
- EMC analyzer: 59 findings, risk score 37.0. Dominated by the same reference-plane/layer-transition heuristics plus clock/connector proximity warnings.
- Thermal analyzer: 0 findings, but 0 components had power-dissipation data, so this is not a thermal proof.
- Gerber review: not performed; no Gerber/fabrication outputs were present.
- SPICE: not performed; no ngspice, LTspice, or Xyce executable was available.
- Lifecycle/availability audit: not performed; no distributor API credentials were available and network access is restricted.

Datasheets manually cross-checked from the shared library:

- `tps7a02.pdf`
- `tps22916.pdf`
- `DS_00819_GD5F2GM7RE_Rev1_3-3435814.pdf`
- `stm32u375ce.pdf`
- `bst-bmm350-ds001.pdf`
- `bst-bmp581-ds004.pdf`
- `RV-3028-C8.pdf`
- `PMBT2222AMB.pdf`
- `lsm6dsv.pdf`

The project itself still has no local `datasheets/` directory, so the schematic analyzer emitted `DS-002`. For this review I used the shared `BoardDesigns/libraries/datasheets` directory.

### Feedback Carried Forward From imutag-smps

- Fab-house panel fiducials are acceptable for this manufacturing flow; board-level fiducial findings are not treated as blockers.
- STM32 PB7/BOOT0 shared with `/SDA` requires an explicit option-byte write and read-back verification in production programming.
- `/clkout` is 32 kHz, so clock-routing warnings for that net are low risk.
- Analyzer "islands" and "plane gaps" are not treated as disconnected planes when they arise from filled-polygon sampling, via antipads, and layer-change geometry.
- For magnetometer accuracy, calibration data is assembly-specific.
- Because the SMPS is increasingly a magnetometer noise risk and forced mode erases much of the SMPS efficiency advantage, this LDO variant is the cleaner magnetic/noise architecture at the cost of linear-regulator energy loss.
- Expected average current is 1-2.2 mA depending on sampling rate; use that range for battery-life and average LDO power calculations.

### Current Findings

#### 1. D401 removal and VBAT/VIN merge are intentional

Severity: pass / schematic cleanup  
Confidence: high  
Evidence: raw schematic/PCB grep, BOM, net trace, KiCad ERC, user interface-history note

There are no `D*` references remaining in the schematic or PCB. The power path is now:

```text
VBAT/VIN same net -> U4 TPS7A02185 LDO -> +1V8
                                      |
                                      +-- EN tied to VBAT

+1V8 -> U1 TPS22916 load switch -> /Flash 1V8 -> U6 NAND flash
```

KiCad correctly collapses the old `VIN` label onto `VBAT` and reports one ERC warning:

```text
Both VBAT and VIN are attached to the same items; VBAT will be used in the netlist.
```

Per the fixed-interface history, the joined pins are expected in this LiPo-based design. The older interface supported tiny coin cells and needed separate charging/feed paths; that is not a requirement here. To make ERC quiet and reduce future ambiguity, the remaining `VIN` labels could be renamed to `VBAT` or kept only as local text rather than a second global net label, but this is not a functional blocker.

Removing D401 also removes the old path-separation behavior, but that is acceptable for this LiPo architecture given the interface constraint above.

#### 2. LDO noise tradeoff remains favorable for the BMM350

Severity: design tradeoff  
Confidence: high  
Evidence: BOM, placement, raw net trace, TPS7A02 datasheet, user-provided current range

The current PCB has no SMPS inductor, no buck switch node, and no D401. The nearest active power parts to the BMM350 are:

- U1 load switch: 9.76 mm from U2
- U4 LDO: 11.14 mm from U2
- U6 NAND on the back side: 13.11 mm from U2

The closest ICs to the BMM350 are the BMP581 at 3.58 mm and the LSM6DSV at 7.16 mm, neither of which is a switching magnetic source. J201 is physically very close on the back side, but as a passive programming/contact structure it is more of a static assembly-calibration concern than a time-varying SMPS-noise source.

Average LDO dissipation is:

```text
P_LDO = (VBAT - 1.85 V) * I_LOAD
Battery-to-1V8 efficiency ~= 1.85 V / VBAT
```

Using your 1-2.2 mA average-current range:

| VBAT | Efficiency | Average LDO Heat |
|------|------------|------------------|
| 2.2 V | 84% | 0.35-0.77 mW |
| 3.0 V | 62% | 1.15-2.53 mW |
| 3.5 V | 53% | 1.65-3.63 mW |
| 4.0 V | 46% | 2.15-4.73 mW |
| 4.2 V | 44% | 2.35-5.17 mW |

Thermally, this is tiny. The decision is battery energy versus magnetometer cleanliness. Since forced-mode SMPS operation would give LDO-like efficiency while preserving switching and magnetic-noise concerns, the LDO choice is still the more coherent magnetometer-first architecture.

#### 3. TPS7A02185 implementation still looks good

Severity: pass  
Confidence: high  
Evidence: TPS7A02 datasheet and analyzer/raw PCB data

U4 is wired as a fixed 1.85 V LDO:

- Pin 1 OUT: `+1V8`
- Pins 2 and 5 GND/thermal pad: `GND`
- Pin 3 EN: `VBAT`
- Pin 4 IN: `VBAT`

The TPS7A02 datasheet requires at least 0.5 uF effective output capacitance for stability and recommends 1 uF or larger for transient response. It also recommends placing input and output capacitors close to the device. This board has:

- C8 = 1 uF on `+1V8`/`GND`, about 0.90 mm from U4.
- C9 = 0.1 uF on `+1V8`/`GND`, about 1.70 mm from U4.
- C7 = 10 uF on `VBAT`/`GND`, about 1.73 mm from U4.

The schematic analyzer still uses a generic 100 uA LDO quiescent-current estimate in sleep calculations. That is pessimistic for TPS7A02; the datasheet value is much lower. For this design's expected 1-2.2 mA average current, load current and the linear voltage drop dominate the energy model.

#### 4. U5/U6 metadata mismatch is resolved

Severity: pass  
Confidence: high  
Evidence: raw schematic/PCB properties and cross-analysis

The previous schematic/PCB mismatches are gone:

- U5 schematic and PCB now both say `LSM6DSV`, MPN `LSM6DSV`.
- U6 schematic and PCB now both say `GD5F2GM7REYIGR`, MPN `GD5F2GM7REYIGR`.
- Cross-analysis no longer emits the old `XV-002` value/MPN mismatch findings.

One minor cleanup remains: the U6 PCB footprint description and 3D model path still reference a `GD5F1...` package/model string. That should not affect electrical connectivity or BOM export because the value/MPN fields are fixed, but it is worth cleaning before documentation/export if you rely on 3D or footprint provenance.

#### 5. STM32 PB7/BOOT0 still needs production option-byte programming

Severity: medium bring-up/production risk  
Confidence: high  
Evidence: STM32U375 datasheet, net trace, carried-forward project requirement

U302 pin 30 is `BOOT0-PB7` and is routed as `/SDA`. `/SDA` has a 10 kOhm pull-up to `+1V8`. The intended boot behavior requires programming STM32 option bytes so the I2C pull-up does not force the wrong boot path.

Recommendation:

- Make the option-byte write an explicit production-programming step.
- Read back and log option bytes after programming.
- Document that PB7/BOOT0 is shared with `/SDA`.

#### 6. Remaining analyzer errors are not current electrical blockers

Severity: low / modeling artifacts  
Confidence: high  
Evidence: analyzer JSON, raw net trace, datasheets

The schematic analyzer still reports three errors:

- `PP-001`: U6 VCC has no DC path to a rail on `Flash 1V8`.
- `PR-001`: U5 dual-use pins look like an I2C bus missing pull-ups on `AT25_MOSI`/`AT25_SCK`.
- `PR-001`: companion missing pull-up warning for the same misidentified bus.

Manual interpretation:

- `Flash 1V8` is intentionally sourced through U1 TPS22916. The same analyzer's power-sequencing section recognizes U1 as a load switch source, so this is a rail-source modeling limitation.
- U5 is being used in SPI mode, not I2C mode on the AT25 nets. LSM6DSV uses dual-function pin naming, and the analyzer mistakes those pins for an I2C bus.
- KiCad ERC no longer reports the earlier BMP581 VSS power-output errors, so that symbol hygiene issue appears fixed.

Firmware contract:

- Keep all SPI chip selects inactive except the selected device.
- Drive U5 CS so the LSM6DSV stays in the intended SPI mode.
- Keep `/Flash 1V8` disabled whenever NAND leakage or bus back-powering would matter.

#### 7. Plane/reference findings remain advisory

Severity: low / advisory  
Confidence: high for manual override; medium for residual EMC margin  
Evidence: cross-analysis, EMC analyzer, carried-forward layout interpretation

Cross-analysis reports 10 findings, all related to plane/reference geometry:

- `/clkout` and `SWCLK` crossing GND reference gaps.
- SPI nets crossing GND reference gaps.
- VBAT, GND, and `+1V8` reported as multiple islands.

The EMC analyzer reports the same family of issues: 59 total findings with a risk score of 37.0, dominated by reference-plane sampling, layer-transition stitching, and clock/connector proximity. Given your clarification, these are not treated as proof of disconnected planes. The residual real-world guidance is narrower: where a signal changes layers, keep the nearest practical GND return via nearby when geometry allows. `/clkout` is 32 kHz and low priority; `/AT25_SCK`, SWCLK, and fast SPI edges are the more relevant nets if emissions ever show up on the bench.

### Manufacturing / Layout Notes

- Board: 21.5 mm x 11.5 mm, 4 copper layers, 36 footprints, 418 track segments, 44 vias.
- Routing: complete, 0 unrouted nets.
- KiCad DRC: clean.
- Process class: still an advanced-process layout by generic DFM thresholds: 0.1016 mm minimum trace width, about 0.1052 mm minimum spacing, 0.2032 mm minimum drill, 0.102 mm annular ring.
- Fiducials: analyzer flags missing board-level fiducials on both sides, but fab-house panel fiducials are accepted for this flow.
- Edge clearance: C10 and C507 are 0.68 mm from board edge; C502 is 0.97 mm.
- Via-in-pad: J401 pad 2 still has an untented via-in-pad warning.
- Thermal pad scan: U302 has 7 nearby GND vias; U6 has 8 nearby GND vias. The analyzer's "insufficient" warning uses a generic 9-via threshold, so treat this as assembly/paste/via-treatment review rather than a thermal blocker.
- Test access: analyzer found no dedicated test points; document connector-based access if that is the intended production test strategy.

### Positive Findings

- No local SMPS inductor or switching node near the BMM350.
- D401 is fully removed from schematic and PCB.
- KiCad DRC is clean: 0 violations and 0 unconnected items.
- KiCad ERC is down to one intentional/cleanup warning for the joined `VBAT`/`VIN` labels.
- Schematic and PCB footprint counts match: 36 components/footprints.
- All BOM components have MPNs populated.
- U5/U6 schematic and PCB metadata now match.
- TPS7A02185 input/output capacitors are close and match datasheet guidance.
- BMM350 CRST implementation remains correct: C4 = 2.2 uF on CRST to GND near U2. The analyzer "missing pull-up" warning is a false positive.
- `/Flash 1V8` is correctly sourced through U1 TPS22916 VOUT; the analyzer's DC-path warning is a load-switch modeling limitation.

### Not Performed / Review Limits

- Lifecycle audit was not performed because network access is restricted and no distributor API credentials are present.
- Gerber analysis was not performed because no fabrication outputs were present.
- SPICE simulation was not performed because no supported simulator was installed.
- Thermal analyzer found 0 hot spots but had 0 component power-dissipation inputs; using the stated 1-2.2 mA average current, LDO average heat is negligible.
- Datasheet extraction cache was not present locally; this review used manual checks against the shared datasheet PDFs.

### Suggested Before-Fab Checklist

1. Optionally rename/remove the remaining `VIN` global labels if you want ERC fully clean.
2. Confirm battery-life impact using the 1-2.2 mA average current range and the expected battery voltage profile.
3. Add/read-back-verify the STM32 BOOT0 option-byte write in the programming flow.
4. Clean the stale U6 footprint description/3D model reference if it matters for documentation or mechanical review.
5. Confirm advanced PCB process assumptions with the intended fab.
6. Review J401 via-in-pad and exposed-pad paste/via treatment with the assembler.
