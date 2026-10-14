# UIUCTag Design Review

**Project:** UIUCTag (KiCad 10, single sheet, 4-layer 0.4 mm PCB, 19.0 × 10.0 mm)
**Date:** 2026-10-14
**Analyzers:** `analyze_schematic.py`, `analyze_pcb.py --full`, `cross_analysis.py`,
`analyze_emc.py`, `analyze_thermal.py --ambient 38`, KiCad DRC/ERC (`kicad-cli`),
`padnet_crosscheck.py`, `stm32_pinmap.py`, `analysis/helpers/u2_fit_check.py`,
and a deep-review evidence gate. All of these ran on run `2026-10-14_0954`, and
its `rules_source` is `UIUCTag.kicad_pro`.
After the board extension and the S1/S2 edits, DRC/ERC, the analyzers and
`padnet_crosscheck.py` were re-run on the changed files, with the same results
except where noted.

## Overview

UIUCTag is BitPresTagBMP585 with the accelerometer changed from the ADXL367 to the
**ADXL362**. The rest is unchanged: an STM32L432KC on an unregulated coin-cell rail,
a BMP585 pressure sensor (power-gated from PB1), an AT25FF321A flash and an
RV-3028 RTC whose CLKOUT drives the LSE. The tag is worn by birds and mates to a
connecting board through the J201 pogo array. The ADXL362 is used **only for
activity detection** and never in measurement mode (designer, 2026-10-14). Its
interrupt is **INT2 → PA0/WKUP1**.

## Verdict

**The board is electrically ready to fabricate. No critical findings.**
The ADXL362 is wired, decoupled and powered correctly. After this review the far
end of the board was extended by 1 mm (now 19 × 10 mm), so a case has room around
U2. Suggestions S1 and S2 are applied. The production package
`pcbway_production/2026-10-14-10-22-05/` is verified against the board (see
[Fab package](#fab-package-verified)). U2's LCSC number is confirmed by the
designer. The one remaining item is a UIUCTag case.

## Critical Findings

| Severity | Issue | Section |
|---|---|---|
| WARNING | No UIUCTag case yet. The board is now 19 mm long and the BitPresTagBMP585 case does not fit; the 1 mm extension gives the new case room | [W1](#w1--case-room-at-the-far-end-board-extended-1-mm) |
| CLOSED | ~~No UIUCTag fab package; parent's package in `pcbway_production/`~~. UIUCTag package generated and verified; superseded exports pruned | [W2](#w2--fab-package-and-parent-files) |
| CLOSED | ~~U2 LCSC C59641 unconfirmed~~. Confirmed by the designer against the JLCPCB parts library | [W3](#w3--u2-lcsc-number-confirmed) |

## Previous Review Delta

The parent was closed out on 2026-09-04. This board has been compared both with
that run and with the *current* parent files.

| Change | Source | Status |
|---|---|---|
| U2 ADXL367 → ADXL362; C8 removed | UIUCTag | Reviewed below. All correct |
| U2, C1, C6, C7, C404 re-placed; Q501 and C502 moved B.Cu → F.Cu | UIUCTag | DRC and padnet clean. Causes W1 |
| INT1 → INT2 on PA0 | UIUCTag (designer, today) | Correct. Firmware contract I2 |
| Far edge extended 1 mm (18 → 19 mm); J303/J304 moved with it | UIUCTag (after this review) | DRC/parity clean; closes the case-room problem (W1) |
| S1 datasheet field + symlink; S2 pin types, GND PWR_FLAG, sym-lib-table | UIUCTag (after this review) | Done; ERC clean, nets unchanged |
| U302 MPN → STM32L432KCU6TR; nine 0.1 µF caps → GRM033R61A104ME15D | Parent commit `b6daea5` (2026-10-05), **after its review** | Never reviewed until now. Fine (I5) |
| ADXL367 VREG_OUT cap, +2V5 relabel, USART2/ADXL367 mapping | Parent findings | Closed: the part is gone or the fix is in place |
| Q501 resistor on the baseboard, AT25 CS pull-up, BMP585 gating, symbol hygiene | Parent findings | Carried forward unchanged |

The deep-review diff reports 10 "fixed" and 14 "new". Most of that is ID churn:
four parent findings were carried forward reworded, so they received new IDs.

## Component Summary

27 footprints: 12 capacitors, 2 resistors, 1 diode, 1 transistor, 5 ICs, and 6
J-items (J201 pogo pads, J301–J304 NPTH holes, J401 MS621 cell), all excluded from
the BOM. 45 nets, 14 no-connects. Every placed part has an MPN and an LCSC number
(U501 is C46471039 in the regenerated BOM).

## Power Tree

```
J401 MS621 cell ── VBAT (3.0–3.1 V fresh) ── D401 CDBQC0130L-HF Schottky (~0.06 V at 10 µA)
                                                  │
                                    VIN / VCC (unregulated, ~3.1 V → ~1.9 V EOL)
   bulk: C4 22 µF + C404 22 µF + C6 47 µF = 91 µF, plus 0.1 µF at each IC
     ├─ U302 STM32L432KC  (VDD, VDDA)       floor 1.71 V (BOR) ← binding
     ├─ U2   ADXL362      (VS, VDD I/O)     1.6–3.5 V          ← new, in range
     ├─ U1   AT25FF321A, U501 RV-3028
     └─ PB1 ─ R2 10 Ω ─ LPS_VDD ─ U3 BMP585 (power-gated, C3 + C5)
```

No regulators, so no Vref or feedback checks apply.

## Analyzer Verification

- **Component count:** 27 schematic = 27 PCB footprints.
- **Pin-to-net, all footprints:** `padnet_crosscheck.py`: 27 footprints, **0
  mismatches**. KiCad DRC schematic parity: 0 issues.
- **Netlist diff vs current BitPresTagBMP585:** only U2 and C8 differ. Every other
  pin-net is identical, so the parent's datasheet verification of Q501, U1, U3 and
  U501 carries over.
- **Analyzer trap avoided:** `analysis/` arrived as a byte-for-byte copy of the
  parent's, with its manifest naming `BitPresTagBMP585.kicad_pro`. It was cleared
  and re-run, and `project_settings.source` is now `UIUCTag.kicad_pro`.

### U2 ADXL362: datasheet-verified (ADI Rev. G)

| Pin | Datasheet Table 6 (p.7) | Net | MCU |
|---|---|---|---|
| 1 | VDD I/O | VIN | |
| 2, 15 | NC, not internally connected | open | |
| 3, 5, 10 | Reserved, "can be left unconnected" | open | |
| 4 | SCLK | ACCEL_SCK | PA4, USART2_CK, AF7 |
| 6 | MOSI | ACCEL_MOSI | PA2, USART2_TX, AF7 |
| 7 | MISO | ACCEL_MISO | PA3, USART2_RX, AF7 |
| 8 | CS (active low) | ACCEL_nCS | PA1, GPIO |
| 9 | INT2 / sync-sample input | WKUP1 | PA0, WKUP1 |
| 11 | INT1 / ext-clock input | open (unused) | |
| 12, 13, 16 | GND | GND | |
| 14 | VS | VIN | |

The footprint is pad-for-pad identical to BitTagv7's `bittag:ADXL362`: 0.798 ×
0.300 mm pads at the same positions. BitTagv7 is a fabricated, working ADXL362
board. Seen from the board top, the pads run clockwise from pin 1, which is
correct for a B.Cu part.

## Deep Review

The gate passed all 14 findings and quarantined 0. The full evidence is in
`analysis/deep_review.json`. The findings specific to this board:

- **I1 Decoupling meets the datasheet.** DS p.39 asks for "a 0.1 µF ceramic
  capacitor (CS) at VS and a 0.1 µF ceramic capacitor (CIO) at VDD I/O placed as
  close as possible". Here C7 is 0.10 mm from pin 1 (through the board) and C1 is
  1.13 mm from pin 14. C6 (47 µF) is 0.81 mm away and C404 (22 µF) 0.87 mm. That
  is closer than BitTagv7, whose nearest caps were 1.41 and 1.21 mm.
  *Datasheet + raw-file verified* (`u2_fit_check.py`).
- **I2 Interrupt pins double as inputs** (firmware contract). INT2 is also the
  synchronized-sampling input (FILTER_CTL bit 3 `EXT_SAMPLE`, DS p.35). INT1 is
  the external-clock input (`EXT_CLK`). Keep both bits at 0 so INT2 stays a
  push-pull output driving PA0, and the open INT1 doesn't become a floating input.
  Map activity through `INTMAP2` (0x2B), and match the WKUP1 polarity
  (`PWR_CR4.WP1`) to `INTMAP2.INT_LOW`.
- **I3 The USART2 synchronous-mode bus carries over unchanged.** The ADXL362 uses
  "CPHA = CPOL = 0" (p.21), fCLK 2.4 kHz to 8 MHz (Table 10), and the same
  0x0A/0x0B commands. The firmware driver must change: PARTID is 0xF2 (vs 0xF7),
  data is 12-bit, and the FIFO, filter and power registers differ. The ADXL367's
  "SCLK low selects I²C" caveat no longer applies.
- **I4 Supply range.** VS is 1.6–3.5 V and VDD I/O is 1.6 V to VS (p.4). VIN runs
  from 1.9 to 3.1 V, and VDD I/O = VS by construction. A connecting board feeding
  J201.1 must stay at or below 3.5 V.
- **I6 Rev. G power-cycle rule.** The supplies must fall to ≤ 100 mV for ≥ 200 ms
  before re-power (p.40). The 91 µF of VIN bulk holds charge after a cell is
  pulled, so wait several seconds before re-inserting a cell, and issue a soft
  reset (0x52 → 0x1F) at boot.
- **I5 Post-review parent MPN changes.** STM32L432KCU6**TR** is tape and reel of
  the same part. GRM033R61A104ME15D (0201, 100 nF, 10 V, X5R) runs at 31% of its
  rating at the 3.1 V maximum. Its DC-bias loss at 3 V is inference only and
  doesn't matter at ~10 µA.
- **Power budget.** Wake-up mode draws 270 nA on the ADXL362, against 180 nA on
  the ADXL367 (both from the datasheet front pages), so the budget rises by about
  +0.09 µA. Standby is 10 nA.

## Findings

### W1 — case room at the far end (board extended 1 mm)

**As first reviewed**, the 18 mm board put U2's body 0.93 mm from the far edge,
with C7/C404 on top directly under where a lid's far block bears. A case could
have had only a 0.08–0.73 mm far-end ledge and a split lid block.

**Resolved on the board, 2026-10-14.** The far (non-pogo) edge moved 1 mm
(Edge.Cuts x 140 → 139), and the J303/J304 harness holes moved with it. The pogo
end, J201, J401 and every component stayed put, so base mating is unchanged.
From `analysis/helpers/u2_fit_check.py` on the 19 mm board:

| | Parent case | UIUCTag, 18 mm | **UIUCTag, 19 mm** |
|---|---|---|---|
| U2 body to far edge | — | 0.93 mm | **1.93 mm** |
| Far-end base ledge (pocket from courtyard / body) | 1.59 mm | 0.08 / 0.73 mm | **1.08 / 1.73 mm** |
| Clear strip for the lid far block | 1.75 mm | ~0.7 mm, split | **1.68 mm** before C7 |

**Still to do:** make a UIUCTag case. The BitPresTagBMP585 case cannot be reused
on a 19 mm board. Follow `Mechanical/TAGCASE-PROCESS.md` using
`board_geometry.py` on the new outline (centre now KiCad x = 148.5). Keep the lid
far block within the 1.68 mm strip, then run `make check`.

### W2 — fab package and parent files

**Closed.** `pcbway_production/2026-10-14-10-22-05/` is the UIUCTag order package
and the only one kept (verified below). Pruned on 2026-10-14:

- `2026-09-04-19-26-51/`, the **parent's** package (`BitPresTagBMP585-*`, ADXL367,
  C8), which would have built the wrong board;
- `2026-10-14-10-18-41/`, the first UIUCTag export, made with the origin still at
  the old 18 mm corner;
- `BitPresTagBMP585-design-review.md` and `BitPresTagBMP585.kibot.yaml`, which were
  copied from the parent.

`archive/` (BitPresTagBMP581 files, inherited) and the empty `jlcpcb/` remain.

### W3 — U2 LCSC number confirmed

U2 is `ADXL362BCCZ-RL`, LCSC **C59641**. The community JLC parts mirror had no
entry for it, but the designer confirmed C59641 against the JLCPCB parts library
on 2026-10-14. Closed.

### Fab package (verified)

`pcbway_production/2026-10-14-10-22-05/` checked against `UIUCTag.kicad_pcb` by
geometry, not mtime:

- **Origin:** the drill/place origin is at the new lower-left corner (139, 113).
  The Edge.Cuts gerber spans (0, 0)–(19, 10). The first export had the origin at
  the old 18 mm corner, so its board spanned x = −1…18.
- **Copper:** all 580 F.Cu/B.Cu track endpoints, 35/35 vias, and all 2,856 In1/In2
  zone-fill vertices are present at the predicted gerber coordinates. The check
  was exhaustive, not sampled.
- **Layers and drills:** 11 gerber layers plus PTH and NPTH drill files. PTH:
  35 holes at 0.0079″ (0.2007 mm) = the board's 35 vias. NPTH: 4 holes at
  0.0433″ (1.0998 mm) = J301–J304. Inner planes measure 18.399 × 9.399 mm, which
  is the 0.3 mm edge clearance on the 19 × 10 mm outline.
- **BOM and CPL:** 21 designators in each, identical sets. Every CPL position
  equals the board footprint position relative to the origin, and every CPL entry
  is exactly +1.000 mm in x from the first export, with y, rotation and side
  unchanged. U2 is ADXL362BCCZ-RL / C59641, C8 is absent, and J201, J301–J304 and
  J401 are correctly excluded.
- **Gerber analyzer:** layer set complete. GR-002 "width varies by 4.2 mm" is the
  known false positive: the outer layers carry no pours, so their extents are
  just the part extents.
- **After the origin change:** KiCad DRC is 0 violations / 0 unconnected / 0
  parity, and ERC is 0.

### Suggestions — applied 2026-10-14

- **S1 (done)** U2's Datasheet field now reads `${KIPRJMOD}/datasheets/adxl362.pdf`
  in the schematic, the PCB footprint and the shared `tag_library` symbol (it was
  a non-existent `…/hardware/hardware/…` file URL). `datasheets/` is back to the
  house symlink `../../libraries/datasheets`; the copy was file-for-file identical.
- **S2 (done)** Pin types fixed:
  - U501, in the board-local `BitTagNG.kicad_sym` and the embedded copy: CLKOUT →
    output, INT → open_collector, SDA → bidirectional, GND and VDD → power_in.
  - adxl362, in `tag_library` and the embedded copy: NC → no_connect, RES →
    passive.
  - U501's mistyped GND had been the GND net's only power output. Correcting it
    surfaced `power_pin_not_driven`, so a `PWR_FLAG` (#FLG0103) now sits on GND,
    as VIN and VBAT already had.
  - The unused adxl367/lis2dw12/lis2du12 entries are gone from `sym-lib-table`.
  - **Correction:** the "no Device library" item was wrong. KiCad 10's global
    table includes the stock libraries, so Device, power, Connector_Generic and
    Mechanical resolve without a project entry.
  - ERC is 0 violations, and the netlist is unchanged outside U2.
- **S3 (moot)** The panel-edge stress concern for U2 lapses: its body is now
  1.93 mm from the edge.

## STM32L432KC pin map

| Pin | Port | Net | Connects to | Function (AF) |
|---|---|---|---|---|
| 1, 17 | VDD | VIN | rail | supply |
| 2 | PC14 | clkout | U501.1 CLKOUT | RCC_OSC32_IN, LSE bypass (additional function) |
| 3 | PC15 | — | — | unused: analog/no-pull |
| 4 | NRST | — | C502, Q501.3 | reset (Q501 inverter, base R on baseboard) |
| 5 | VDDA | VIN | rail | analog supply |
| 6 | PA0 | WKUP1 | **U2.9 INT2** | wake input |
| 7 | PA1 | ACCEL_nCS | U2.8 | GPIO CS |
| 8 | PA2 | ACCEL_MOSI | U2.6 | USART2_TX (AF7), sync mode |
| 9 | PA3 | ACCEL_MISO | U2.7 | USART2_RX (AF7) |
| 10 | PA4 | ACCEL_SCK | U2.4 | USART2_CK (AF7) |
| 11 | PA5 | LPS_SCK | U3.1 | SPI1_SCK (AF5) |
| 12 | PA6 | lps_rdy | U3.5 INT | GPIO input, no pull |
| 13 | PA7 | — | — | unused: analog/no-pull |
| 14 | PB0 | LPS_CS | U3.7 | GPIO CS |
| 15 | PB1 | LPS_PWR | R2 → U3 supply | GPIO power gate, lowest slew |
| 16, 32, 33 | VSS / EP | GND | rail | ground |
| 18–20 | PA8–PA10 | — | — | unused: analog/no-pull |
| 21 | PA11 | LPS_MISO | U3.3 | SPI1_MISO (AF5) |
| 22 | PA12 | LPS_MOSI | U3.2 | SPI1_MOSI (AF5) |
| 23 | PA13 | SWDIO | J201.3 | SWDIO (AF0) |
| 24 | PA14 | SWCLK | J201.4 | SWCLK (AF0) |
| 25 | PA15 | AT25_nCS | U1.B4 | GPIO CS, internal pull-up |
| 26 | PB3 | AT25_SCK | U1.F2 | SPI3_SCK (AF6), loses TRACESWO |
| 27 | PB4 | AT25_MISO | U1.D4 | SPI3_MISO (AF6), loses NJTRST |
| 28 | PB5 | AT25_MOSI | U1.E3 | SPI3_MOSI (AF6) |
| 29 | PB6 | SCL | U501.3 | bit-banged I²C, internal pull-up |
| 30 | PB7 | SDA | U501.4 | bit-banged I²C, internal pull-up |
| 31 | BOOT0 | GND | — | hard low |

`stm32_pinmap.py` checked pin numbering against ST's data (25 GPIOs, all match).
Its three "SPI1 collisions" (LPS vs AT25) are resolved by putting the flash on
SPI3 (AF6), as on the parent. The "BOOT0 pulled via R1" note is the known
artefact: BOOT0 is tied to GND directly. The ACCEL bus is on USART2, not SPI, so
the three buses never contend. This table is mirrored in
`.kicad-happy.json → mating_design.host_pin_map`.

## PCB Layout

- **Board:** 19.0 × 10.0 × 0.4 mm, 4 layers: In1 is a solid VIN plane (118.2 mm²)
  and In2 a solid GND plane (127.3 mm²), each one fill region. 19 parts on the top side and 8 on the
  bottom, 35 vias, routing complete.
- **Rules:** identical to the parent's `.kicad_pro`. Edge clearance 0.3 mm,
  annular ring 0.1524 mm, vias 0.5048/0.2 mm, track/space 0.1016 mm (advanced
  process).
- **KiCad DRC:** 0 violations, 0 unconnected, 0 parity. This holds both on the
  saved zone fill and with `--refill-zones`, so the saved fill is current. **ERC:**
  0 violations.
- **U302 exposed pad:** 2 vias. That is electrically adequate, and the
  dissipation is microwatts (TV-001 is suppressed in the config).
- **Thermal analyzer** (38 °C ambient): 0 findings. There are no power-dissipating
  parts.

## EMC / Cross-Domain

EMC reported 54 findings and cross-analysis 10. Every warning and error falls
under an existing config suppression with a recorded reason: GP-001, GP-004,
PS-002, RP-001/002, CK-001/003. The plane-split findings were re-checked for this
layout rather than assumed. Both inner zones are single regions, and KiCad reports
0 unconnected, so "GND split into 6 islands" is the known union-find false
positive. CK-003 cites the J30x mounting holes and J401.

## False Positives / Reviewer Overrides

| Finding | Disposition |
|---|---|
| PM-002 "U2 0.28 mm / C7 0.93 mm from board edge" (18 mm board) | Courtyard, not copper. Gone after the 1 mm extension; no suppression needed |
| PU-001 "U2 INT1 missing pull-up" | INT1 is an unused push-pull output. Suppression re-keyed from the 367's INT2 to INT1 |
| PS-002 / RP-002 / GP-001 plane splits | Single-region planes and DRC 0 unconnected. House false positive |
| FD-001, TE-001, CC-002, DFM-001, TV-001, PP-001, PR-002, RS-001 | House conventions, already suppressed with reasons |
| X/Y axes inverted vs parent and BitTagv7 | Irrelevant: activity detection only (designer) |

## Not Performed / Review Limits

- **SPICE:** not run. No simulator (ngspice/LTspice/Xyce) is installed, and the
  only analog subcircuit is the R2/C3/C5 gate ramp, already computed on the parent.
- **Gerber analysis:** run on `2026-10-14-10-22-05` and its predecessor; see
  [Fab package](#fab-package-verified).
- **Lifecycle audit:** not run. No distributor API credentials are configured. The
  one LCSC lookup was a manual query of a community mirror; C59641 was then
  confirmed by the designer (W3).
- **Datasheet extraction cache:** none. Pin-level checks were made against the
  manufacturer PDFs directly. The GRM033R61A104ME15D DC-bias figure is inference
  only.
- **Parts unchanged from the parent** (Q501, U1, U3, U501, D401) were verified on
  2026-09-04 and confirmed unchanged by netlist diff, not re-read today.

## Positive Findings

1. The ADXL362 reuses a land pattern already proven on BitTagv7.
2. Its decoupling is tighter than on the reference board: 0.10 mm and 1.13 mm.
3. The swap changed only the accelerometer's pins. The MCU pin map and bus
   allocation are untouched, so the parent's verified firmware contracts still hold.
4. The re-placement was done cleanly. Q501/C502 survived the side flip with 0 pad
   mismatches, and DRC, ERC and parity are all clean on the first pass.
