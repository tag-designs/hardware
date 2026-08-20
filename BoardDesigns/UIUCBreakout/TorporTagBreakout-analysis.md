# TorporTagBreakout KiCad Analysis

Analysis date: 2026-05-11

Latest analyzer run: 2026-05-11 15:40 local time

Project: `/Users/geobrown/Research/tag-designs/hardware/hardware/TorporTagBreakout`

KiCad files analyzed:

- `TorporTagBreakout.kicad_sch`
- `TorporTagBreakout.kicad_pcb`
- `TorporTagBreakout.kicad_pro`

Analyzer outputs:

`/Users/geobrown/Documents/Codex/2026-05-10/analyze-my-kicad-project-at-users/analysis_torportagbreakout_2026-05-11_1540`

## Bottom Line

The layout tweaks did not introduce KiCad ERC/DRC regressions. KiCad ERC reports no violations. KiCad DRC reports 0 board violations and 0 unconnected layout items; the only DRC output remains two schematic-parity warnings for the custom J3/J4 footprint filters.

The refreshed PCB remains routed complete, cross-analysis is clean, and thermal analysis is clean. The most relevant open items are still manufacturing/intent items rather than board-function blockers: top-side fiducials if using SMT assembly, J3/J4 edge spacing, the J3/J4 footprint-filter metadata warnings, and the firmware contract for sleep/reset/internal pulls.

One fab-output caveat: the Gerbers/BOM/CPL are timestamped 2026-05-11 15:37:58, while the saved PCB is timestamped 15:38:04. That six-second gap may just be KiCad plot/save order, but regenerate fabrication outputs once more if the last PCB save contained a real copper/layout change.

## User / Firmware Configuration Notes

These are the board-user and firmware-contract details that should be read before the lower-level analyzer findings.

### Optional TMP119 Pull-ups

R3, R4, and R5 are optional fallback pull-ups, not default population parts. They should remain DNP unless the STM32L432 internal pull-ups are insufficient at the chosen slow I2C clock.

| Ref | Net | Connection | Intended status |
|---|---|---|---|
| R5 | `tmp119_sda` | 10 kOhm to `tmp119_pwr` | DNP / fallback if STM32 internal pull-up is insufficient |
| R4 | `tmp119_scl` | 10 kOhm to `tmp119_pwr` | DNP / fallback if STM32 internal pull-up is insufficient |
| R3 | `tmp119_rdy` | 10 kOhm to `tmp119_pwr` | DNP / fallback if STM32 internal pull-up is insufficient |

The assembly BOM/CPL still correctly exclude R3/R4/R5. The analyzer still emits I2C/pull-up findings because it does not treat DNP resistors or MCU internal pulls as active electrical pull-ups. For this design, those findings are firmware/configuration constraints, not schematic mistakes.

If R3/R4/R5 are populated, they pull to `tmp119_pwr`, which is the desired switched rail. If they remain DNP, the STM32 internal pulls should be enabled only when `tmp119_pwr` is on, then released to no-pull/high-Z when the TMP119 rail is off to avoid back-power paths.

### Host STM32L432 Internal Pull Configuration

This breakout does not include the STM32L432 symbol, so exact STM32 pin names come from the mating TorporTag design where known. Header pins are from this breakout schematic.

| Host STM32 pin | Breakout header | Net | Connected part | Recommended host state | Why it matters |
|---|---:|---|---|---|---|
| PA1 | J3.9 | `tmp119_sda` | TMP119 SDA, optional R5 to `tmp119_pwr` | Pull-up only when `tmp119_pwr` is on; no-pull/high-Z when off | Default plan is STM32 internal pull-up. Avoid back-powering TMP119 when its rail is off. |
| PA2 | J3.10 | `tmp119_scl` | TMP119 SCL, optional R4 to `tmp119_pwr` | Pull-up only when `tmp119_pwr` is on; no-pull/high-Z when off | Weak internal pull implies slow I2C timing. |
| PA3 | J3.11 | `tmp119_rdy` | TMP119 ALERT/RDY, optional R3 to `tmp119_pwr` | Pull-up only when TMP119 is powered and alert is used; no-pull/high-Z when off | ALERT is open-drain style; avoid back-power paths. |
| PB0 | J3.16 | `tmp119_pwr` | TMP119 V+, C1, optional pull-up rail | Push-pull high to power TMP119; drive low or hold pull-down/off in sleep | This pin is the switched sensor rail. |
| PA4 | J3.12 | `ACCEL_nCS` | ADXL362 `~CS` | Pull-up during reset/sleep/high-Z unless an external pull-up is added | Keeps accelerometer deselected. |
| PA5 | J3.13 | `ACCEL_SCK` | ADXL362 SCLK | Pull-down in reset/sleep/high-Z | Prevents spurious accelerometer clocks. |
| PA6 | J3.14 | `ACCEL_MISO` | ADXL362 MISO/MSIO | Pull-down or no-pull if ADXL362 is known driven in sleep | Avoids floating host input while CS is high. |
| PA7 | J3.15 | `ACCEL_MOSI` | ADXL362 MOSI | Pull-down in reset/sleep/high-Z | Keeps accelerometer input quiet. |
| PA0 | J3.8 | `WKUP1` | ADXL362 INT2 | Pull-down if interrupt is active-high; pull-up if configured active-low/open-drain | Wake source inactive state must be deliberate. |
| PA15 | J4.3 | `AT25_nCS` | AT25 flash nCS | Pull-up during reset/sleep/high-Z unless an external pull-up is added | Keeps flash deselected. |
| PB3 | J4.2 | `AT25_SCK` | AT25 flash SCK | Pull-down in reset/sleep/high-Z | Prevents spurious flash clocks. |
| PB4 | J3.1 | `AT25_MISO` | AT25 flash SO | Pull-down or no-pull if known driven | Flash SO is usually tri-stated when nCS is high. |
| PB5 | J3.2 | `AT25_MOSI` | AT25 flash SI | Pull-down in reset/sleep/high-Z | Keeps flash input quiet while deselected. |
| From mating design | J4.8 | `LED1` | LED D1 cathode, R1 to +3.3V | Pull-up or push-pull high for LED off | LED is active-low from host perspective. |
| From mating design | J4.16 | `LED2` | LED D2 cathode, R2 to +3.3V | Pull-up or push-pull high for LED off | Same active-low LED behavior. |

## Previous Review Delta

| Item | Status |
|---|---|
| KiCad ERC | Still clean: `kicad-cli sch erc` reports no violations. |
| KiCad DRC | Still clean for physical layout: 0 violations, 0 unconnected items. |
| Schematic parity | Unchanged: 2 warnings remain, both J3/J4 footprint-filter mismatches. |
| PCB routing | Still complete; track count changed from 146 to 159 and total track length decreased from 522.71 mm to 509.14 mm. |
| Vias / stitching | Changed from 178 total vias / 169 GND stitching vias to 162 total vias / 145 GND stitching vias. |
| F.Cu GND fill | Slightly improved: 1575.43 mm2, 34.3%, 15 regions. |
| B.Cu GND fill | Slightly reduced: 2045.87 mm2, 43.0%, 2 regions. |
| Cross-analysis | Clean: 0 schematic-vs-PCB findings. |
| Thermal | Clean: 0 findings, 100/100 score. |
| EMC heuristic score | Still 62.5/100. Finding count is now 25; the new/change item is `AT25_MOSI` layer-transition return-path warning, while `tmp119_pwr` downgraded to info. |
| Production package | Present and consistently named, but timestamps are 6 seconds older than the saved PCB. Regenerate if the final PCB save affected copper. |

## Inputs And Coverage

| Area | Result |
|---|---|
| Schematic analyzer | 16 components, 44 nets, 23 findings: 2 error, 8 warning, 13 info |
| PCB analyzer | 16 footprints, 159 track segments, 162 vias, 2 GND zones, routing complete |
| Cross-analysis | 0 findings |
| Gerber analyzer | 11 manufacturing files found: 9 Gerbers, 2 drill files; 1 paste-ratio warning |
| EMC analyzer | 25 findings, score 62.5/100 |
| Thermal analyzer | 0 findings, score 100/100 |
| KiCad CLI ERC | 0 violations |
| KiCad CLI DRC | 0 DRC violations, 0 unconnected layout items, 2 schematic-parity warnings |
| SPICE | Not run; `ngspice`, `ltspice`, and `xyce` were not found |
| Datasheets | `datasheets` symlink points to `../libraries/datasheets`; PDFs found for STM32L432, TMP119, LIS2DW12, AT25XE321D, RV-3028, and ADXL362 |

Note: this Codex shell still did not resolve `kicad-cli` from `PATH`, likely because the running shell did not reload the updated `.zshrc`. I used `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` directly.

## Current Findings

| Severity | Finding | Evidence / note |
|---|---|---|
| Warning | Regenerate final fab outputs if the 15:38:04 PCB save changed copper. | Existing Gerbers/BOM/CPL are timestamped 15:37:58, six seconds older than the PCB. Gerber analysis was run on those outputs and found a complete layer/drill set. |
| Warning | Add fiducials if using SMT assembly. | PCB analyzer `FD-001`: 0 top-side fiducials with 14 SMD parts and 0.25 mm finest pad dimension. |
| Warning | J3/J4 sit 0.74 mm from the board edge. | Analyzer recommends >= 1.0 mm for handling/depanel risk. This may be intentional for the breakout geometry. |
| Warning | J3/J4 schematic parity warnings remain. | KiCad DRC: custom `tag_library:PinHeader_1x17_P2.54mm_Vertical_Staggered` footprint does not match symbol filter `Connector*:*_1x??_*`. |
| Warning | Host-side GPIO sleep/reset bias is required. | Breakout has no MCU; all control nets leave through J3/J4. See the STM32 pull table near the top of this report. |
| Warning | EMC heuristics still flag several return-path/reference-plane items. | Most are expected for a dense two-layer breakout. Highest-priority nets are `/AT25_SCK` and `/ACCEL_SCK`; return-path warnings remain on several SPI/control nets. |
| Info | Gerber analyzer reports a front-paste ratio warning. | F.Paste has 56 flashes vs 252 copper flashes. This appears to be a heuristic caution, not a missing package issue: top paste exists, bottom paste is effectively empty, and CPL/BOM contain only top-side assembly parts. |
| Info | Explicit test-point coverage is 0%. | Most nets are accessible on headers; acceptable if header probing is the intended test method. |

## KiCad CLI ERC / DRC

`kicad-cli` 10.0.2 was run directly from:

`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`

ERC result:

- 0 violations
- Ignored check classes in the project: single global label, simulation model issue, footprint link issue

DRC result:

- 0 board DRC violations
- 0 unconnected layout items
- 2 schematic-parity warnings:
  - J3 footprint filter mismatch
  - J4 footprint filter mismatch

These remaining parity warnings are metadata/library hygiene items, not copper/layout violations.

## Production Package Check

Freshly named production files are present:

- `jlcpcb/gerber/TorporTagBreakout-CuTop.gbr`
- `jlcpcb/gerber/TorporTagBreakout-CuBottom.gbr`
- `jlcpcb/gerber/TorporTagBreakout-EdgeCuts.gbr`
- `jlcpcb/gerber/TorporTagBreakout-MaskTop.gbr`
- `jlcpcb/gerber/TorporTagBreakout-MaskBottom.gbr`
- `jlcpcb/gerber/TorporTagBreakout-PasteTop.gbr`
- `jlcpcb/gerber/TorporTagBreakout-PasteBottom.gbr`
- `jlcpcb/gerber/TorporTagBreakout-SilkTop.gbr`
- `jlcpcb/gerber/TorporTagBreakout-SilkBottom.gbr`
- `jlcpcb/gerber/TorporTagBreakout-PTH.drl`
- `jlcpcb/gerber/TorporTagBreakout-NPTH.drl`
- `jlcpcb/production_files/BOM-TorporTagBreakout.csv`
- `jlcpcb/production_files/CPL-TorporTagBreakout.csv`

Assembly BOM/CPL check:

| Check | Result |
|---|---|
| Active assembly parts | C1/C2/C3/C5, R1/R2, D1/D2, U1, U2, U3 |
| R3/R4/R5 optional TMP119 pull-ups | Correctly absent from BOM and CPL |
| CPL side | All assembled parts are top-side |
| Current naming | Uses `TorporTagBreakout`, not old `TorperTagBreakout` or `IMUTagBreakout` names |
| Timestamp caveat | Package files are six seconds older than the PCB file; regenerate if the last PCB save changed copper |

## Layout / DFM Notes

The board is 48.26 mm x 48.26 mm, 2 copper layers, 1.6 mm thick. Routing is complete.

Updated saved PCB metrics:

- 159 track segments
- 162 total vias
- 145 GND stitching vias
- Total routed track length: 509.14 mm
- F.Cu GND filled area: 1575.43 mm2, 34.3% fill ratio, 15 regions
- B.Cu GND filled area: 2045.87 mm2, 43.0% fill ratio, 2 regions

Decoupling placement remains reasonable:

| IC | Closest matching bypass cap |
|---|---|
| U3 TMP119 | C1 at about 2.2 mm on `tmp119_pwr`/GND |
| U1 AT25XE321D | C2 at about 2.5 mm on +3.3V/GND |
| U2 ADXL362 | C3 at about 2.0 mm on +3.3V/GND |

The EMC analyzer additionally flags C5 as 3.2 mm from a nearby via. That is worth checking visually, but not a KiCad DRC issue.

## EMC / Return Path Notes

The EMC heuristic still reports partial reference-plane and layer-transition warnings. These are useful cautions, but they should be interpreted in context: this is a compact two-layer breakout with long header-routed signals.

Highest-priority EMC/layout cautions:

| Net / item | Why flagged |
|---|---|
| `/AT25_SCK` | Partial reference coverage and close proximity to J4 |
| `/ACCEL_SCK` | Partial reference coverage |
| `/tmp119_sda`, `/tmp119_rdy` | Partial reference coverage on low-speed TMP119 nets |
| `/ACCEL_MOSI`, `/ACCEL_nCS`, `/AT25_MOSI`, `/AT25_nCS`, `/WKUP1` | Layer transitions without a ground stitching via within the analyzer's 1.0 mm threshold |
| `/tmp119_pwr` | Now downgraded to info: 4 layer transitions, 1 without a ground stitching via within 1.0 mm |
| J3/J4 | Low ground-pin ratio and no connector-level filtering/ESD |

For a lab/prototype breakout, these are not blockers. For cabled use, compliance testing, or noisy environments, prioritize additional ground references around the headers, nearby stitching at signal layer changes, and filtering/ESD at external cable entry points.

## False Positives / Reviewer Overrides

- TMP119 I2C missing-pull-up errors: intentional when R3/R4/R5 are DNP and the host STM32 internal pulls are being evaluated.
- TMP119 ALERT/SCL/SDA pull-up warnings: same root cause; these are firmware and population-option constraints.
- `tmp119_pwr` source warning from the schematic analyzer: intentional switched rail driven by STM32 PB0 in the mating TorporTag design.
- `+3.3V` source warning from the schematic analyzer: expected on a breakout where power arrives from the mating board/header.
- ADXL362 INT1 missing-pull warning: non-actionable; U2 INT1 is no-connect.
- Gerber F.Paste ratio warning: likely heuristic noise from comparing paste flashes to all copper flashes, including non-paste copper.
- Test-point coverage warning: lower priority because the board is a breakout and the header pins provide access.

## Open Checks Before Fab

1. Regenerate final Gerbers/BOM/CPL if the last PCB save after 15:37:58 changed copper or component placement.
2. Add top-side fiducials if this will be pick-and-place assembled.
3. Confirm J3/J4 0.74 mm board-edge spacing is acceptable for the chosen fabrication/handling flow.
4. Decide whether to update the J3/J4 symbols or footprint filters to quiet the remaining KiCad schematic-parity warnings.
5. Keep R3/R4/R5 DNP in assembly unless measured rise time with STM32 internal pulls is inadequate.
6. Confirm firmware reset/sleep pull configuration for TMP119, ADXL362, AT25, and LED nets before low-power testing.
7. For cabled or compliance-sensitive use, consider extra return-path stitching near SPI/control layer transitions and connector-side ESD/filtering.
