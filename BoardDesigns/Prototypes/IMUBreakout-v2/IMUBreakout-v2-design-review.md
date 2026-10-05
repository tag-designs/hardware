# IMUBreakout-v2 Design Review

**Project:** IMUBreakout-v2, KiCad 10.0 project, single-sheet schematic, 4-layer PCB  
**Date:** 2026-06-15  
**Review data:** `analysis/2026-06-15_1048`  
**Analyzers run:** `analyze_schematic.py`, `analyze_pcb.py --full`, `cross_analysis.py`, `analyze_gerbers.py`, EMC analyzer, `analyze_thermal.py`, lifecycle audit, KiCad ERC, KiCad DRC  
**SPICE:** not run; `ngspice`, `ltspice`, and `xyce` were not installed.

## Overview

IMUBreakout-v2 is a 1.8 V sensor breakout with a Macronix 128 Mbit SPI flash (U2), AK09940A magnetometer (U3), LSM6DSV16X IMU (U4), and LPS22HH pressure sensor (U5). J3/J4 expose the host interface and power rail through two 17-pin staggered headers. The PCB is 48.26 mm x 48.26 mm, 4 copper layers, with In1 used as +1V8 pour and In2 used as GND pour.

## Verdict

**Closer, with only a small schematic cleanup plus optional EMC/layout polish remaining.** KiCad DRC is clean and the schematic-to-PCB connectivity is internally consistent. Your latest layout pass increased total vias from 44 to 64 and GND stitching from 19 to 35, which improved the return-path situation. KiCad ERC still reports the same two C1 wire stubs.

| Severity | Issue | Evidence |
|---|---|---|
| WARNING | A smaller set of signal vias still lack nearby GND stitching vias, and some fast/control lines change F/B layers | EMC RP-001, PCB layer-transition data |
| WARNING | KiCad ERC has two unconnected wire endpoints on the C1 local decoupling wiring | KiCad ERC report |
| SUGGESTION | LPS22HH symbol carries an LPS22DF datasheet URL, and U4 MPN is shortened to `LSM6DSV` instead of the orderable `LSM6DSV16XTR` | Raw schematic properties |

The analyzer's I2C pull-up errors on `LSM_CK`/`LSM_MOSI` are treated as false positives if this board is intentionally SPI-only. Both LPS22HH and LSM6DSV16X datasheets show those pins are SPI/I2C multiplexed and SPI mode is selected by CS low. No external I2C pull-ups are required for SPI operation.

## User / Firmware Configuration Notes

- The host must provide a clean `+1V8` rail on J3 pin 7 and/or J4 pin 1. The schematic has no onboard regulator and no PWR_FLAG on `+1V8`.
- The host owns all chip-select and bus timing. Analyzer "no driver" warnings on `MX_SCK`, `MX_nCS`, `MX_MOSI`, `AK_CS`, `LSM_CS`, and `LPS_CS` are expected for a breakout.
- Keep inactive SPI chip-selects high at reset/sleep. `U2 ~RESET` and `~WP` are tied to `+1V8`; the Macronix flash datasheet states these pins have internal pull-ups only when not physically connected, so here the explicit rail tie is the controlling state.
- J3/J4 are intentionally not populated in assembly, but their PTH pads/holes should remain in the Gerbers. The current files match that intent: J3/J4 are DNP/not-in-BOM, absent from BOM/CPL, and present in the Gerber copper/mask/drill data.
- For SPI mode, drive `LSM_CS`, `LPS_CS`, and `AK_CS` intentionally. Do not rely on the analyzer's I2C interpretation of `SCL/SDA`-named pins.

## Component Summary

| Type | Count |
|---|---:|
| ICs | 4 |
| Capacitors | 9 |
| Connectors | 2 |
| Total schematic components | 15 |
| PCB footprints | 15 |

MPN coverage is complete for assembled BOM parts. J3/J4 intentionally have no MPN and are marked DNP/not-in-BOM. Production BOM/CPL includes C1/C2/C3/C4/C6/C7/C8/C9/C10 and U2/U3/U4/U5 only.

## Power Tree

```text
1V8 from host connector
  -> U2 MX25U12843GBBI00 VCC, RESET, WP
  -> U3 AK09940A VDD, VOD, RSTN
  -> U4 LSM6DSV16XTR VDD, VDD_IO
  -> U5 LPS22HH VDD, Vdd_IO
  -> 7 x 0.1 uF local bypass + 2 x 4.7 uF bulk/local caps
```

Analyzer-estimated load is about 35 mA on `+1V8`; this is heuristic and likely high for typical sensor duty cycles. Routing uses 0.1524 mm traces plus +1V8/GND pours; this is adequate for low tens of milliamps.

## Analyzer Verification

- Component count matches: 15 schematic components and 15 PCB footprints.
- KiCad DRC: 0 violations, 0 unconnected pads, 0 footprint errors.
- KiCad ERC: 2 warnings, both unconnected wire endpoints in schematic-sheet coordinates near C1. These are schematic coordinates, not PCB-layout coordinates. Reference point: C1 is centered at `(29.21,133.35)` mm and `#PWR019 +1V8` is above it at `(29.21,125.73)` mm. The dangling stubs are the short left-facing C1 wires ending at `(22.86,129.54)` and `(22.86,137.16)` mm.
- Gerbers: complete layer set with top/bottom copper, In1/In2 copper, mask, paste, silk, Edge.Cuts, PTH and NPTH drill files. Drill file has 64 vias and 34 plated component holes.
- Datasheets: the project-local `datasheets` link points to the shared library at `../libraries/datasheets` (`BoardDesigns/libraries/datasheets` from this workspace). That library contains the MX25U12843G PDF. ST datasheets were checked online for LPS22HH and LSM6DSV16X. I did not find a local or online AK09940A datasheet during this run, so AK09940A pin correctness remains consistency-only.

## IC Pinout Checks

| Ref | Part | Status | Notes |
|---|---|---|---|
| U2 | MX25U12843GBBI00 | Datasheet-checked | WLCSP pins match local Macronix datasheet page 6: A2 VCC, A3 CS#, B2 RESET#/SIO3, B3 SO/SIO1, C2 SCLK, C3 WP#/SIO2, D2 SI/SIO0, D3 GND. |
| U3 | AK09940A | Consistency-only | Schematic and PCB pad nets match. No AK09940A manufacturer datasheet was available in the checked datasheet sources. |
| U4 | LSM6DSV16XTR | Datasheet-checked for major pins | ST datasheet Table 2 matches VDD/VDD_IO/GND, CS, SCL, SDA, INT1/INT2, and permits OCS_Aux/SDO_Aux unconnected in relevant modes. |
| U5 | LPS22HH | Datasheet-checked | ST datasheet Table 2 matches pins 1-10. Pin 3 is reserved and tied to GND as required. |

## Connector Pin Tables

### J3

| Pin | Net | Function |
|---:|---|---|
| 1 | MX_MISO | Flash MISO |
| 2 | MX_MOSI | Flash MOSI |
| 3 | NC | Unused |
| 4 | NC | Unused |
| 5 | GND | Ground |
| 6 | GND | Ground |
| 7 | +1V8 | Power input |
| 8 | WKUP1 | U4 INT1 |
| 9 | NC | Unused |
| 10 | AK_TRG | U3 DRDY/TRG |
| 11 | AK_CS | U3 chip select |
| 12 | NC | Unused |
| 13 | LSM_CK | Shared clock |
| 14 | LSM_MISO | U4 MISO/SDO |
| 15 | LSM_MOSI | U3/U4 MOSI |
| 16 | LSM_CS | U4 chip select |
| 17 | GND | Ground |

### J4

| Pin | Net | Function |
|---:|---|---|
| 1 | +1V8 | Power input |
| 2 | MX_SCK | Flash clock |
| 3 | MX_nCS | Flash chip select |
| 4 | LPS_MOSI | U5 MOSI/SDA |
| 5 | LPS_MISO | U5 MISO/SA0 and U3 SO |
| 6 | LPS_CS | U5 chip select |
| 7 | LPS_DRDY | U5 interrupt/data-ready |
| 8 | LSM_TRG | U4 INT2 |
| 9-15 | GND | Ground pins |
| 16 | NC | Unused |
| 17 | GND | Ground |

## Signal Analysis

- The `PR-001` I2C pull-up findings on `LSM_CK`/`LSM_MOSI` are false positives for SPI mode. LPS22HH and LSM6DSV16X both multiplex SPI and I2C onto these pins; CS low selects SPI.
- Interrupt/pulse nets `WKUP1`, `LSM_TRG`, and `LPS_DRDY` have no external pulls. This can be fine if the host configures internal pulls or the sensor outputs are actively driven, but it is a firmware contract worth documenting.
- U5 `SA0` is connected to `LPS_MISO`; in SPI this is SDO, so the net name is reasonable. In I2C it would be an address strap and would need a defined high/low state.
- AK09940A uses `LSM_CK` and `LSM_MOSI` plus `LPS_MISO`, with `AK_CS` on J3. The mixed net prefixes are electrically OK but easy to miswire in host firmware; consider documenting this as an "AK bus uses LSM clock/MOSI and LPS_MISO" note.

## PCB Layout

- Board dimensions: 48.26 mm x 48.26 mm.
- Stackup: F.Cu, 0.1 mm prepreg, In1.Cu, 1.24 mm core, In2.Cu, 0.1 mm prepreg, B.Cu. Copper thickness is 0.035 mm on all copper layers.
- Zones are filled. GND is one connected island in the PCB connectivity graph. +1V8 has a single In1 filled region in zone data, and KiCad DRC reports no unconnected pads.
- The latest PCB has 64 vias, up from 44 in the first review pass. Analyzer-reported GND stitching increased to 35 vias, up from 19.
- All routing is complete.
- Minimum trace width is 0.1524 mm, minimum drill is 0.2997 mm, minimum annular ring is 0.155 mm. The analyzer classifies DFM as standard tier with no DFM violations.

## EMC / Return Path

The EMC analyzer reported a high risk score due mostly to reference-plane and return-path checks. After triage:

- **Keep:** Missing ground stitching vias remain near F/B transitions on `AK_CS`, `AK_TRG`, `LPS_CS`, `LSM_MOSI`, and `WKUP1` at warning level. `LSM_CK`, `LPS_DRDY`, and `LPS_MOSI` are now info-level EMC findings rather than warning-level findings. Add GND stitching vias within about 1 mm of remaining signal vias where space allows, especially chip-selects and wake/interrupt lines.
- **Keep:** `MX_SCK` is routed on outer layers and passes within 2.1 mm of J4. If this flash clock runs fast, route it with a tighter return path or add nearby ground guard/stitching.
- **Downgrade:** EMC `SU-001` "adjacent signal layers" is an analyzer false positive. The raw stackup lists layers as KiCad signal layers, but In1/In2 are used as +1V8/GND copper pours.
- **Downgrade:** Cross-analysis `+1V8 plane split: 7 islands` conflicts with KiCad DRC and raw zone data. Treat as analyzer false positive unless KiCad zone refill later shows an actual split.
- **Context:** J3 has 3 GND pins for 13 signal pins by schematic audit, while J4 has many more GND pins. For a short board-to-board connection this may be acceptable; for cable-like use, add grounds or reduce edge-coupled clocks.

## Manufacturing / Assembly

- **Fiducials:** PCB analyzer FD-001 flagged no local fiducials, but this is acceptable for the current flow because the fabricator will add fiducials. Keep this as an assembly-process note, not a board-design blocker.
- **J3/J4 placement:** Both headers are 0.74 mm from board edge. This is below the analyzer's 1.0 mm recommendation; acceptable only if the mechanical design intentionally places the staggered headers at the edge and the fab/assembly process allows it.
- **Paste warning triage:** Gerber analyzer warned that F.Paste has 69 flashes vs 167 F.Cu flashes. This appears benign: F.Cu includes 69 SMD pads, 34 through-hole header pads, and 64 via pads; F.Paste includes the 69 SMD pads only.
- **Production package:** BOM/CPL include only the top-side assembled SMD parts, not J3/J4. That matches the intentional schematic DNP status for headers. Gerbers still include the J3/J4 through-hole copper, mask openings, and plated drill holes.

## Thermal

Thermal analyzer found 0 findings and 0 modeled heat sources. For this low-power sensor breakout, no thermal blocker was found. The thermal model did not estimate detailed junction temperatures because no power-dissipating regulators or drivers are present.

## Lifecycle / Sourcing

Lifecycle audit ran against 6 unique MPNs, but no distributor/status sources were available to the script, so all parts came back `unknown`. Treat this as no lifecycle coverage rather than an all-clear.

Order/package cleanup before release:

- Set U4 MPN to the full orderable part, likely `LSM6DSV16XTR`, instead of `LSM6DSV`.
- Replace U5's `Datasheet` property URL. It currently points at `lps22df.pdf`, while the MPN/value are `LPS22HH`.
- No connector MPN action is needed for J3/J4 in the intended DNP/user-header flow.

## False Positives / Reviewer Overrides

- I2C missing pull-ups on `LSM_CK`/`LSM_MOSI`: false positive for SPI operation.
- LSM6DSV16X pins 10 and 11 unconnected: acceptable per ST Table 2 for modes where auxiliary interface is unused.
- EMC stackup `SU-001`: downgraded because In1/In2 are not routed signal layers in practice.
- Cross-analysis +1V8 disconnected/split: downgraded because KiCad DRC is clean and In1 +1V8 zone has one filled region.
- Gerber paste `GR-004`: downgraded because paste count matches SMD pad count.

## Not Performed / Review Limits

- No SPICE simulation was run because no supported simulator is installed.
- AK09940A pinout was not datasheet-verified; schematic and PCB are internally consistent only.
- Lifecycle status was attempted but produced unknown results for all parts due lack of available lookup sources.
- No full visual PCB inspection in KiCad GUI was performed; this review used raw files, KiCad CLI reports, Gerber files, and analyzer JSON.

## Recommended Pre-Fab Actions

1. Clean the two KiCad ERC unconnected wire endpoints on the C1 wiring stubs.
2. Add any remaining GND stitching vias near F/B signal transitions if you want to further reduce EMC risk, prioritizing `AK_CS`, `AK_TRG`, `LPS_CS`, `LSM_MOSI`, and `WKUP1`.
3. Keep J3/J4 DNP/not-in-BOM for assembly while preserving their footprints in fabrication outputs.
4. Correct U5 datasheet property and U4 MPN property.
5. Add a short host firmware note for SPI mode, inactive CS states, interrupt pin pulls, and the AK09940A mixed-prefix bus routing.

## Sources

- Local analyzer outputs in `analysis/2026-06-15_1048`.
- KiCad ERC/DRC reports in `analysis/2026-06-15_1048/kicad-erc.rpt` and `analysis/2026-06-15_1048/kicad-drc.rpt`.
- Local shared datasheet library: `../libraries/datasheets` from the KiCad project, symlinked as `./datasheets` and located at `BoardDesigns/libraries/datasheets` in this workspace.
- Local Macronix MX25U12843G datasheet: `../libraries/datasheets/MX25U12843G18V128Mbv11.pdf`.
- ST LPS22HH datasheet: https://www.st.com/resource/en/datasheet/lps22hh.pdf
- ST LSM6DSV16X datasheet: https://www.st.com/resource/en/datasheet/lsm6dsv16x.pdf
