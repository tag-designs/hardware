# TorporTag KiCad Analysis

**Analyzed path:** `/Users/geobrown/Research/tag-designs/hardware/hardware/TorporTag`  
**Date:** 2026-05-11  
**Files reviewed:** `TorporTag.kicad_sch`, `TorporTag.kicad_pcb`, `TorporTag.kicad_pro`, `jlcpcb/gerber/`  
**Latest analyzer outputs:** `analysis_torpor_2026-05-11_1212/`  
**Previous baseline:** `analysis_torpor/2026-05-11_1153/`

## Verdict

The layout moved in the right direction: a filled GND zone is now present, the “no ground plane zones detected” EMC error cleared, and the EMC score improved from 31/100 to 40/100. I still would not send this as-is for production assembly. The remaining blockers are weak return paths through the dense 2-layer routing, missing stitching near several layer transitions, no fiducials, and advanced-process geometry.

TMP119 GPIO power and STM32 internal pull-ups on the private TMP119 I2C bus are intentional design choices. That makes the analyzer’s TMP119 power/pull-up errors firmware-constraint findings rather than schematic mistakes: bring-up code must configure PB0 and the internal pulls deliberately, and the TMP119 I2C clock should stay slow as planned.

## Delta Since Previous Run

| Area | Change |
|---|---|
| Datasheets | `tmp119.pdf` is now present in `TorporTag/datasheets`. The analyzer still reads U3’s schematic datasheet property as the TI URL, but the local PDF is available for manual verification. |
| Schematic | C5 was removed. Findings stayed at 20 total: 3 errors, 6 warnings, 11 info. |
| PCB | Footprints dropped from 23 to 22. A filled GND zone was added on F.Cu/B.Cu. |
| EMC | `GP-002 No ground plane zones detected` resolved. New remaining issue is `GP-004 Low ground plane fill ratio`. EMC score improved from 31 to 40. |
| Layout warnings cleared | C5/U2 courtyard overlap cleared, C5 edge-clearance warning cleared, U501 pad 3 via-in-pad warning cleared. |
| Still open | TMP119 power rail / pull-ups, missing fiducials, advanced-process DFM dimensions, return-path/stitching issues, Gerber alignment warning. |

## Analyzers Run

| Analyzer | Result |
|---|---|
| `analyze_schematic.py` | 20 findings: 3 errors, 6 warnings, 11 info |
| `analyze_pcb.py --full` | 47 findings: 2 errors, 26 warnings, 19 info |
| `cross_analysis.py` | 7 findings: 2 errors, 3 warnings, 2 info |
| `emc/scripts/analyze_emc.py` | 35 findings: 4 errors, 23 warnings, 8 info; EMC score 40/100 |
| `analyze_thermal.py` | 0 findings, but no component power model was available |
| `analyze_gerbers.py` | 2 findings: Gerber set complete, with alignment/paste notes |

Not run: SPICE, because `ngspice`, LTspice, and Xyce are not installed. KiCad CLI DRC/ERC was not run because `kicad-cli` is not installed. Lifecycle audit was not run because no distributor API credentials or network-backed lifecycle data were available.

## Design Summary

Small 2-layer tag board, 18.0 mm x 9.0 mm, with 22 schematic components and 22 PCB footprints. The PCB has 318 track segments, 29 vias, 42 nets, and complete routing according to the analyzer.

The board now has one filled GND zone on both F.Cu and B.Cu:

| Zone | Detail |
|---|---|
| Net | GND |
| Layers | F.Cu and B.Cu |
| Filled area | 129.68 mm² total |
| Fill ratio | 52.1% |
| Fill regions | 6 |
| GND stitching | 7 vias detected |

Key active parts:

| Ref | Function / value | MPN |
|---|---|---|
| U302 | STM32 MCU, schematic value `stm32l431kc` | `STM32L432KCU6` |
| U1 | SPI flash | `AT25XE321D-UUN-T` |
| U2 | ADXL362 accelerometer | `ADXL362BCCZ-RL7` |
| U3 | TMP119 temperature sensor | `TMP119AIYBGR` |
| U501 | RV-3028-C7 RTC | `RV-3028-C7 32.768KHZ 1PPM-TA-QA` |
| Q501 | NPN reset transistor | `PMBT2222AMBYL` |
| D401 | Schottky input diode | `CDBQC0130L-HF` |

## Highest Priority Findings

| Severity | Finding | Evidence basis |
|---|---|---|
| Critical | TMP119 V+ is still powered from MCU PB0 (`tmp119_pwr`) rather than a declared rail. | Raw-file/analyzer net trace: U302 PB0, U3 V+, and C1 share `tmp119_pwr`. |
| Critical | Return paths remain weak: `/clkout`, `SWCLK`, `/AT25_MISO`, `/AT25_MOSI`, `/AT25_SCK` still cross routed-copper gaps; EMC flags missing stitching on `/ACCEL_SCK`, `/AT25_SCK`, and `/clkout`. | Analyzer-derived from full PCB geometry. |
| Critical | No fiducials on either side despite fine-pitch parts. | Analyzer-derived from PCB footprints. |
| Warning | TMP119 local I2C bus has no external pull-ups by design; it relies on STM32L432 internal pull-ups and slow I2C timing. | User design note plus analyzer net trace. |
| Warning | Ground zone exists but fill ratio is low at about 52%; GND/VIN are still split into multiple routed islands in cross-analysis. | PCB/EMC analyzer. |
| Warning | Board still uses advanced-process geometry: 0.1016 mm traces, 0.1183 mm spacing, and 0.102 mm annular ring. | PCB/DFM analyzer. |
| Warning | U302 value and MPN still disagree: value says `stm32l431kc`, MPN says `STM32L432KCU6`. | Raw schematic property check. |
| Warning | Gerber alignment warning remains: copper/edge layer extents differ by 2.4 mm. | Gerber analyzer. |

## Power / Schematic Notes

`VBAT` enters through J401/J201, D401 feeds `VIN`, and `VIN` powers the MCU, flash, RTC, ADXL362, and decoupling/bulk caps. `VBAT` and `VIN` are still flagged as having no declared source; this likely reflects connector-fed rails, but explicit source/PWR_FLAG intent would make ERC cleaner.

The TMP119 power arrangement is intentional. `tmp119_pwr` is driven from U302 PB0 and feeds U3 V+ plus C1. Treat this as a firmware-controlled switched sensor rail. The important checks are PB0 source-current margin, C1 charging/inrush, reset/default pin state, and ensuring TMP119 access only occurs after PB0 is driven to the intended state.

`tmp119_scl`, `tmp119_sda`, and `tmp119_rdy` are intentionally pulled up with STM32L432 internal pull-ups. Since these are high-impedance pulls, the design should keep the private TMP119 I2C clock slow and configure the pulls before talking to the sensor. This is acceptable as a low-power/private-bus choice, but it should be captured in firmware notes or schematic comments because automated ERC will continue to flag it.

`AT25_nCS` still has no external pull-up. During MCU reset, flash select can float unless the MCU pin state is guaranteed.

## STM32 Internal Pull Configuration

These are the STM32L432 pin bias requirements implied by the schematic and your sleep-state notes. Treat this as a firmware checklist; the exact active/low-power mode matters because some STM32 low-power modes preserve GPIO configuration and some need explicit standby/shutdown pull configuration.

| STM32 pin | Net | Connected part | Internal state to use | Why it matters |
|---|---|---|---|---|
| PA1 | `tmp119_sda` | TMP119 SDA | Pull-up when TMP119 is powered and bus is active; disable pull or make high-Z when `tmp119_pwr` is off | Private I2C SDA needs idle high. Avoid back-powering TMP119 through SDA when PB0 has the sensor rail off. |
| PA2 | `tmp119_scl` | TMP119 SCL | Pull-up when TMP119 is powered and bus is active; disable pull or make high-Z when `tmp119_pwr` is off | Private I2C SCL needs idle high. Weak internal pull means use slow I2C timing. |
| PA3 | `tmp119_rdy` | TMP119 ALERT/RDY | Pull-up only when TMP119 is powered and alert is used; disable/high-Z when `tmp119_pwr` is off | ALERT is open-drain/open-collector style, so it needs a pull-up when active. Also avoid back-power when the TMP119 rail is off. |
| PB0 | `tmp119_pwr` | TMP119 V+ and C1 | Drive output high to power TMP119; drive output low to turn it off. If not actively driven, use pull-down | This is the switched sensor rail. Reset/sleep code must leave it in a defined state. |
| PA4 | `ACCEL_nCS` | ADXL362 CS | Pull-up | Keeps accelerometer SPI deselected during reset/sleep/high-Z MCU states. |
| PA5 | `ACCEL_SCK` | ADXL362 SCLK | Pull-down | Prevents spurious clocks while MCU sleeps or the pin is not actively driven. |
| PA7 | `ACCEL_MOSI` | ADXL362 MOSI | Pull-down | Keeps accelerometer input from floating in sleep. |
| PA6 | `ACCEL_MISO` | ADXL362 MISO/MSIO | Pull-down or no-pull if ADXL362 actively drives in the selected sleep mode | If ADXL362 tri-states MISO while CS is high, the MCU input can float; pull-down is the conservative sleep bias. |
| PA0 | `WKUP1` | ADXL362 INT2 | Pull-down if interrupt is configured active-high; pull-up if configured active-low/open-drain | Must match the ADXL362 interrupt polarity used for wake. This is a wake pin, so the inactive state must be defined. |
| PA15 | `AT25_nCS` | AT25 flash nCS | Pull-up | Keeps flash deselected during reset/sleep/high-Z MCU states. This remains important without an external pull-up. |
| PB3 | `AT25_SCK` | AT25 flash SCK | Pull-down | Prevents spurious flash clocks. |
| PB5 | `AT25_MOSI` | AT25 flash SI | Pull-down | Keeps flash input from floating when flash is deselected. |
| PB4 | `AT25_MISO` | AT25 flash SO | Pull-down or no-pull if known driven | Flash SO is usually tri-stated when nCS is high; pull-down avoids a floating MCU input. |
| PB6 | `SDA` | RV-3028 SDA | Pull-up if there is no external I2C pull-up | RTC I2C SDA needs idle high. If relying on internal pull-ups, use slow I2C timing. |
| PB7 | `SCL` | RV-3028 SCL | Pull-up if there is no external I2C pull-up | RTC I2C SCL needs idle high. If relying on internal pull-ups, use slow I2C timing. |
| PC14 | `clkout` | RV-3028 CLKOUT | No-pull if RTC actively drives CLKOUT; pull-down if CLKOUT can be disabled/tri-stated in sleep | Avoids a floating MCU input if the RTC clock output is disabled. |
| PA13 | `SWDIO` | SWD header | Leave SWD default pull-up while debug is enabled; otherwise analog/no-pull for lowest sleep current | Debug interface has its own expected idle behavior. Do not fight the debugger unless SWD is disabled. |
| PA14 | `SWCLK` | SWD header | Leave SWD default pull-down while debug is enabled; otherwise analog/no-pull for lowest sleep current | Debug clock should not float during debug use. |
| PB1, PC15, PA8-PA12 | unconnected | none | Analog/no-pull | Lowest leakage state for unused GPIOs. |

Boot/reset pins are separate from normal GPIO firmware setup: BOOT0 is hard-tied to GND in the schematic, and `~NRST` has the reset capacitor/transistor network rather than a firmware-configurable internal pull plan.

## PCB / EMC Notes

The added GND zone is a meaningful improvement. The remaining issue is that the zone is fragmented by dense routing: fill ratio is about 52%, and cross-analysis still reports GND split into 7 islands and VIN split into 8 islands. EMC now reports low fill ratio instead of complete absence of a ground plane.

Placement and fabrication status:

| Item | Detail |
|---|---|
| Fiducials | Still missing on both sides. Add them for assembly, especially with DSBGA/WLCSP/QFN-style parts. |
| Courtyard overlap | C5/U2 overlap cleared because C5 was removed. U1/U2 overlap remains, but tiny at 0.006 mm². |
| Edge clearance | C5 edge issue cleared. C2 remains 0.6 mm from edge; U3 remains 0.75 mm from edge. |
| U302 thermal pad | 3 thermal vias found versus nominal 9-via recommendation. Likely tolerable for low power, but not thermally proven. |
| Test access | 0/41 nets detected as test points. |
| Via-in-pad | Previous U501 pad 3 via-in-pad warning cleared. |

## Gerber / Production Output

The `jlcpcb/gerber/` folder was not regenerated; timestamps are still from May 6, 2026, so it may not reflect the updated layout. Analyzer results on that folder are unchanged:

| Severity | Finding |
|---|---|
| Warning | Layer extents vary by 2.4 mm between copper and edge layers. Review in CAM before ordering. |
| Info | F.Paste is missing. If this is for assembly, export paste or confirm the assembler derives paste from pads. |

Regenerate Gerbers/drills from the current PCB before ordering.

## Reviewed False Positives / Downgrades

The ADXL362 `INT1` missing-pull-up warning still looks non-actionable: U2 INT1 is no-connect, while INT2 is wired to `WKUP1`.

The TMP119 `tmp119_pwr` and `tmp119_scl`/`tmp119_sda` pull-up findings are intentional design choices, not mistakes. Residual risk is firmware/configuration dependent: PB0 and the internal pulls must be configured correctly, and I2C speed must remain slow enough for the weak pull-ups.

The `VBAT`/`VIN` no-source warnings look like connector-fed rail style issues, not necessarily broken wiring.

The EMC connector-filter warnings are heuristic. If J201/J30x are pogo/test pads and not user cables, treat them as lower risk than true external connectors.

## Review Limits

The local datasheet directory now includes STM32L432, ADXL362, AT25XE321D, RV-3028, TMP119, and LIS2DW12 PDFs. I did not run structured datasheet extraction, so this report still does not claim exhaustive manufacturer pinout verification for every part.

Thermal analysis produced no findings because no component power model was available, not because junction temperatures were proven safe. SPICE and KiCad CLI DRC/ERC were unavailable in this environment.

## Recommended Fix Order

1. Improve GND/VIN continuity: increase usable GND fill, reduce fragmentation, and add GND stitching vias near every signal layer transition.
2. Document the TMP119 firmware contract: PB0 powers V+, internal pulls are enabled for `tmp119_scl`/`tmp119_sda`/`tmp119_rdy`, and the private I2C clock is intentionally slow.
3. Verify PB0 current/inrush/reset behavior against the TMP119 and STM32 datasheets.
4. Add an external pull-up for `AT25_nCS` unless reset-state behavior is otherwise guaranteed.
5. Add assembly fiducials and intentional test access.
6. Revisit advanced-process dimensions if using standard low-cost fab rules.
7. Resolve U302 value/MPN mismatch.
8. Regenerate current Gerbers/drills and recheck CAM alignment/paste output.
