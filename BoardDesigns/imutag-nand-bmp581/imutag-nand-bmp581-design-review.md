# imutag-nand-bmp581 Design Review

Review date: 2026-08-26  
Project: `BoardDesigns/imutag-nand-bmp581`  
Primary design files: `imutag-nand-bmp581.kicad_sch`, `imutag-nand-bmp581.kicad_pcb`, `imutag-nand-bmp581.kicad_pro`  
Datasheet source used: `BoardDesigns/libraries/datasheets`  
Current analysis run: `analysis/2026-08-26_1027-2`

## Verdict

The latest revision is materially cleaner than the earlier LDO pass. D401 is now gone from both schematic and PCB, U5 and U6 metadata now match the schematic/BOM intent, KiCad DRC is clean, and KiCad ERC is down to one warning: `VBAT` and `VIN` are attached to the same net, with KiCad using `VBAT` in the netlist.

For the magnetometer question, this remains the lower-risk architecture versus `imutag-smps`: there is no local SMPS inductor or switching node near the BMM350. Given your current conclusion that forced-mode SMPS efficiency is essentially LDO-like, the LDO version is the better magnetic/noise choice. The cost is linear-regulator battery efficiency; at your stated 1-2.2 mA average current, the heat is negligible but the energy penalty is real.

I would treat this revision as close to fab-ready electrically. The direct `VBAT`/`VIN` merge is intentional for this LiPo-based design; the joined pins are inherited from a fixed interface that previously supported tiny coin cells with separate charging/feed paths, but that separation is not needed here. The remaining ERC warning is therefore schematic hygiene rather than an electrical concern.

The analyzer's "plane split", "island", and "plane gap" language remains manually downgraded as in the SMPS review. You clarified that the GND and +1V8 planes are connected and that many apparent holes occur where vias and layer changes require antipads. I am therefore treating those reports as local reference-continuity/geometry advisories, not as evidence of disconnected planes. `/clkout` is also treated as a 32 kHz low-risk clock.

## Review Basis

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

## Feedback Carried Forward From imutag-smps

- Fab-house panel fiducials are acceptable for this manufacturing flow; board-level fiducial findings are not treated as blockers.
- STM32 PB7/BOOT0 shared with `/SDA` requires an explicit option-byte write and read-back verification in production programming.
- `/clkout` is 32 kHz, so clock-routing warnings for that net are low risk.
- Analyzer "islands" and "plane gaps" are not treated as disconnected planes when they arise from filled-polygon sampling, via antipads, and layer-change geometry.
- For magnetometer accuracy, calibration data is assembly-specific.
- Because the SMPS is increasingly a magnetometer noise risk and forced mode erases much of the SMPS efficiency advantage, this LDO variant is the cleaner magnetic/noise architecture at the cost of linear-regulator energy loss.
- Expected average current is 1-2.2 mA depending on sampling rate; use that range for battery-life and average LDO power calculations.

## Current Findings

### 1. D401 removal and VBAT/VIN merge are intentional

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

### 2. LDO noise tradeoff remains favorable for the BMM350

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

### 3. TPS7A02185 implementation still looks good

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

### 4. U5/U6 metadata mismatch is resolved

Severity: pass  
Confidence: high  
Evidence: raw schematic/PCB properties and cross-analysis

The previous schematic/PCB mismatches are gone:

- U5 schematic and PCB now both say `LSM6DSV`, MPN `LSM6DSV`.
- U6 schematic and PCB now both say `GD5F2GM7REYIGR`, MPN `GD5F2GM7REYIGR`.
- Cross-analysis no longer emits the old `XV-002` value/MPN mismatch findings.

One minor cleanup remains: the U6 PCB footprint description and 3D model path still reference a `GD5F1...` package/model string. That should not affect electrical connectivity or BOM export because the value/MPN fields are fixed, but it is worth cleaning before documentation/export if you rely on 3D or footprint provenance.

### 5. STM32 PB7/BOOT0 still needs production option-byte programming

Severity: medium bring-up/production risk  
Confidence: high  
Evidence: STM32U375 datasheet, net trace, carried-forward project requirement

U302 pin 30 is `BOOT0-PB7` and is routed as `/SDA`. `/SDA` has a 10 kOhm pull-up to `+1V8`. The intended boot behavior requires programming STM32 option bytes so the I2C pull-up does not force the wrong boot path.

Recommendation:

- Make the option-byte write an explicit production-programming step.
- Read back and log option bytes after programming.
- Document that PB7/BOOT0 is shared with `/SDA`.

### 6. Remaining analyzer errors are not current electrical blockers

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

### 7. Plane/reference findings remain advisory

Severity: low / advisory  
Confidence: high for manual override; medium for residual EMC margin  
Evidence: cross-analysis, EMC analyzer, carried-forward layout interpretation

Cross-analysis reports 10 findings, all related to plane/reference geometry:

- `/clkout` and `SWCLK` crossing GND reference gaps.
- SPI nets crossing GND reference gaps.
- VBAT, GND, and `+1V8` reported as multiple islands.

The EMC analyzer reports the same family of issues: 59 total findings with a risk score of 37.0, dominated by reference-plane sampling, layer-transition stitching, and clock/connector proximity. Given your clarification, these are not treated as proof of disconnected planes. The residual real-world guidance is narrower: where a signal changes layers, keep the nearest practical GND return via nearby when geometry allows. `/clkout` is 32 kHz and low priority; `/AT25_SCK`, SWCLK, and fast SPI edges are the more relevant nets if emissions ever show up on the bench.

## Manufacturing / Layout Notes

- Board: 21.5 mm x 11.5 mm, 4 copper layers, 36 footprints, 418 track segments, 44 vias.
- Routing: complete, 0 unrouted nets.
- KiCad DRC: clean.
- Process class: still an advanced-process layout by generic DFM thresholds: 0.1016 mm minimum trace width, about 0.1052 mm minimum spacing, 0.2032 mm minimum drill, 0.102 mm annular ring.
- Fiducials: analyzer flags missing board-level fiducials on both sides, but fab-house panel fiducials are accepted for this flow.
- Edge clearance: C10 and C507 are 0.68 mm from board edge; C502 is 0.97 mm.
- Via-in-pad: J401 pad 2 still has an untented via-in-pad warning.
- Thermal pad scan: U302 has 7 nearby GND vias; U6 has 8 nearby GND vias. The analyzer's "insufficient" warning uses a generic 9-via threshold, so treat this as assembly/paste/via-treatment review rather than a thermal blocker.
- Test access: analyzer found no dedicated test points; document connector-based access if that is the intended production test strategy.

## Positive Findings

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

## Not Performed / Review Limits

- Lifecycle audit was not performed because network access is restricted and no distributor API credentials are present.
- Gerber analysis was not performed because no fabrication outputs were present.
- SPICE simulation was not performed because no supported simulator was installed.
- Thermal analyzer found 0 hot spots but had 0 component power-dissipation inputs; using the stated 1-2.2 mA average current, LDO average heat is negligible.
- Datasheet extraction cache was not present locally; this review used manual checks against the shared datasheet PDFs.

## Suggested Before-Fab Checklist

1. Optionally rename/remove the remaining `VIN` global labels if you want ERC fully clean.
2. Confirm battery-life impact using the 1-2.2 mA average current range and the expected battery voltage profile.
3. Add/read-back-verify the STM32 BOOT0 option-byte write in the programming flow.
4. Clean the stale U6 footprint description/3D model reference if it matters for documentation or mechanical review.
5. Confirm advanced PCB process assumptions with the intended fab.
6. Review J401 via-in-pad and exposed-pad paste/via treatment with the assembler.
