# tag-breakout-l432-u375-lipo-v1 Design Review

**Date:** 2026-06-09  
**Project:** `BoardDesigns/tag-breakout-l432-u375-lipo-v1`  
**Analysis run:** `analysis/2026-06-09_1450`  
**Analyzers run:** schematic, PCB `--full`, Gerber/drill, cross-analysis, EMC, thermal, KiCad PCB DRC  
**Skipped:** SPICE, because no simulator was installed; lifecycle audit, because no distributor/API audit was run.

## Verdict

The design is a four-layer PCB on disk (`F.Cu`, `In1.Cu`, `In2.Cu`, `B.Cu`). KiCad DRC is clean, Gerber/drill analysis is clean, routing is complete, thermal remains clean, and U7/Q1/BOOT0/USB/decoupling concerns are closed. The added stitching vias did not change the sampled connector-local reference misses: `/SCLK` and `/SWDIO` still each miss 1 of 7 sample points, and `/UART_TX` still misses 1 of 18. Cross-analysis now reports both `+3V3` and `GND` as graph-split nets in that same connector/fanout cluster, but the actual In2 `+3V3` zone remains one filled region and the main In1 GND plane remains one filled region. Treat this as connector antipad/fanout return-path hygiene, not a board-level plane split.

## Reanalysis Delta

Compared with the prior `analysis/2026-06-09_1437` pass, the current `analysis/2026-06-09_1450` pass changed as follows:

| Analyzer | Previous | Current | Notes |
|---|---:|---:|---|
| Schematic | 36 findings: 1 error, 3 warnings, 32 info | 36 findings: 1 error, 3 warnings, 32 info | Unchanged; remaining error is the known TAG_3V3 source false positive through U2. |
| PCB full | 46 findings: 2 errors, 3 warnings, 41 info | 46 findings: 2 errors, 3 warnings, 41 info | Actionable PCB findings are unchanged. Via count changed from 95 to 86. |
| Gerber/drill | 0 findings | 0 findings | Still clean; regenerated Gerbers include `CuIn1` and `CuIn2`, with 139 total holes. |
| Cross-analysis | 3 findings: 2 errors, 1 info | 4 findings: 3 errors, 1 info | Added `GND` connectivity-graph split item. The connector-local crossing list is still `/SWDIO`, `/SCLK`, and `/UART_TX`. |
| EMC | 38 findings: 1 error, 30 warnings, 7 info, score 64.0 | 38 findings: 1 error, 29 warnings, 8 info, score 64.0 | Score unchanged. Remaining EMC error is still `/SCLK` reference gap; the sampled coverage for `/SCLK`, `/SWDIO`, and `/UART_TX` is unchanged. |
| Thermal | 1 info, score 100 | 1 info, score 100 | Still clean; hottest estimate is U10 at 29.5 C. |
| KiCad DRC | 0 violations, 0 unconnected | 0 violations, 0 unconnected | Clean. |

## Blocking / High-Priority Findings

| Severity | Finding | Evidence |
|---|---|---|
| Review | Cross-analysis reports `+3V3` as 11 connectivity-graph islands and `GND` as 3 connectivity-graph islands, with `/SWDIO`, `/SCLK`, plus `/UART_TX` overlapping the analyzer's gap boxes. However, the actual In2 `+3V3` zone and In1 GND plane each report one fill region, and visual inspection places the coordinates at connector/fanout geometry. | Cross-analysis `PS-002`, `RP-002`; PCB zone data; visual inspection near connector. |
| Error | J104 is reported `-0.32 mm` from the board edge. This may be intentional for an edge-mounted USB connector, but verify against the connector drawing and assembler courtyard rules. | PCB analyzer `PM-002`; KiCad DRC itself reports 0 violations. |
| Error | `/SCLK` has partial reference-plane coverage: 86% coverage over 11.1 mm. | EMC `GP-001`, heuristic. |
| Warning | Several other layer-transition nets lack nearby stitching vias, including `TAG_1V8`, `/stm32/NRST`, `/stm32/PA15`, `Net-(U5-PA15)`, `/NRST`, and `Net-(U5-PB3)`. | EMC `RP-001`. |
| Warning | Test-point coverage is 2/82 signal nets. Headers may be enough for bring-up, but dedicated ICT/flying-probe coverage is still sparse. | PCB analyzer `TE-001`. |

## Datasheet / Raw-File Checks

The datasheet symlink now resolves to `../libraries/datasheets`, and the schematic datasheet coverage warning is gone. `pdftotext` was used for local checks of TPS7A02, SiP32432, SN74LVC1T45, AP2112, XC6206, STM32U375, and BCX70H.

Key confirmations:

| Ref | Check | Status |
|---|---|---|
| U11 TPS7A0218 | Pin map matches schematic: OUT/TAG_1V8, GND, EN/TAG_3V3, IN/TAG_3V3, thermal pad/GND. Datasheet requires >=0.5 uF effective output capacitance and recommends 1 uF close to OUT. | OK electrically; layout cap distance should be checked. |
| U2 SiP32432 | Datasheet identifies IN, OUT, GND, ON/OFF; schematic uses IN on +3V3, OUT on TAG_3V3, ON/OFF from PWR_IN_MIRROR. Analyzer rail-source error on TAG_3V3 is a symbol typing limitation because U2 OUT is marked passive. | False positive, but consider changing the symbol pin type. |
| U7 SN74LVC1T45 | VCCA=+3V3, VCCB=+1V8, DIR=+3V3. Datasheet says DIR high drives A to B, so U7 is fixed 3.3 V to 1.8 V. | Confirmed OK. |
| U8 SN74LVC1T45 | VCCA=+3V3, VCCB=+1V8, DIR is MCU-controlled. | Firmware must set DIR before active traffic and avoid bus contention. |
| U1 XC6206 | SOT-23 pinout is VSS/VIN/VOUT, matching GND/VUSB/+3V3 in the schematic. Datasheet calls for close input/output capacitors. | OK; cap placement should remain close. |
| U10 AP2112K-1.8 | SOT25 pinout is VIN/GND/EN/NC/VOUT, matching +3V3/GND/en1.8v/NC/+1V8. | OK. |
| Q1 BCX70H,215 | Nexperia BCX70H datasheet pin table gives SOT-23 pin 1=B, 2=E, 3=C. The KiCad symbol is `Q_NPN_BEC` with `Sim.Pins` `1=B 2=E 3=C`, so the symbol/footprint pin order matches the intended part. | Verified against local `BCX70H.pdf`. |

## Firmware / Bring-Up Notes

- U5 PA1 drives `en1.8v`, which enables U10 and the local `+1V8` rail.
- `/stm32/clkout` is intended to run at 1024 Hz; treat it as a low-frequency timing/reference output, not a high-speed clock for EMC triage.
- U8 direction is firmware-controlled; define reset/sleep state for that GPIO so the TAG SWDIO path does not fight the external target.
- U5 has many intentionally unused GPIO nets reported as single-pin. Add no-connect markers or route them intentionally if they are planned test points.

## Layout / Manufacturing

- KiCad PCB DRC: 0 violations, 0 unconnected items.
- PCB stats: 53.34 mm x 73.66 mm, 4 copper layers, 52 footprints, 45 SMD, 5 THT, 86 vias, fully routed.
- DFM summary: standard tier, no analyzer DFM metric violations.
- Board-level fiducials are not detected, but the PCB vendor adds fiducials for assembly; treat `FD-001` as vendor-handled rather than a board blocker.
- U3/U5 exposed pads have fewer thermal/ground vias than the analyzer recommends: U3 has 3/9, U5 has 4/9. Thermal analysis is fine for expected power, but tenting/voiding and ground impedance are still worth reviewing before assembly.
- J104 being reported `-0.32 mm` from the board edge is likely an edge-mounted USB connector artifact. Verify the connector courtyard/board edge against the mechanical drawing rather than treating this as automatically wrong.
- Gerber/drill analysis: 11 Gerber files, including `CuIn1` and `CuIn2`; 2 drill files; 139 total holes; 0 analyzer findings.

## EMC / Signal Integrity

The EMC and cross-domain analyzers still report layout risk, but the geometry is localized at connector/fanout clearances. The added stitching vias did not change the sampled coverage: `/SCLK` and `/SWDIO` each miss reference-plane coverage at 1 of 7 sampled points, and `/UART_TX` misses at 1 of 18 sampled points. The reported `+3V3` and `GND` splits are connectivity-graph results; the actual In2 `+3V3` zone fill and In1 GND plane are each one contiguous filled region. Visual inspection puts `/SCLK` around (119,66), `/SWDIO` around (119,65), and `/UART_TX` around (111,66), matching connector/pad antipad geometry rather than a board-level split.

- Treat the connector-local reference misses as acceptable for a breakout if the trace stubs are short and there is no attached high-emissions cable requirement; add nearby ground stitching only if you want extra margin.
- Add ground stitching vias near layer transitions on `TAG_SCK`, SWD, UART, and NRST.
- Review `/SWDIO` and `/SCLK` over their short routed segments and either improve the reference plane continuity or decide that the short length and product environment make the residual risk acceptable.
- `/stm32/clkout` is reported for missing stitching, but at 1024 Hz it is not a meaningful radiated-emissions clock source; keep the note as layout hygiene only.
- Keep `/SCLK` and `TAG_SCK` away from headers where possible, or add grounded guard/stitching nearby. `TAG_SCK` no longer has an EMC error in this pass, but remains a clock-routing warning because it is routed on an outer layer.

## Sourcing / Datasheets

Q1 is assigned as Nexperia `BCX70H,215` in the STM32 sheet and PCB metadata, so the previous Q1 MPN ambiguity is closed. Remaining local datasheet housekeeping is mostly metadata/naming and generated-output hygiene:

- Local PDF coverage exists for the major ICs and several passives.
- KiCad `Datasheet` fields are still only filled for 5/21 BOM lines, so analyzer trust remains `mixed` even though the folder now contains more PDFs.
- Add/normalize datasheet fields for AP2112, TPS7A02, SiP32432, SN74LVC1T45, STM32U375, STM32L432, and RV-3028.
- Regenerate or cross-check production BOM outputs before assembly ordering: the current generated JLCPCB BOM row for Q1 still appears as generic `Q_NPN_BEC` / `C20527`, so confirm that sourcing row maps to Nexperia `BCX70H,215`.

## False Positives / Overrides

- `PP-001` on U11/TAG_3V3 is likely false positive: raw schematic shows TAG_3V3 sourced through U2 OUT, but U2 OUT is typed passive.
- `RS-001` rail-source warnings on external/mirrored rails are expected for connector-sourced rails; add PWR_FLAGs if you want ERC/analyzer quiet.
- `FD-001` board-level fiducials are vendor-handled: the PCB vendor adds fiducials at the panel/assembly level.
- `RP-001` on `/stm32/clkout` is downgraded by design intent: the signal is only 1024 Hz, so the missing adjacent stitching via is not treated as a high-priority EMC issue.
- `PS-002` on `+3V3`/`GND` is partly an analyzer-model issue: the In2 `+3V3` zone has `fill_region_count: 1` and the In1 GND plane has `fill_region_count: 1`, while the connectivity graph counts same-net pads/vias/tracks as separate islands and estimates gap boxes from island bounding boxes. User visual inspection confirms the flagged coordinates are at connector/fanout geometry.
- `PM-002` J104 edge-clearance warning is likely expected for an edge USB connector, pending mechanical confirmation.
- `TE-001` sparse test points is softened because the board is a breakout with large headers, but dedicated ICT/flying-probe pads are still mostly absent.

## Not Performed / Limits

- No SPICE simulation was run because `ngspice`, `ltspice`, and `xyce` were not installed when checked.
- No lifecycle audit was run.
- KiCad lock files were clear when this pass started; this run reflects the saved PCB file on disk from 2026-06-09 14:50:13.
- Datasheet checks were targeted, not an exhaustive page-by-page verification of every passive and connector.
