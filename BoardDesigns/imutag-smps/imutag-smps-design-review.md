# imutag-smps Design Review

Review date: 2026-08-25  
Project: `BoardDesigns/imutag-smps`  
Primary design files: `imutag-smps.kicad_sch`, `imutag-smps.kicad_pcb`, `imutag-smps.kicad_pro`  
Datasheet source used: `BoardDesigns/libraries/datasheets`

## Verdict

The design is electrically close: schematic and PCB component counts match, all nets are routed, KiCad DRC reports zero violations and zero unconnected items, and the main power topology matches the relevant datasheets. I would not treat the raw analyzer "U6 has no DC power path" and "LSM6DSV SPI pins need I2C pull-ups" reports as real electrical blockers.

I would still do a focused metadata/layout cleanup before fab. The main issues are fragmented return paths for the SPI/SWD signals, U5 PCB metadata not matching the intended LSM6DSV part, the required STM32 BOOT0 option-byte programming step, and several assembly/process constraints that need an intentional fab/assembly decision. The `/clkout` net is only 32 kHz, so its plane-gap finding is low risk compared with the SPI and SWD clocks.

## Review Basis

Tools and files checked:

- KiCad ERC: 3 warnings, 0 errors.
- KiCad DRC: 0 violations, 0 unconnected items.
- Schematic analyzer: 22 findings, including 3 errors that were manually triaged against datasheets.
- PCB analyzer: 50 findings, including 2 fiducial findings that are covered by the fab house's panel process, plus DFM warnings.
- Cross-analysis: 11 findings, including 5 return-plane/plane-split errors.
- EMC analyzer: 63 findings, risk score 29.5.
- Thermal analyzer: 0 findings, but 0 components had power-dissipation data, so this is not a thermal proof.
- Gerber review: not performed; no Gerber/fabrication outputs were present.
- SPICE: not performed; no ngspice, LTspice, or Xyce executable was available.
- Lifecycle/availability audit: not performed; no distributor API credentials were available and network access is restricted.

Datasheets manually cross-checked from the shared library:

- `tps62840.pdf`
- `tps22916.pdf`
- `DS_00819_GD5F2GM7RE_Rev1_3-3435814.pdf`
- `stm32u375ce.pdf`
- `bst-bmm350-ds001.pdf`
- `bst-bmp581-ds004.pdf`
- `RV-3028-C8.pdf`
- `PMBT2222AMB.pdf`
- `lsm6dsv.pdf`

User-confirmed design intent: U5 is `LSM6DSV`. The PCB currently calls U5 `LSM6DSV16X` / `LSM6DSV16XTR`, so this is a metadata synchronization issue rather than an unresolved part selection question.

## High Priority Findings

### 1. U5 PCB metadata differs from the intended LSM6DSV part

Severity: medium-high  
Confidence: high  
Evidence: cross-analysis, schematic BOM, PCB footprint properties, shared datasheet library, user-confirmed design intent

The intended part is `LSM6DSV`. The schematic/BOM identifies U5 as `LSM6DSV` with MPN `LSM6DSV`, while the PCB footprint properties identify it as `LSM6DSV16X` / `LSM6DSV16XTR`. The shared datasheet directory contains `lsm6dsv.pdf`.

Why it matters:

- The electrical design intent is clear, but the PCB metadata can still cause BOM/CPL ordering mistakes or review confusion.
- If assembly data is generated from PCB fields, the wrong MPN could propagate into manufacturing files.

Recommendation:

- Update U5 PCB value/MPN fields to `LSM6DSV`.
- Re-run the cross-analysis after the metadata update.

### 2. Return paths and planes are fragmented for SPI/SWD signals

Severity: medium-high for EMC and signal robustness  
Confidence: medium-high  
Evidence: cross-analysis and EMC analyzer; user-confirmed `/clkout` frequency; KiCad DRC is clean

The cross-check reports that several nets cross reference-plane gaps:

- `/clkout` crosses a VBAT plane gap, but this is user-confirmed as a 32 kHz clock and is therefore low risk.
- `SWCLK` crosses a GND plane gap.
- `/LPS_MOSI`, `/LPS_MISO`, `/AT25_MISO`, `/AT25_SCK`, and `/AT25_MOSI` cross GND plane gaps.
- Plane split summary: VBAT has 4 islands, GND has 18 islands, and +1V8 has 6 islands.

The EMC analyzer similarly flags low reference-plane coverage on several nets, with the worst examples including `/BMM_INT`, `/AT25_MISO`, `/SCL`, `/SDA`, `/AT25_SCK`, `/AT25_MOSI`, `/LSM_TRG`, `RST`, `/clkout`, and `SWCLK`.

Why it matters:

- These are short traces on a very small board, so the absolute loop sizes are limited.
- The 32 kHz `/clkout` trace is not a high-speed EMC driver.
- The affected SPI and SWD nets still have fast edges. Return-current detours can increase emissions and susceptibility, especially near the TPS62840 buck converter.

Recommendation:

- Prioritize continuous GND reference under `/AT25_SCK`, `/AT25_MOSI`, `/AT25_MISO`, `SWCLK`, `/SCL`, and `/SDA`.
- Treat `/clkout` as a low-priority cleanup unless it is routed off-board or used as a sensitive timing reference.
- Add nearby GND stitching vias at layer transitions, especially for `/AT25_SCK` and `SWCLK`.
- Avoid routing high-edge-rate signals over voids between GND islands or power pours.
- Re-pour and re-run cross/EMC checks after layout changes.

### 3. Fiducials are supplied by the fab panel, not the board

Severity: low, assuming the fab/assembly house controls panel fiducials  
Confidence: high  
Evidence: PCB analyzer and user-provided fab process note

The board file itself has SMD components on both sides, including fine-pitch/WLCSP/BGA-like parts, and the analyzer found no board-level fiducials on either `F.Cu` or `B.Cu`. The fab house adds its own fiducials in the panel, so this is not a board-design blocker for that manufacturing flow.

Why it matters:

- Fine-pitch devices such as U2 BMM350, U4 TPS62840 WLCSP, and U302 UFQFPN benefit from local/global fiducials.
- If the design is moved to another assembler or panelization flow, board- or panel-level fiducials must still be present.

Recommendation:

- Keep the fab house's panel fiducial requirement documented with the manufacturing package.
- Revisit board-level/local fiducials only if changing assembler or panel process.

### 4. PB7/BOOT0 use requires an option-byte programming step

Severity: medium bring-up/production risk  
Confidence: high  
Evidence: STM32U375 pinout datasheet, PCB footprint properties, user-confirmed programming requirement

U302 pin 30 is `BOOT0-PB7` and is routed as `/SDA`. `/SDA` has a 10 kOhm pull-up to +1V8. The intended boot behavior requires programming the STM32 option bytes so this pin sharing does not force the wrong boot path.

Why it matters:

- A blank or reworked MCU may not boot as intended until the option-byte write has been performed.
- Any production programming flow that erases or changes option bytes can reintroduce the issue.

Recommendation:

- Make the option-byte write an explicit, verified step in the production programming script.
- Read back and log the option bytes after programming.
- Document that PB7/BOOT0 is shared with `/SDA` and depends on that programmed configuration.

### 5. Magnetometer placement should be validated against the buck converter and assembly

Severity: medium  
Confidence: medium  
Evidence: PCB footprint coordinates and BMM350 datasheet role as geomagnetic sensor

U2 BMM350 is placed on the right side of the board. The center-to-center spacing from U2 to the TPS62840 inductor L1 is about 11.49 mm; spacing to U4 is about 12.09 mm. That is reasonable for a 21.5 mm x 11.5 mm board, but it is still close in absolute terms for a magnetometer.

Why it matters:

- The buck inductor, battery current path, nearby ferromagnetic parts, and assembly hardware can create magnetic offset.
- BMM350 accuracy may vary with regulator load state and mechanical mounting.

Recommendation:

- Measure magnetometer offsets with the buck enabled at idle and at expected peak load.
- Keep high-current loops and magnetic materials as far from U2 as the mechanical envelope allows.
- Treat calibration data as board- and assembly-specific.

## Medium Priority Findings

### 6. I2C pull-ups are acceptable for light capacitance but should be verified at 400 kHz

Severity: medium  
Confidence: medium-high  
Evidence: schematic analyzer and protocol check

The real I2C bus is `/SDA` and `/SCL`, shared by U2 BMM350, U501 RV-3028-C8, and U302. R2 and R3 are 10 kOhm to +1V8.

The analyzer estimates about 212 ns rise time at 25 pF, which fits 400 kHz fast-mode rise-time limits. At higher bus capacitance, 10 kOhm can become marginal.

Recommendation:

- Keep 10 kOhm if the bus is short and measured rise time is acceptable.
- If using 400 kHz and the measured rise time is slow, consider 4.7 kOhm or lower-power firmware scheduling tradeoffs.

### 7. Advanced PCB process assumptions are baked into the layout

Severity: medium  
Confidence: high  
Evidence: PCB analyzer DFM summary

Detected minimums:

- Track width: 0.1016 mm
- Approximate spacing: 0.1052 mm
- Drill: 0.2032 mm
- Annular ring: 0.102 mm

KiCad DRC passes because the board rules allow these values, but the analyzer classifies the design as requiring an advanced process and notes the via annular ring is below the IPC Class 2 default threshold used by the analyzer.

Recommendation:

- Confirm the intended fab process supports these rules, including 4 mil class trace/space and 0.2 mm drills.
- Keep the fab stackup and capabilities tied to the project configuration, not only to order notes.

### 8. Edge clearance and via-in-pad details need assembly review

Severity: medium  
Confidence: high  
Evidence: PCB analyzer

Issues found:

- C10 and C507 are 0.68 mm from the board edge.
- C502 is 0.97 mm from the board edge.
- J401 pads 1 and 2 have untented vias in SMD pads.
- U302 and U6 exposed-pad via patterns were flagged by the analyzer; raw footprint scan sees nearby vias, so the main concern is solder wicking/voiding treatment rather than copper access.

Recommendation:

- Increase edge clearance for C10/C507/C502 if panelization or depaneling stress is expected.
- Tent, cap, or otherwise document via-in-pad treatment for J401 and exposed-pad regions as required by the assembler.
- Review paste apertures for exposed pads so the vias do not steal too much solder.

### 9. Test coverage is minimal

Severity: medium  
Confidence: high  
Evidence: PCB analyzer

The analyzer found 0 dedicated test points across 36 signal nets. The design does have connectors/SWD access, but production test and bring-up would benefit from intentional pads.

Recommendation:

- At minimum, make VBAT, +1V8, GND, RST/NRST, SWDIO, SWCLK, `/SDA`, `/SCL`, and `/FLASH_PWR` easy to probe.
- If board area is too tight, document which connector pads are the official test access points.

### 10. Schematic pin-map note is stale

Severity: medium  
Confidence: high  
Evidence: schematic text annotation and actual U302 pad nets

The schematic text note says `PA8 - LSM_TRG`, `PA9 - LPS_CS`, `PA10 - LPS_DRDY`, and `PB4 - xx`. The actual PCB/schematic net mapping shows:

- PA8 is `/FLASH_PWR`.
- PA9 is `/LPS_DRDY`.
- PA10 is `/LPS_CS`.
- PB4 is `/LSM_TRG`.
- PB6 is `/SCL`.
- PB7/BOOT0 is `/SDA`.

Recommendation:

- Update the schematic note before firmware bring-up so the pin map does not mislead firmware or test work.

## Checks That Passed

### TPS62840 1.8 V buck configuration

Confidence: high  
Evidence: TPS62840 datasheet and schematic/PCB net mapping

The TPS62840YBGR configuration matches the datasheet:

- VIN on VBAT.
- EN tied to VBAT, so +1V8 is always enabled when VBAT is present.
- VSET tied to GND, selecting 1.8 V for the YBG package variant.
- 2.2 uH inductor is used.
- 4.7 uF input and 10 uF output capacitance are present.
- Input capacitor C7 is close to U4 at about 1.15 mm.

Layout still deserves a visual/current-loop review around VIN, SW, L1, C7, C8, and GND because switching supply layout dominates actual performance.

### TPS22916 flash load switch

Confidence: high  
Evidence: TPS22916 datasheet and net trace

U1 is wired consistently:

- VIN: +1V8
- VOUT: `/Flash 1V8`
- ON: `/FLASH_PWR` from U302 PA8
- GND: GND

The B variant has fast turn-on behavior. With about 1.1 uF on `/Flash 1V8` near the flash, estimated inrush is modest. Firmware must still ensure the flash is not powered down during write/erase/program operations.

### GD5F2GM7RE SPI NAND pinout and power

Confidence: high  
Evidence: GD5F2GM7RE datasheet and U6 pad nets

U6 pin mapping matches the datasheet for standard SPI:

- CS#, SO/SIO1, SI/SIO0, and SCLK route to the AT25 SPI bus nets.
- VCC is on `/Flash 1V8`.
- WP#/SIO2 and HOLD#/SIO3 are tied high to `/Flash 1V8`.

This is acceptable for standard SPI operation and explains the KiCad ERC warnings about bidirectional pins connected to a power flag. The tradeoff is that Quad SPI/DTR modes are unavailable unless SIO2/SIO3 are routed to the MCU.

### BMM350 CRST implementation

Confidence: high  
Evidence: BMM350 datasheet and U2/C4 net mapping

The analyzer warning that U2 CRST needs a pull-up is a false positive. The BMM350 datasheet requires a 2.2 uF capacitor on CRST. The design has C4 = 2.2 uF from `Net-(U2-CRST)` to GND and places it near U2, about 1.9 mm by analyzer distance and about 2.37 mm center-to-center from U2.

### STM32U375 supply support

Confidence: high  
Evidence: STM32U375 datasheet and schematic/PCB net mapping

The MCU supply arrangement is broadly correct:

- VDD and VDDA are tied to +1V8, within the 1.71 V to 3.6 V operating range.
- VCAP has C12 = 4.7 uF to GND.
- Decoupling capacitors are present near U302.
- NRST is pulled/controlled through Q501, and the PMBT2222AMB pinout matches the intended collector/emitter/base use.

## Analyzer False Positives and Overrides

### U6 VCC no DC path to power rail

Raw finding: schematic `PP-001` and `RS-001` for `/Flash 1V8`  
Disposition: false positive / documentation cleanup

The analyzer does not understand that U1 TPS22916 VOUT is the source for `/Flash 1V8`. The datasheet and net trace confirm that U1 A1/VOUT feeds U6 VCC and the local flash capacitors.

Recommended cleanup:

- Add a PWR_FLAG or improve the U1 symbol pin type/regulator mapping so ERC-style tools understand `/Flash 1V8`.

### AT25_MOSI / AT25_SCK missing I2C pull-ups

Raw finding: schematic `PR-001`  
Disposition: false positive if U5 is operated in SPI mode

The LSM6DSV-family pins are dual-use I2C/SPI pins. Its datasheet states that CS high selects I2C and CS low selects SPI. In this design, U5 has `/LSM_CS`, so SPI use is plausible and no I2C pull-ups are needed on `AT25_MOSI` or `AT25_SCK`.

Firmware contract:

- Keep all chip selects inactive except the selected device.
- Drive U5 CS appropriately so the IMU stays in the intended serial mode.
- Correct the PCB metadata so it consistently names the intended LSM6DSV part.

### KiCad ERC warnings on U6 WP/HOLD tied high

Raw finding: ERC bidirectional pins connected to power output flag  
Disposition: acceptable for standard SPI; update symbols/flags if desired

The flash datasheet says unused WP#/SIO2 and HOLD#/SIO3 must be driven high or pulled high. Tying them to `/Flash 1V8` is correct for standard SPI.

## Datasheet and Library Hygiene

- The shared library path used for this review was `BoardDesigns/libraries/datasheets`.
- U302's datasheet property points at an older absolute path under `hardware/libraries/datasheets/stm32u375ce.pdf`; the actual shared file is under `BoardDesigns/libraries/datasheets/stm32u375ce.pdf`.
- U5 datasheet coverage is complete for the intended `LSM6DSV` part; PCB metadata should be updated from `LSM6DSV16XTR` to `LSM6DSV`.
- No missing MPNs were reported by the schematic analyzer.

## Suggested Before-Fab Checklist

1. Update U5 PCB properties to match the intended `LSM6DSV` part.
2. Document that the fab house supplies panel fiducials for both assembled sides.
3. Rework high-speed/clock return paths and add GND stitching near layer transitions.
4. Add/read-back-verify the STM32 BOOT0 option-byte write in the programming flow.
5. Update the stale schematic pin-map text note.
6. Confirm advanced PCB process assumptions with the intended fab.
7. Review J401 via-in-pad and exposed-pad paste/via treatment with the assembler.
8. Add probe/test access or document connector-based test access.
9. Run fresh ERC, DRC, cross-analysis, and EMC checks after layout edits.
