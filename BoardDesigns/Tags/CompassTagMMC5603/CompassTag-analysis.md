# CompassTag KiCad Analysis

Analysis date: 2026-05-11

Latest analyzer run: 2026-05-11 20:19 local time

Project: `/Users/geobrown/Research/tag-designs/hardware/hardware/CompassTag`

KiCad files analyzed:

- `CompassTag.kicad_sch`
- `CompassTag.kicad_pcb`
- `CompassTag.kicad_pro`

Analyzer outputs:

`/Users/geobrown/Documents/Codex/2026-05-10/analyze-my-kicad-project-at-users/analysis_compasstag_2026-05-11_2019`

## Bottom Line

KiCad ERC and DRC are clean: 0 ERC violations, 0 board DRC violations, 0 unconnected layout items, and 0 schematic-parity issues.

The saved PCB is routed complete, schematic/PCB cross-analysis has no warning-level issues, thermal analysis reports 0 findings, and the regenerated Gerber package now passes the Gerber analyzer with 0 findings. Paste layers are present and the prior alignment warning is gone.

The U501 SCL via-in-pad issue is fixed: the PCB analyzer now reports no `VP-001` via-in-pad findings. The Gerbers/BOM/CPL and PCB are also timestamp-aligned at 2026-05-11 20:18:59, so the previous package-freshness caveat is gone.

The remaining pre-order items are assembly/DFM and intent details: there are no fiducials for fine-pitch two-sided SMT assembly, the board uses advanced-process geometry, and U302 has 4 thermal-pad vias versus the analyzer's 9-via recommendation.

For firmware/bring-up, the important item is that several chip-select, clock, wake, reset, and power-enable nets rely on deliberate STM32L432 GPIO state. Add a project-local `.kicad-happy.json` if you want these states to become persistent machine-readable design intent like we did for TorporTagBreakout.

## User / Firmware Configuration Notes

### Power Profile

User-provided operating-current intent:

- Typical current: about 10 uA
- Normal operating current: below 1 mA
- Peak flash-write current: about 10 mA

This materially downgrades the electrical-current concern behind the analyzer's narrow-trace warnings. The 0.1016 mm traces are still an advanced-process fabrication choice, but they are not a current-capacity concern for the stated load profile. Treat the trace-width findings as DFM/process-selection notes unless a future revision adds materially higher-current loads.

No `mating_design` config was present for CompassTag, so this table is inferred from U302 STM32L432 schematic connectivity and should be reviewed against firmware.

| STM32 pin | Net | Connected part | Recommended reset/sleep state | Why it matters |
|---|---|---|---|---|
| PC14 | `clkout` | RV-3028 CLKOUT | Input/no-pull unless actively using clock output capture | Avoids fighting RTC clock output; clock net is EMC-sensitive. |
| PC15 | `NO_CONNECT` | none | Analog/no-pull | Lowest leakage for unused pin. |
| NRST | `__unnamed_1` | C502, Q501 collector | External reset network controls state | Verify Q501 reset-drive polarity during programming and sleep. |
| PA0 | `WKUP1` | LIS2DU12 INT1 and also U3 pin 5 marked NC | Pull state must match accelerometer interrupt polarity | Wake input should have a deliberate inactive state. Also review the U3 pin 5 NC connection to this net. |
| PA1 | `ACCEL_CS` | LIS2DU12 CS | Pull-up during reset/sleep/high-Z | Keeps accelerometer deselected. |
| PA2 | `USART2_TX` | LIS2DU12 SDA/SDI/SDO | Pull-down or push-pull idle appropriate to selected bus mode | Prevents floating accelerometer data input. Net name suggests UART but part pin is SPI/I2C multiplexed. |
| PA3 | `USART2_RX` | LIS2DU12 SDO/SA0 | Pull-down or no-pull if driven only when CS active | Avoids floating host input and sets address/SDO behavior only if required. |
| PA4 | `USART2_CK` | LIS2DU12 SCL/SPC | Pull-down in reset/sleep/high-Z | Prevents spurious accelerometer clocks. |
| PA5 | `AK_CK` | AK09940A SCL/SK | Pull-down when magnetometer rail is enabled; no-pull/high-Z if AK domain is off | Prevents spurious clocks and avoids back-power risk. |
| PA6 | `AK_MISO` | AK09940A SO | Pull-down or no-pull while AK_CS is inactive | Avoids floating host input. |
| PA7 | `AK_MOSI` | AK09940A SDA/SI | Pull-down when AK domain is enabled; no-pull/high-Z if AK domain is off | Keeps magnetometer input quiet and avoids back-power risk. |
| PB0 | `AK_RSTN` | AK09940A RSTN | Hold low during reset/sleep unless magnetometer is intentionally active | Keeps magnetometer reset while power domain is off or settling. |
| PB1 | `AK_CS` | AK09940A CSB | Pull-up during reset/sleep/high-Z | Keeps magnetometer deselected. |
| PA8 | `NO_CONNECT` | none | Analog/no-pull | Lowest leakage for unused pin. |
| PA9 | `AK_PWR` | TPS7A2018 EN | Drive low or pull-down in sleep; drive high to enable +1V8 | Controls the magnetometer 1.8 V LDO. |
| PA10 | `AK_DRDY` | AK09940A DRDY/TRG | Pull state depends on AK09940 output mode; likely input/no-pull or pull-down when powered | Data-ready line should not float as a wake/event source. |
| PA11 | `NO_CONNECT` | none | Analog/no-pull | Lowest leakage for unused pin. |
| PA12 | `NO_CONNECT` | none | Analog/no-pull | Lowest leakage for unused pin. |
| PA13 | `SWDIO` | J201 SWD | Preserve SWD debug function or use documented debug-disable state | Debug access and leakage trade-off. |
| PA14 | `SWCLK` | J201 SWCLK | Preserve SWD debug function or pull-down if debug disabled | Prevents floating clock input when not debugging. |
| PA15 | `AT25_nCS` | AT25 flash nCS | Pull-up during reset/sleep/high-Z unless external pull-up is added | Analyzer flags missing pull-up; keeps flash deselected. |
| PB3 | `AT25_SCK` | AT25 flash SCK | Pull-down during reset/sleep/high-Z | Prevents spurious flash clocks. |
| PB4 | `AT25_MISO` | AT25 flash SO | Pull-down or no-pull while AT25_nCS is high | Flash SO is normally tri-stated when deselected. |
| PB5 | `AT25_MOSI` | AT25 flash SI | Pull-down during reset/sleep/high-Z | Keeps flash input quiet. |
| PB6 | `SDA` | RV-3028 SDA | I2C pull-up strategy must be explicit | No discrete pull-ups were detected in the schematic analyzer output. |
| PB7 | `SCL` | RV-3028 SCL | I2C pull-up strategy must be explicit | No discrete pull-ups were detected in the schematic analyzer output. |
| BOOT0 | `GND` | ground | Hard low | Normal boot from flash. |

## Inputs And Coverage

| Area | Result |
|---|---|
| Schematic analyzer | 28 components, 39 nets, 18 findings: 0 error, 4 warning, 14 info |
| PCB analyzer | 28 footprints, 387 track segments, 34 vias, 2 zones, routing complete |
| Cross-analysis | 2 info findings: GND plane split into 7 islands; +2V5 plane split into 6 islands |
| Gerber analyzer | 9 Gerbers, 2 drill files, 0 findings |
| EMC analyzer | 37 findings, score 43.0/100 |
| Thermal analyzer | 0 findings, score 100/100 |
| KiCad CLI ERC | 0 violations |
| KiCad CLI DRC | 0 violations, 0 unconnected items, 0 schematic-parity issues |
| SPICE | Not run; `ngspice`, `ltspice`, and `xyce` were not found |
| Datasheets | `datasheets` symlink points to `../libraries/datasheets`; component datasheet fields exist for STM32L432, AT25XE321D, RV-3028, TPS7A20, PMBT2222AMB, and local LIS/AK files |

## Current Findings

| Severity | Finding | Evidence / note |
|---|---|---|
| Info | U501 via-in-pad issue is fixed. | PCB analyzer has no `VP-001` findings in the 20:19 run. |
| Info | Fab outputs are timestamp-aligned and analyzer-clean. | PCB, project, Gerbers, drills, BOM, CPL, and zip are timestamped 2026-05-11 20:18:59; Gerber analyzer reports 0 findings. |
| Warning | No fiducials on either SMT side. | PCB analyzer `FD-001`: 16 F.Cu SMD and 8 B.Cu SMD components, fine-pitch pads present. Add fiducials if assembled by pick-and-place. |
| Warning | Board requires advanced fab geometry. | 0.1016 mm traces, 0.1183 mm approximate spacing, and 0.102 mm annular rings are below common standard-process thresholds. Given the stated 10 uA typical / <1 mA operating / 10 mA flash-write current profile, this is a fabrication-process issue, not an electrical current-capacity issue. |
| Warning | U302 thermal pad has only 4 vias. | PCB analyzer recommends 9 vias for the QFN exposed pad; 4 are untented, so solder wicking risk is also flagged. |
| Warning | AT25 flash nCS lacks an external pull-up. | Schematic analyzer `PR-002`; can be firmware-internal pull-up if guaranteed during reset/sleep. |
| Warning | LIS2DU12 wake/interrupt pull state should be clarified. | `WKUP1` connects STM32 PA0 to LIS2DU12 INT1 and also to U3 pin 5 marked NC in analyzer output; review pin intent. |
| Info | +2V5 and VBAT source warnings are analyzer-only. | KiCad ERC is clean; +2V5 appears fed from VBAT through D401 and available on J201. Document source intent or add a config suppression if this is expected. |

## KiCad CLI ERC / DRC

`kicad-cli` 10.0.2 was run directly from:

`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`

ERC result:

- 0 violations
- Project ignored ERC classes: single global label, four-way junction, simulation model issue, footprint filter

DRC result:

- 0 board DRC violations
- 0 unconnected layout items
- 0 schematic-parity issues
- Project ignored DRC classes include missing courtyard, track-not-centered-on-via, footprint-filter mismatch, PTH/NPTH inside courtyard, and tuning profile geometries

## Production Package Check

Current production package files exist and the Gerber analyzer reports 0 findings.

| File group | Timestamp | Review |
|---|---|---|
| KiCad schematic | 2026-05-11 19:58:01 | Current schematic analyzed |
| KiCad PCB/project | 2026-05-11 20:18:59 | Matches fab output timestamp |
| Gerbers/drills/BOM/CPL/zip | 2026-05-11 20:18:59 | Regenerated; Gerber analyzer clean |

The regenerated Gerber package includes top and bottom paste layers:

- `CompassTag-PasteTop.gbr`
- `CompassTag-PasteBottom.gbr`

Gerber analyzer result: 9 Gerbers, 2 drill files, 39 holes, 570 flashes, 2003 draws, 0 findings.

## Layout / DFM Notes

The board is 18.0 mm x 9.0 mm, 2 copper layers, and routing is complete.

Updated PCB metrics:

- 381 track segments
- 35 vias
- 229.11 mm total routed length
- F.Cu +2V5 zone: 38.90 mm2, 17.9% fill ratio, 3 regions
- B.Cu GND zone: 29.88 mm2, 13.0% fill ratio, 3 regions
- Zone stitching: +2V5 has 6 vias, GND has 9 vias

Manufacturing details to confirm before fab:

- 0.1016 mm traces imply advanced process selection, but are electrically adequate for the stated sub-1 mA operating and 10 mA flash-write peak currents.
- 0.102 mm annular ring is below the analyzer's IPC Class 2/default standard-process threshold.
- U302 exposed pad via count is low for thermal/mechanical soldering robustness.
- U501 SCL via-in-pad is fixed; no `VP-001` findings remain.
- C4 and C404 show medium tombstoning risk due to thermal asymmetry.

## EMC / Return Path Notes

The EMC score is 43.0/100, mostly because this is a very compact 2-layer board with low ground fill, adjacent signal layers, clocks near small connectors/test pads, and sparse stitching near layer transitions.

Highest-priority EMC/layout cautions:

| Net / item | Why flagged |
|---|---|
| B.Cu GND zone | 13% fill ratio and fragmented return path |
| `/AT25_SCK`, `/clkout` | Missing nearby ground stitching at layer transitions; clocks routed near connectors |
| `/AK_DRDY`, `/USART2_TX` | Partial reference-plane coverage |
| `/AK_MOSI`, `/ACCEL_CS`, `/AT25_MISO`, `/AT25_MOSI`, `/AT25_nCS`, `/SDA`, `/USART2_CK`, `/USART2_RX`, `/USART2_TX`, `/WKUP1`, `RST` | Layer transitions without a GND stitching via within the analyzer's 1.0 mm threshold |
| J201/J301-J304/J401 | No connector-level filtering/ESD detected; likely acceptable for test pads/internal battery contacts, but not for cabled use |

For a tiny battery tag this may be acceptable, but if this board will be used with cables, external debug leads, or compliance-sensitive fixtures, add local GND stitching around clock/SPI transitions and consider connector-side ESD/filtering.

## False Positives / Reviewer Overrides

- KiCad ERC/DRC is clean; schematic analyzer source warnings on +2V5/VBAT appear to reflect power-source modeling rather than a KiCad electrical-rule failure.
- Narrow-trace/current-capacity warnings are DFM/process-selection notes for this board. User-provided currents are about 10 uA typical, below 1 mA operating, and about 10 mA peak during flash write.
- Test-point coverage reports 0%, but J201 and the one-pin connectors/test features appear to provide access; decide based on intended production test method.
- EMC connector filtering warnings are likely lower priority for non-cabled tag contacts/test pads.
- Two-layer stackup warning `SU-001` is a generic EMC heuristic; the board is intentionally 2-layer, so treat this as return-path caution rather than an automatic blocker.

## Open Checks Before Fab

1. Add fiducials if using SMT assembly on either side.
2. Decide whether to increase U302 exposed-pad via count and tent/fill/cap exposed-pad vias.
3. Confirm advanced-process fabrication settings for 0.1016 mm traces and 0.102 mm annular rings.
4. Document STM32 reset/sleep GPIO pulls for chip-select, clock, wake, and power-enable nets, ideally in `.kicad-happy.json`.
5. Review the `WKUP1` / LIS2DU12 INT1 plus NC-pin connectivity.
