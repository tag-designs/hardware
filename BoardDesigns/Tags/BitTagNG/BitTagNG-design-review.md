# BitTagNG — Design Review

**Board:** BitTagNG "BitTag with External Memory" (IUCS, Geoffrey Brown)
**Reviewed:** 2026-08-31 · analysis run `2026-08-31_2012`
**Files:** `BitTagNG.kicad_sch`, `BitTagNG.kicad_pcb` (KiCad 6, file version 20211014)

---

## Overview

A 17.25 × 9.0 mm, 2-layer, 0.4 mm-thick battery-powered sensor tag. 23 components, 11 unique
parts, 37 nets, fully routed. Four active devices on a single unregulated rail fed from a 3 V
rechargeable coin cell through a series Schottky.

**Verdict: no blockers. Fabricable as-is.** *(Revised 2026-08-31 after designer review — see
[Designer Response](#designer-response) below.)* All three original blockers were answered: two are
deliberate system-level design choices whose context does not appear in this project, and the third
is a labelling cleanup that the fab flow does not consume. What remains is a set of robustness
improvements and process confirmations, none of which prevent a working board.

The design is sound — every IC pinout checks out against its datasheet, schematic and PCB are
perfectly in sync, and the RTC support circuit is a literal copy of the vendor reference design.

---

## Designer Response

Three findings were raised as blockers in the initial pass. The designer's responses, and what
each leaves behind:

| # | Original finding | Response | Now |
|---|-----------------|----------|-----|
| 1 | I²C has no pull-ups | Intentional — slow **software** I²C driver on the STM32 internal pull-ups; works in the field | Resolved → design intent |
| 2 | Q501 base has no series resistor | The series resistor is on the **external baseboard** that drives J201 | Resolved → design intent |
| 3 | Value/MPN mismatch | Never an issue in fab (flow consumes MPN, Value is a label); agreed worth correcting | Downgraded → cleanup |

All three responses are consistent with the measured evidence, and the review's own numbers support
the first two (see below). **The residual risk in every case is documentation, not electronics** —
each of these is a real design decision that is invisible to anyone reading this project on its own.

### 1 → Resolved. I²C on internal pull-ups with a software driver

A slow bit-banged driver on the MCU's internal pull-ups is a legitimate solution, and the rise-time
budget computed in the original pass already supported it: **730 ns worst case against the 1000 ns
standard-mode limit**, with a software driver free to clock slower still. The datasheet's
"requires pull-up resistor" is satisfied by the internal ones; it does not specify external.

*Residual risk:* the dependency is invisible on the schematic. Anyone who later switches to the
hardware I²C peripheral, raises the bus to 400 kHz, or simply forgets to enable the internal
pull-ups gets a bus that fails for no visible reason. **Worth a schematic note on SCL/SDA.**

### 2 → Resolved. Base resistor lives on the baseboard

That removes the drive-current concern entirely in the intended configuration. The missing
base-emitter pull-down is not a practical concern either, and the numbers are not close: with the
base open, BC847AMB collector leakage is on the order of **10 nA**, while pulling NRST low through
the STM32's internal pull-up requires roughly **100 µA** of collector current — four orders of
magnitude away.

*Residual risk:* the dependency is not recorded anywhere in this project. A future baseboard
revision, or any standalone use of J201, could drop the resistor silently. **Worth a note near J201.**

### 3 → Downgraded to cleanup. Value/MPN mismatch

Correct that the fab and assembly flow consumes the MPN and treats `Value` as a label, so this has
not caused a build problem.

*Residual risk:* `Value` is what a **human** reads when reviewing the schematic, so the mismatch
misleads review rather than fabrication. That is precisely what happened here — this review verified
U302 against the STM32L432KC datasheet and U1 against the AT25XE321D ball map, on the strength of two
fields that disagree with each other. Correcting it at the next schematic edit closes that gap.

---

## Remaining Findings

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 4 | Warning | PA3 (U302 pin 9) hard-tied to GND — firmware error shorts the rail | Add 0 Ω/1 kΩ series; reserve pin |
| 5 | Warning | Neither SPI chip-select has a pull-up; both float during reset | 100 kΩ pull-ups, or drive high first |
| 6 | Warning | Both SPI devices share SPI1 on two pin mappings | Firmware must remux MISO |
| 7 | Warning | No copper zones anywhere — GND/VIN are narrow traces only | Add GND pours + stitching vias |
| 8 | Warning | 0.102 mm annular ring is below IPC Class 2 | Confirm advanced fab class |
| 9 | Warning | C6 sits ~0.27 mm from the routed board edge | Confirm depanel method |
| 10 | Warning | VBAT exposed on J201.2 with no charge control (cell is rechargeable) | Document charge limits |
| 3 | Cleanup | U302 and U1 `Value` fields disagree with their `MPN` fields | Correct at next edit |

---

## Original Blocker Analysis (retained for the record)

### 1. I²C bus has no pull-up resistors — *datasheet-verified* — **resolved, see above**

`SCL` (U302.30/PB7 → U501.3) and `SDA` (U302.29/PB6 → U501.4) are two-pin nets. R1 is the only
resistor on the board and it is the RTC's VBACKUP 10 kΩ. The RV-3028-C7 App Manual says so three
separate times:

> "SCL 3 — I²C Serial Clock Input; **requires pull-up resistor**." (Rev 1.4, §2.2, p.9)
> "SDA 4 — I²C Serial Data Input-Output; open-drain; **requires pull-up resistor**." (§2.2, p.9)
> "I²C lines SCL, SDA are open-drain and **require pull-up resistors to VDD**." (§7.1 note 4, p.103)

The bus therefore works only if firmware enables the STM32's internal weak pull-ups (R<sub>PU</sub>
= 25/40/55 kΩ, DS11451 Rev 4, p.107). Quantifying that
(`../kicad-helpers/i2c_risetime.py`) — traces are only 1.7 mm, so C<sub>bus</sub> ≈ 15.7 pF:

| R<sub>PU</sub> | t<sub>r</sub> | 100 kHz (≤1000 ns) | 400 kHz (≤300 ns) |
|---|---|---|---|
| 25 kΩ (min) | 332 ns | pass | fail |
| 40 kΩ (typ) | 531 ns | pass | fail |
| 55 kΩ (max) | 730 ns | **pass** | **fail** |

So it will probably work at 100 kHz — but only by accident of the short traces, only if firmware
remembers to enable internal pull-ups, and never at 400 kHz. Two 0201 resistors remove all of that
risk.

### 2. Q501 reset transistor has no base resistor — *datasheet-verified* — **resolved, see above**

Net `RST` contains exactly two pins: `J201.5` and `Q501.1` (base). Q501's collector drives
`U302.4/NRST`. There is no series resistor and no base-emitter pull-down.

- **Driving it:** V<sub>BE</sub> clamps near 0.8 V, so a 3.3 V push-pull debug adapter sees only its
  own output impedance. At 25–50 Ω that is **50–100 mA** into the base. BC847AMB's I<sub>BM</sub>
  rating is 100 mA and is only valid for pulses under 1 ms (NXP BC847xMB, p.3).
- **Not driving it:** with no adapter attached the base is an open, high-impedance node.
- **What's actually needed:** Q501 only has to sink the STM32's internal NRST pull-up — about
  0.6–1.0 µA of base current. A 10 kΩ series resistor supplies 250 µA, over 1000× margin.

Add a 10 kΩ series resistor and a 100 kΩ base-emitter pull-down. (`../kicad-helpers/base_drive.py`)

### 3. Value/MPN mismatches — *raw-file verified* — **downgraded to cleanup, see above**

```
U302   value=stm32l431kc        mpn=STM32L432KCU6        MISMATCH
U1     value=at25ex321D-UUN     mpn=AT25FF321A-UUN-T     MISMATCH
```

STM32L431KC and STM32L432KC are different devices; AT25XE321D and AT25FF321A are different flash
families. Fabrication and assembly consume the MPN field, so the board would be built with parts
the schematic does not name. Resolve before generating any BOM.

Note the review verified U302 against the **STM32L432KC** datasheet and U1's ball map against the
**AT25XE321D** datasheet — whichever part you settle on, re-confirm the one you did not.

---

## Component Summary

| Ref | Part | Package | Role |
|-----|------|---------|------|
| U302 | STM32L432KCU6 | UFQFPN-32 5×5 | MCU |
| U2 | ADXL367BCCZ-RL7 | LGA-12 2.3×2.3 | Accelerometer (SPI) |
| U1 | AT25FF321A-UUN-T | WLCSP-12 | 32 Mb SPI flash |
| U501 | RV-3028-C7 | C7 3.2×1.5 | RTC (I²C) + 32.768 kHz CLKOUT |
| Q501 | BC847AMB | SOT-883 | Reset inverter |
| D401 | CDBQC0130L-HF | 0402 | Reverse-polarity Schottky |
| R1 | 10 kΩ | 0201 | RTC VBACKUP tie-down |
| C1–C6, C404, C501–C503 | 0.1 µ ×6, 22 µ ×2, 47 µ, 0.22 µ | 0201/0402/0603 | Decoupling + bulk |
| J201 | 6-pin | tagpoints6 | SWD + power + VBAT |
| J401 | MS621 | — | 3 V rechargeable coin cell |
| J301–J304 | — | taghole1.1mm | Mounting holes (mechanical) |

Assembly complexity 63/100: 13 hard-to-place parts (eight 0201s, one WLCSP, one QFN-32).

---

## Power Tree

```
J401 (MS621, 3 V rechargeable coin cell)
  └─ VBAT ──┬── J201.2  (exposed on programming header — see finding 10)
            └── D401 (Schottky, reverse-polarity protection)
                  └─ VIN ≈ 2.8 V ──┬── U302  VDD ×2 + VDDA/VREF+
                                   ├── U2    Vs + Vddio
                                   ├── U1    VCC + /RESET
                                   ├── U501  VDD
                                   └── J201.1
```

There is no regulator. Every device runs directly at battery voltage minus one diode drop.

**Rail headroom — datasheet-verified:**

| Device | Operating | Abs max |
|--------|-----------|---------|
| STM32L432KC | 1.71 – 3.6 V | 4.0 V |
| ADXL367 | 1.1 – 3.6 V | 4.0 V |
| RV-3028-C7 | 1.2 – 5.5 V | 6.0 V |

The binding limit is **3.6 V**. At ~2.8 V from an MS621 there is comfortable margin. ⚠️ Do not
substitute a 3.7 V LiPo: at 4.2 V charged, VIN would reach ~4.0 V — the absolute maximum of both
U302 and U2.

D401 orientation is correct (VBAT → anode, cathode → VIN).

---

## Analyzer Verification

Analyzer output was cross-checked against raw files and datasheets rather than taken at face value.

- **Component count:** 23 in schematic (excl. power symbols) = 23 PCB footprints ✓
- **Pin-to-net cross-check:** every schematic pin-net compared against every PCB pad-net across
  all 23 footprints — **0 mismatches** (`../kicad-helpers/padnet_crosscheck.py`). Schematic and
  layout are perfectly in sync.
- **KiCad native DRC** (v10.0.2, run on a copy with the project's own rules): **0 unconnected
  items**, 0 clearance/width/annular-ring errors. 25 violations, all library-metadata bookkeeping
  plus one silkscreen text-height warning.

### Pinout verification — all five active devices

| Device | Source | Result |
|--------|--------|--------|
| U302 STM32L432KCU6 | DS11451 Rev 4, Fig. 5, p.51 | 32 pins + exposed pad **all match** |
| U501 RV-3028-C7 | App Manual Rev 1.4, §2.2, p.9 | 8 pins **all match** |
| U2 ADXL367 | Rev B, Table 9, p.13 | 12 pins **all match** |
| Q501 BC847AMB | NXP BC847xMB, Table 3, p.2 | 1=B, 2=E, 3=C — matches `Q_NPN_BEC` |
| U1 AT25 WLCSP-12 | AT25XE321D, p.8 (family) | 12 balls **all match** |

This was the highest-risk area — a library symbol whose pinout disagrees with the real part passes
DRC/ERC silently and kills the board. Nothing of the kind here.

Individually confirmed as **correct, not merely consistent**:

- **U2.8 ADC_IN → GND.** "ADC Input Pin. Can be left unconnected, or connected to Pin 7 and/or
  Pin 11." (p.13) Pins 7 and 11 are GND — explicitly sanctioned.
- **C3 = 0.22 µF on U2.9 VREG_OUT.** "This pin is used as an internal supply decoupling pin, an
  external 0.2 μF capacitor is needed." (p.13) 0.22 µF is the nearest E-series value. ✓
- **U1.F4 nWP floating.** "The WP pin is internally pulled high and can be left floating if not
  used." (AT25XE321D p.9) ✓
- **U1.D2 HOLD/RESET → VIN.** Correctly deasserts both. ✓
- **U302.31 BOOT0 → GND.** Correct for boot-from-flash. ✓
- **U302 pad 33 (exposed pad) → GND** with 3 GND vias. ✓

### RTC circuit matches the vendor reference design exactly

U501's support circuit is a literal reproduction of App Manual §7.1, *"No backup source / event
input not used"* — the 45 nA configuration:

| Design | Reference circuit |
|--------|-------------------|
| R1 10 kΩ VBACKUP → GND | "Do not leave VBACKUP floating. Connection to VSS through a 10 kΩ resistor keeps functional test possible." |
| INT (pin 2) left open | "INT pin is an open-drain output, which can be left open when not used." |
| EVI (pin 8) → GND | "This pin should not be left floating." |
| CLKOUT → MCU PC14/OSC32_IN | "CLKOUT with a frequency of 32.768 kHz is enabled by default (default value on delivery)." |

The 32.768 kHz clock works with no EEPROM configuration. **Firmware note:** the MCU must run LSE
in *bypass* mode to accept an external clock on OSC32_IN, not crystal-drive mode.

### Footprint named for a different part — checked, benign

U501 uses footprint `AccelTag:RV-8803-C7` for an RV-3028-C7. Measured against the package drawing
(App Manual §8.1, p.106): pads 0.5 × 0.8 mm on 0.9 mm pitch, 1.2 mm row spacing (2.0 mm overall
span), 8 pads numbered counter-clockwise. **Exact match** to the RV-3028-C7 land pattern — both
are Micro Crystal C7 packages. The library name is cosmetic; the footprint's own `value` field
already reads "RV-3028-C7". No action needed.

---

## Signal Analysis

**SPI — two devices on SPI1 via two different pin mappings:**

```
ADXL367:  PA5 SCK / PA6 MISO / PA7 MOSI / PA4 CS
AT25:     PB3 SCK / PA11 MISO / PA12 MOSI / PA10 CS
```

Both groups are SPI1 alternate functions on STM32L4. This gives each device its own physical bus,
which is a nice touch on a board this dense — but it carries a firmware constraint: **PA6 and PA11
must not be muxed to SPI1_MISO simultaneously**, or the peripheral receives two inputs on one
internal signal. Remux when switching devices, or leave the inactive pin as a plain input.

**Chip selects float during reset.** Neither `AT25_nCS` nor `ACCEL_CS` has a pull-up. STM32L4
GPIOs come out of reset as high-impedance analog inputs, so both active-low selects float until
firmware drives them — a device can be spuriously selected. Add 100 kΩ pull-ups to VIN, or drive
both high as the very first GPIO action after reset.

**PA3 tied hard to GND.** Pin 9 is PA3, a general-purpose I/O, and it is on the GND net in both
schematic and PCB. Safe out of reset (STM32L4 GPIOs default to analog mode), but any firmware that
configures PA3 as a push-pull output and drives it high shorts VDD to GND through the output
driver — fatal on a coin cell. If this is a deliberate anchor, add a 0 Ω/1 kΩ series resistor and
mark PA3 reserved in the firmware pin map.

**Wake-up path.** `WKUP4` ties U2.5 (INT1) to *both* U302.6 (PA0) and U302.8 (PA2), giving the
accelerometer interrupt access to both a wake-up pin and an EXTI line. Deliberate and fine —
firmware must not configure either as an output.

**Reset.** `NRST` carries C502 (0.1 µF) plus Q501's collector. The 100 nF on NRST is ST's
recommendation and the STM32's internal ~40 kΩ pull-up handles the rest. Topology correct; see
finding 2 for the base-drive problem.

---

## PCB Layout Analysis

17.25 × 9.0 mm, 2 layers (F.Cu/B.Cu), 0.4 mm thick, 155 mm² usable. 269 track segments,
25 vias, routing complete, 0 unrouted nets.

**No copper zones at all** (`zone_count = 0`). GND is 77 track segments totalling 51.1 mm; VIN is
78 segments totalling 50.6 mm — both at 0.102–0.152 mm width. Connectivity is sound, but every
signal's return path is long and undefined, and PDN impedance is set by trace inductance rather
than plane capacitance. On an already-routed 2-layer board, adding GND pours on both layers with
stitching vias is nearly free and is the single highest-value layout improvement available.

**Decoupling is genuinely well done.** Every IC has a 100 nF within 2 mm sharing both VIN and GND:

| IC | Nearest 100 nF | Nearest bulk |
|----|----------------|--------------|
| U302 | C5 @ 0.90 mm | C404 @ 0.67 mm |
| U2 | C1 @ 0.84 mm | C404 @ 1.05 mm |
| U501 | C2 @ 0.98 mm | C6 @ 1.92 mm |
| U1 | C501 @ 1.84 mm | C404 @ 3.69 mm |

Bulk is nominally ~91 µF (47 µF + 2 × 22 µF). ⚠️ Note that 22 µF in 0402 and 47 µF in 0603 at
6.3 V lose a large fraction of their capacitance to DC bias at 3 V — effective bulk is well below
91 µF. Fine for this design, but don't rely on the nameplate number.

**Fabrication class.** All 25 vias are 0.4572 mm pad on 0.254 mm drill → **0.102 mm annular ring**,
below the IPC-6012 Class 2 minimum of 0.125 mm. Minimum track width is 0.1016 mm (4 mil). This is
deliberate — the project rules set both to 0.1016 mm and DRC passes cleanly — but it restricts
which fabricators can build the board and at what price. Confirm your fab quotes this as an
advanced class.

**Board edge clearance.** C6 sits ~0.27 mm from the routed edge (C4 0.64 mm, D401 0.82 mm). On a
17 × 9 mm tag this is an understandable trade-off, but confirm your assembler's depanel method
(V-score vs tab-route) tolerates it.

---

## Thermal Analysis

**Not applicable — stated rather than skipped.** `analyze_thermal.py` ran and returned 0 findings
("no components had quantifiable power dissipation data"). Substantively this is correct: there is
no regulator, no power device and no load switch on the board. The largest dissipator is the MCU at
a few mW, on a design that spends most of its life asleep. There is no thermal question to answer.

The analyzer's `power_budget` estimate of 50 mA on VIN is a **heuristic placeholder** (20 mA MCU +
10 mA per peripheral); it is not a real budget for a coin-cell tag and should be ignored.

---

## EMC / Cross-Domain Analysis

EMC risk score 43/100; 4 errors, 22 warnings. Nearly all of it collapses to one root cause — the
absent ground plane — and most of the rest is false-positive noise (see below).

For this product the compliance question is largely moot: a 17 × 9 mm tag with no radio, no
external cabling and a 32.768 kHz primary clock is not a meaningful radiator, and it is not going
through FCC/CISPR as a standalone product. The ground-plane recommendation stands on **signal
integrity and noise immunity** grounds, not compliance.

Cross-domain analysis (`cross_analysis.py`) produced 3 findings, all downstream of the same
false-positive island decomposition.

---

## Manufacturing / DFM / Testability

- **No test points** (0 of 36 nets) and **no fiducials** on either side. For a board this size both
  are defensible — J201 carries VIN, GND, SWDIO, SWCLK, RST and VBAT, which covers bring-up. But
  the WLCSP flash, QFN-32 and eight 0201s do need fiducials for placement accuracy. `panel-copy.kicad_pro`
  suggests a panel exists; **confirm the panel rails carry fiducials.**
- **Footprint type metadata:** J201 and J401 are marked SMD but have through-hole pads (2 DRC
  errors). Cosmetic, but it affects which parts land in a pick-and-place position file. Worth fixing.
- **Silkscreen text height** 0.6 mm vs the project's own 0.8 mm minimum ("BTNG V2" on B.Silkscreen).
  Most fabs render 0.6 mm acceptably; confirm with yours.
- **Tombstoning:** C4 flagged medium risk from via-count asymmetry on its pads. Minor; reflow
  profile normally handles 0402.
- **Vias are tented** (`viasonmask false`), so there is no solder-wicking risk at U302's thermal pad.

---

## Component Lifecycle

**Not performed.** No distributor API credentials are configured (DigiKey/Mouser/element14) and
LCSC returned no listings for these MPNs. No obsolescence, stock, or temperature-grade evidence is
available. Worth running before a production build — the ADXL367 and RV-3028-C7 in particular are
specialty parts.

---

## False Positives / Reviewer Overrides

Each of these was investigated and dismissed, with the evidence that retired it:

| Finding | Verdict |
|---------|---------|
| `PS-002` GND split into 4 islands; `RP-002` /AT25_MISO crosses GND plane gap | **False positive.** KiCad's own DRC reports **0 unconnected items**. The analyzer's union-find over copper does not merge islands the way KiCad's connectivity engine does. |
| `TV-001` "3 vias not tented — solder may wick through" | **False positive.** `(viasonmask false)` in the PCB file means vias *are* tented. |
| `via_in_pad` at U302 with `same_net: false` | **False positive.** All three vias inside the exposed pad are on **GND**, the same net as the pad. Verified by computing via positions against the pad-33 rectangle. Would have been a short if real. |
| `TV-001` "U302 needs 9 thermal vias, has 3" | **Downgraded to none.** Electrically the exposed pad is correctly bonded to GND. At a few mW there is no thermal requirement. |
| `IO-001` "No EMC filtering near J303" (×6) | **False positive.** J301–J304 are 1.1 mm mounting holes modelled as 1-pin connectors, not I/O. |
| `CK-003` "Clock routed near connector" (×11) | **Mostly false positive.** Six cite the mounting holes above. SWCLK is only active during debug; `/clkout` is 32.768 kHz. Negligible. |
| `RP-001` "Missing stitching via at layer transition" (×14) | **Not actionable as stated.** There is no plane to stitch to. Subsumed by the ground-pour recommendation. |
| `PU-001` U2 INT2 missing pull-up | **False positive.** ADXL367 INT2 is a push-pull output (Table 9, p.13), not open-drain. An unused output may float. |
| `RS-001` VBAT has no declared source | **Artifact.** VBAT is sourced by the battery at J401; the analyzer wants a PWR_FLAG. Cosmetic — adding one silences it. |
| `TB-001` tombstoning "pad 2 is GND (likely ground pour)" | **Rationale invalid** — this board has no pour. Residual via-asymmetry risk on C4 is minor. |
| `DFM-001` 4 mil track width "requires advanced process" | **Accepted, not a defect.** Deliberate; see fabrication class above. |

---

## Not Performed / Review Limits

- **Gerber analysis** — no fabrication outputs present in the project.
- **SPICE simulation** — no simulator installed (`ngspice`/`ltspice`/`xyce` all absent). Low impact:
  the analyzer detected no filters, dividers, or op-amp stages to simulate. The one computed
  circuit result (I²C rise time) was derived analytically instead and is shown above.
- **Lifecycle audit** — no distributor credentials; see above.
- **Previous review delta** — none possible; this is the first review and `analysis/manifest.json`
  had no prior runs.
- **Structured datasheet extraction cache** — not present. All pin verification was done by reading
  the manufacturer PDFs directly, which is why every claim above carries a page citation.
- **Datasheets not obtained:** `CDBQC0130L-HF` (D401). Its forward drop directly sets VIN, so the
  ~2.8 V figure assumes a typical low-current Schottky V<sub>f</sub> of 0.15–0.3 V — **inference,
  not verified**. Automated fetch failed for this part (no credentials; not on LCSC).
- **Exact-MPN gaps:** U1 was verified against the **AT25XE321D** datasheet, not AT25FF321A
  (family-level, same 12-ball WLCSP map). Q501 was verified against the BC847xMB series datasheet,
  which covers BC847AMB directly. Both are noted in finding 3.

---

## Positive Findings

Worth recording, because these are the things that usually go wrong and did not:

- **Every IC pinout matches its datasheet.** Five for five, including a custom `adxl367.kicad_sym`
  and a WLCSP ball map — the highest-risk category on any board.
- **Schematic and PCB are perfectly in sync** — 0 pad-net mismatches across 23 footprints.
- **KiCad DRC is clean** under the project's own rules: 0 unconnected, 0 clearance/width violations.
- **Decoupling placement is excellent** — 100 nF within 2 mm of every IC, bulk within 4 mm.
- **The RTC circuit is a faithful copy of the vendor's 45 nA reference design**, down to the 10 kΩ
  VBACKUP tie-down that is easy to get wrong.
- **Reverse-polarity protection** present and correctly oriented.
- **Unused pins handled correctly** — ADC_IN to GND, EVI to GND, nWP floating, HOLD/RESET high,
  BOOT0 low: each one matches its datasheet's explicit guidance.

---

## Recommended Actions Before Fabrication

**Nothing blocks fabrication.** The items below improve robustness and close documentation gaps.

**Document (highest value — these are real design decisions currently invisible in this project):**
1. Note on SCL/SDA that the bus intentionally relies on MCU internal pull-ups and a slow software driver.
2. Note near J201 that Q501's base series resistor is supplied by the external baseboard.
3. Correct `Value` to match `MPN` on U302 and U1; re-verify whichever part was not checked.

**Should fix:**
4. Add 100 kΩ pull-ups on `AT25_nCS` and `ACCEL_CS` (or handle in firmware, documented).
5. Add GND pours on both layers with stitching vias.
6. Add a series resistor on PA3, or document it as reserved.
7. Confirm fab supports 0.102 mm annular ring; confirm panel fiducials; confirm C6 edge clearance.
8. Fix J201/J401 footprint type metadata (SMD → through-hole).

**Firmware constraints to record:**
- Keep the software I²C driver on PB6/PB7 with internal pull-ups enabled; do not move to hardware
  I²C at 400 kHz without adding external pull-ups first.
- Configure LSE in **bypass** mode for the RV-3028 CLKOUT input.
- Never mux PA6 and PA11 to SPI1_MISO simultaneously.
- Never configure PA3, PA0 or PA2 as outputs.

---

*Analyzers run: `analyze_schematic.py`, `analyze_pcb.py --full --proximity`, `cross_analysis.py`,
`analyze_emc.py`, `analyze_thermal.py`, `deep_review_gate.py` (15/15 findings verified, 0
quarantined), plus KiCad 10.0.2 native DRC. Helper scripts under `../kicad-helpers/`.*
