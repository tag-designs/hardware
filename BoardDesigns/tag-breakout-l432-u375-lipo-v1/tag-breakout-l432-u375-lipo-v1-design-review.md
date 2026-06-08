# tag-breakout-l432-u375-lipo-v1 Design Review

**Date:** 2026-06-08  
**Project:** `BoardDesigns/tag-breakout-l432-u375-lipo-v1`  
**Analysis run:** `analysis/2026-06-08_1720`  
**Analyzers run:** schematic, PCB `--full`, cross-analysis, EMC, thermal, KiCad PCB DRC  
**Skipped:** SPICE, because no simulator was installed; lifecycle audit, because no distributor/API audit was run; Gerber analysis, because `jlcpcb/gerber` has no Gerber/drill files.

## Verdict

Much improved after the cleanup passes. KiCad DRC is clean, schematic/PCB synchronization is internally consistent, BOOT0/USB/fiducial/decoupling warnings are no longer reported, and U7 direction is confirmed OK. The remaining pre-fab concerns are mostly layout-level: J104 mechanical edge clearance and return-path support for clock/SWD-style nets.

## Reanalysis Delta

Compared with the prior `analysis/2026-06-08_1615` pass, the current `analysis/2026-06-08_1720` pass changed as follows:

| Analyzer | Previous | Current | Notes |
|---|---:|---:|---|
| Schematic | 52 findings: 1 error, 17 warnings, 34 info | 37 findings: 1 error, 3 warnings, 33 info | Most unused-MCU single-pin warnings are gone. Remaining error is the known TAG_3V3 source false positive through U2. |
| PCB full | 46 findings: 1 error, 3 warnings, 42 info | 46 findings: 1 error, 3 warnings, 42 info | No layout/DFM count change. J104 edge clearance remains. |
| Cross-analysis | 1 info | 1 info | Still only sparse via stitching info. |
| EMC | 40 findings: 3 errors, 33 warnings, 4 info, score 52 | 37 findings: 3 errors, 29 warnings, 5 info, score 52 | Same three error classes remain, but warning count dropped and one `TAG_SCK` transition now has nearby GND stitching. |
| Thermal | 1 info, score 100 | 1 info, score 100 | Still clean; hottest estimate is U10 at 29.5 C. |
| KiCad DRC | 0 violations, 0 unconnected | 0 violations, 0 unconnected | Clean. |

## Blocking / High-Priority Findings

| Severity | Finding | Evidence |
|---|---|---|
| Error | J104 is reported `-0.32 mm` from the board edge. This may be intentional for an edge-mounted USB connector, but verify against the connector drawing and assembler courtyard rules. | PCB analyzer `PM-002`; KiCad DRC itself reports 0 violations. |
| Error | `/SCLK` has partial reference-plane coverage: 90% coverage over 11.1 mm of routing. | EMC `GP-001`, heuristic. |
| Error | `/stm32/clkout` and `TAG_SCK` layer transitions do not have GND stitching vias within 1.0 mm. | EMC `RP-001`, deterministic topology. |
| Warning | Several other layer-transition nets lack nearby stitching vias, including `TAG_1V8`, `/NRST`, `/UART_TX`, `/stm32/NRST`, `/stm32/rtc_scl`, and two local unnamed nets. | EMC `RP-001`. |
| Warning | Test-point coverage is still 0/81 signal nets. Headers may be enough for bring-up, but there are no dedicated ICT/flying-probe pads. | PCB analyzer `TE-001`. |

## Datasheet / Raw-File Checks

The datasheet symlink now resolves to `../libraries/datasheets`, and the schematic datasheet coverage warning is gone. `pdftotext` was used for local checks of TPS7A02, SiP32432, SN74LVC1T45, AP2112, XC6206, STM32U375, and PMBT2222AMB.

Key confirmations:

| Ref | Check | Status |
|---|---|---|
| U11 TPS7A0218 | Pin map matches schematic: OUT/TAG_1V8, GND, EN/TAG_3V3, IN/TAG_3V3, thermal pad/GND. Datasheet requires >=0.5 uF effective output capacitance and recommends 1 uF close to OUT. | OK electrically; layout cap distance should be checked. |
| U2 SiP32432 | Datasheet identifies IN, OUT, GND, ON/OFF; schematic uses IN on +3V3, OUT on TAG_3V3, ON/OFF from PWR_IN_MIRROR. Analyzer rail-source error on TAG_3V3 is a symbol typing limitation because U2 OUT is marked passive. | False positive, but consider changing the symbol pin type. |
| U7 SN74LVC1T45 | VCCA=+3V3, VCCB=+1V8, DIR=+3V3. Datasheet says DIR high drives A to B, so U7 is fixed 3.3 V to 1.8 V. | Confirmed OK. |
| U8 SN74LVC1T45 | VCCA=+3V3, VCCB=+1V8, DIR is MCU-controlled. | Firmware must set DIR before active traffic and avoid bus contention. |
| U1 XC6206 | SOT-23 pinout is VSS/VIN/VOUT, matching GND/VUSB/+3V3 in the schematic. Datasheet calls for close input/output capacitors. | OK; cap placement should remain close. |
| U10 AP2112K-1.8 | SOT25 pinout is VIN/GND/EN/NC/VOUT, matching +3V3/GND/en1.8v/NC/+1V8. | OK. |
| Q1 | Schematic assumes B/E/C = pins 1/2/3. PMBT2222AMB datasheet is present and appears compatible, but Q1 has no MPN in the schematic. | Add Q1 MPN if PMBT2222AMB is intended. |

## Firmware / Bring-Up Notes

- U5 PA1 drives `en1.8v`, which enables U10 and the local `+1V8` rail.
- U8 direction is firmware-controlled; define reset/sleep state for that GPIO so the TAG SWDIO path does not fight the external target.
- U5 has many intentionally unused GPIO nets reported as single-pin. Add no-connect markers or route them intentionally if they are planned test points.

## Layout / Manufacturing

- KiCad PCB DRC: 0 violations, 0 unconnected items.
- PCB stats: 53.34 mm x 73.66 mm, 2 copper layers, 53 footprints, 47 SMD, 6 THT, 86 vias, fully routed.
- DFM summary: standard tier, no analyzer DFM metric violations.
- U3/U5 exposed pads have fewer thermal/ground vias than the analyzer recommends: U3 has 1/9, U5 has 2/9. Thermal analysis is fine for expected power, but tenting/voiding and ground impedance are still worth reviewing before assembly.
- J104 being reported `-0.32 mm` from the board edge is likely an edge-mounted USB connector artifact. Verify the connector courtyard/board edge against the mechanical drawing rather than treating this as automatically wrong.

## EMC / Signal Integrity

The EMC analyzer reports high layout risk, mostly from two-layer return-path geometry and connector-adjacent clocks. The most useful fixes are small:

- Add ground stitching vias near layer transitions on `TAG_SCK`, `/stm32/clkout`, SWD, UART, and NRST.
- Review `/SCLK` over its 11.1 mm routed segment and either improve the reference plane continuity or decide that the short length and product environment make the residual risk acceptable.
- Keep `/SCLK` and `TAG_SCK` away from headers where possible, or add grounded guard/stitching nearby.

## Sourcing / Datasheets

Schematic MPN coverage is 20/21 unique BOM lines; Q1 is the missing MPN. Remaining local datasheet housekeeping is mostly metadata/naming:

- Local PDF coverage exists for the major ICs and several passives.
- KiCad `Datasheet` fields are still only filled for 5/21 BOM lines, so analyzer trust remains `mixed` even though the folder now contains more PDFs.
- Add/normalize datasheet fields for AP2112, TPS7A02, SiP32432, SN74LVC1T45, STM32U375, STM32L432, RV-3028, and Q1 once Q1 is assigned.

## False Positives / Overrides

- `PP-001` on U11/TAG_3V3 is likely false positive: raw schematic shows TAG_3V3 sourced through U2 OUT, but U2 OUT is typed passive.
- `RS-001` rail-source warnings on external/mirrored rails are expected for connector-sourced rails; add PWR_FLAGs if you want ERC/analyzer quiet.
- `PM-002` J104 edge-clearance warning is likely expected for an edge USB connector, pending mechanical confirmation.
- `TE-001` no test points is softened because the board is a breakout with large headers, but dedicated ICT/flying-probe pads are still absent.

## Not Performed / Limits

- No SPICE simulation was run because `ngspice`, `ltspice`, and `xyce` were not installed when checked.
- No lifecycle audit was run.
- No Gerber analysis was run because fabrication outputs were not present.
- Datasheet checks were targeted, not an exhaustive page-by-page verification of every passive and connector.
