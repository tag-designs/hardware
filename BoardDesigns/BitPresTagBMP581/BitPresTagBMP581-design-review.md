# BitPresTagBMP581 — Design Review

**Date:** 2026-09-04 (re-verified after design update)
**Reviewer:** automated review via `kicad-happy` suite + datasheet verification
**Analysis run:** `analysis/2026-09-04_1900` (initial review: `analysis/2026-09-04_0738`)
**Board:** 18.0 × 10.0 mm, 4-layer, 0.4 mm thick, 28 footprints, 42 nets
**Prior review:** none (first review of this board)

---

## Update — 2026-09-04, design revision verified

The designer acted on the review. Re-ran the full pipeline against the updated files:

| Change | Verified |
|---|---|
| **C8 = 220 nF** (0201, `GRM033R60J224ME15D`) on U2.9 `VREG_OUT` → GND | ✅ Closes finding 1. 220 nF is the nearest standard value to the datasheet's 0.2 µF |
| **R2 = 10 Ω** (0201, `RC0201FR-0710RL`) in series in the sensor supply | ✅ Closes the inrush half of finding 4. Wired PB1 → R2 → C3/C5/U3.4/U3.8 — decoupling correctly on the *load* side of the resistor |
| **U3 pin 9 no-connect flag** added | ✅ Closes finding 6 |
| **U2 pins 7/11 `GND`** pin type `power_out` → `power_in` | ✅ Clears both ERC `pin_to_pin` errors |
| **`track_not_centered_on_via`** re-enabled `ignore` → `error`, violation fixed | ✅ DRC clean under the stricter rule |
| **`single_global_label`** `ignore` → `warning` | ✅ |
| **7 `power:+2V5` symbols → `power:VCC`**, `VIN` global labels retained | ✅ Closes finding 2 — see below |

**Result: KiCad DRC 0 violations / 0 unconnected. KiCad ERC 0 violations (was 6).
`padnet_crosscheck`: 28 footprints, 0 mismatches.**

R2 is the better fix than the one I proposed as a fallback: it satisfies the BMP585's
normative *"a 10 Ohm resistor must be connected in series to the power supply"* **by
construction**, rather than leaving compliance resting on an inferred GPIO output impedance
and a firmware speed setting. The 2.6 mV drop at the 260 µA peak is immaterial.

**The rail relabel is a clean outcome.** `VCC` for the 7 power symbols with the `VIN` global
labels kept is a better answer than either of the options I offered:

- **The phantom rail is gone.** The analyzer previously reported `+2V5 = 2.5 V` beside the real
  rail; it now reports `VCC` with **no voltage** — no false claim anywhere in the output.
- **Zero churn.** Because the netlist still resolves the net to `VIN`, the PCB net name is
  unchanged, no update-from-schematic was needed, and no copper moved. Confirmed: the PCB rail
  nets are still `VBAT` and `VIN`, and the In1.Cu `VIN` zone is untouched (single fill region).
- **The dual name is now meaningful rather than accidental** — `VCC` is the internal rail name,
  `VIN` the name the surrounding environment uses (the J201 pin 1 / harness-facing name). That
  makes the retained `multiple_net_names` ERC exclusion the *correct* tool rather than a
  workaround: it documents a deliberate alias. It should be kept, not "fixed" by deleting one
  of the names.

**One item remains open from this revision:** the switched sensor-supply node is an unnamed net
(`__unnamed_13`) — see finding 10.

---

## Verdict

**As of the 2026-09-04 revision, the board is electrically clean and fabrication-ready.**
Every electrical defect found by this review has been fixed and re-verified.

KiCad DRC is clean (0 violations, 0 unconnected) under the tightened rules *including* the
re-enabled `track_not_centered_on_via`, KiCad ERC is clean (0 violations, down from 6), all
28 footprints pass a schematic-to-PCB pad/net cross-check with zero mismatches, and every
pinout checked against a manufacturer PDF is correct — including the three most dangerous
(the transistor, the 12-ball WLCSP flash, and the BMP585).

What remains is **documentation and hygiene, not electrical**: an unnamed switched-supply net,
two `Value`/`MPN` disagreements, and one open question about where the reset transistor's base
resistor lives. The rail-label defect is fixed — the schematic no longer claims a voltage the
rail does not have.
The board's `.kicad-happy.json` — which had described a completely different board — has been
rewritten, and the pin map it now carries records the firmware contracts: all three serial
buses have hardware support, but on three *different* peripherals (USART2 synchronous mode,
SPI1 and SPI3).

### The uncommitted rule tightening is verified good

The working tree has uncommitted changes to `.kicad_pro` that tighten the design rules, plus
a fab package exported 2026-09-04 07:36. I verified all of it:

| Rule | Was | Now | Verified |
|---|---|---|---|
| `min_copper_edge_clearance` | 0.0 mm | **0.3 mm** | DRC clean; In1/In2 copper measures 17.399 × 9.399 mm inside an 18 × 10 mm outline — exactly 0.3 mm inset on all sides |
| `min_via_annular_width` | 0.1016 mm | **0.1524 mm** | all 39 vias measure exactly 0.1524 mm |
| via diameter / drill | 0.4572 / 0.254 mm | **0.5048 / 0.2 mm** | board and shipped drill file both agree (0.2007 mm tool) |

The old 0.4064/0.2032 and 0.4572/0.254 via entries were removed and a single 0.5048/0.2
size now applies across the Default, MEDIUM and WIDE net classes. **DRC passes with zero
violations under the tightened rules.** This is a straight improvement in fabricability and
should be committed.

---

## Findings

| # | Status | Item | Summary |
|---|---|---|---|
| 1 | ✅ **Fixed** | U2 pin 9 | `VREG_OUT` had no cap; **C8 = 220 nF added** |
| 2 | ✅ **Fixed** | Schematic-wide | Rail was drawn as `+2V5`; **now `VCC`**, with `VIN` kept as the environment-facing alias |
| 3 | Info | U302 / U2 | ADXL367 runs on **USART2 synchronous mode**, not an SPI peripheral — firmware config note |
| 4 | ✅ **Fixed** / ⚠️ | U3 / PB1 | Inrush: **R2 = 10 Ω added**. Back-power sequencing remains a firmware contract |
| 5 | ⚠️ **Open** | U1, U302 | `Value` names a different device than `MPN` on two parts |
| 6 | ✅ **Fixed** | U3 pin 9 | `L/M` is a lasermarking pad; **no-connect flag added** |
| 7 | ❓ **Question** | Q501 | Reset transistor base has no series resistor, and this board has no baseboard |
| 8 | Info | U1 | CS relies on PA15 internal pull-up; datasheet suggests 10 kΩ for the ramp window |
| 9 | ◐ **Partly fixed** | U2, U501, Q501 | **U2 GND pin types fixed**; U501 CLKOUT/SDA/GND types and the unmapped `Device` library remain |
| 10 | ⚠️ **New** | U3 supply node | The switched sensor rail (PB1 → R2 → U3) is an **unnamed net** |

---

### 1. **Error** — U2 `VREG_OUT` is missing its required decoupling capacitor

ADXL367 pin 9 (`VREG_OUT`) is a single-pin net (`__unnamed_15`) with nothing attached.

> **ADXL367 datasheet, pin description table, footnote 1:** "VREG_OUT … Internally Regulated
> Voltage. This pin is used as an internal supply decoupling pin, **an external 0.2 μF
> capacitor is needed**."

This is the only genuinely missing required external on the board — every other IC supply pin
has local 0.1 µF decoupling within ~1–2 mm. `VREG_OUT` is the output of the accelerometer's
internal LDO, which is what the part's "internal power supply regulation for high PSRR"
feature depends on. Unbypassed, that regulator is unstabilised and supply noise couples
into the measurement.

**✅ Fixed 2026-09-04.** `C8 = 220 nF` (`GRM033R60J224ME15D`, 0201) now connects U2 pin 9 to
GND. 220 nF is the nearest standard E-series value to the specified 0.2 µF — correct choice.
Verified in the netlist: `C8.1` and `U2.9 (VREG_OUT)` share a net, `C8.2` is on GND.

---

### 2. ✅ **Fixed** — the supply rail was labelled `+2V5`; it is now `VCC`

**Original problem.** The schematic carried **7 `power:+2V5` symbols and zero `VIN` power
symbols**. The net resolved to `VIN` only via two global labels, so KiCad reported
`multiple_net_names`. There is no regulator in the BOM — the rail is:

```
J401 battery ──> D401 (CDBQC0130L-HF Schottky) ──> rail ──> everything
```

so it tracks the cell (~3.1 V fresh, falling toward ~1.9 V at end of life) and was never a
regulated 2.5 V. Nothing was electrically wrong — the nets were already merged — but the label
asserted a voltage the rail does not have, and that false claim had already propagated into the
board's config as a `+2V5: 2.5` rail-voltage override.

**✅ Resolved 2026-09-04.** The 7 symbols are now `power:VCC`, and the 2 `VIN` global labels
were deliberately retained because `VIN` is the name the surrounding environment uses. Verified:

| Check | Before | After |
|---|---|---|
| Analyzer `power_rails` | `+2V5 = 2.5 V` (false) alongside `VIN = 2.85 V` | **`VCC` = no voltage**, `VIN = 2.85 V` |
| Power symbols | 7 × `power:+2V5` | 7 × `power:VCC` |
| Netlist net name | `VIN` | `VIN` (unchanged) |
| PCB net name / zones | `VIN`, In1.Cu zone | **unchanged** — no update-from-schematic, no copper moved |
| ERC | `multiple_net_names` warning | excluded, and now *correctly* so |

This is a better outcome than either option I suggested. `VCC` is a stock symbol, so no custom
library work was needed; it makes **no numeric claim**, which was the entire defect; and because
the netlist name stayed `VIN`, the change cost nothing downstream — the PCB rail nets are still
`VBAT` and `VIN`, and the In1.Cu `VIN` plane is untouched (still a single fill region).

**On keeping both names.** The retained `multiple_net_names` exclusion is now the right tool
rather than a workaround. `VCC` is the internal rail name; `VIN` is the environment-facing name
(J201 pin 1, the harness). A deliberate alias documented by an exclusion is exactly what
exclusions are for — this should be **kept**, not "fixed" later by deleting one of the names.
The config records that so a future review does not undo it.

**One thing no label can carry:** the voltage *range*. A schematic text note is still worth
adding, and the same text now lives in the config under `analysis.power_rails.notes`:

```
VCC (= VIN) = VBAT - D401 Vf.  Unregulated; tracks the cell.
~3.1 V fresh -> ~1.9 V end of life.  All parts rated to 1.71 V min (STM32L432KC binding).
```

**Family note:** BitTagNG still carries the identical 7 `power:+2V5` symbols. The same
one-symbol swap applies there, with the same phantom-rail benefit.

---

### 3. **Info** — the ADXL367 runs on USART2 synchronous mode, not an SPI peripheral

> **Correction.** An earlier draft of this review claimed this bus had no hardware option and
> had to be bit-banged. That was wrong, and the error was mine: I searched ST's alternate-function
> table only for function names containing "SPI". PA2/PA3/PA4 are
> `USART2_TX` / `USART2_RX` / `USART2_CK`, all on **AF7** — a complete hardware synchronous-serial
> group. No bit-banging is required.

All three buses have hardware support; the peripheral assignment is what matters:

| Device | Pins | Peripheral | AF |
|---|---|---|---|
| U2 ADXL367 | PA4 / PA2 / PA3 (+ PA1 CS) | **USART2 synchronous mode** CK/TX/RX | AF7 |
| U3 BMP585 | PA5 / PA12 / PA11 | **SPI1** SCK/MOSI/MISO | AF5 |
| U1 AT25 flash | PB3 / PB5 / PB4 | **SPI3** SCK/MOSI/MISO | AF6 |

The STM32L432 datasheet is explicit that this is a supported use:

> **DS11453 §3.x:** "USART1 and USART2 also provide Smart Card mode (ISO 7816 compliant) and
> **SPI-like communication capability.**" … "All USART interfaces can be served by the DMA
> controller." … "able to communicate at speeds of up to 10 Mbit/s."
>
> **Table 11, STM32L432xx USART/LPUART features:** Synchronous mode — USART1 X, **USART2 X**,
> LPUART1 not supported

So the pin choice is deliberate and correct, not a compromise: `USART2_CK` on PA4 is the clock,
`USART2_TX` on PA2 is MOSI, `USART2_RX` on PA3 is MISO, and PA1 — used here as a GPIO chip
select — even carries `USART2_RTS` (AF7) and `USART2_DE` as an additional function. It is
DMA-capable, so FIFO burst reads cost no more CPU time than a true SPI peripheral would.

This also resolves the three SPI1 collisions `stm32_pinmap.py` reports between the `LPS_*` and
`AT25_*` groups: with the accelerometer on USART2, the pressure sensor takes SPI1 (AF5) and the
flash takes SPI3 (AF6), and nothing contends. **All three buses can be live simultaneously.**

**Firmware notes**, since a USART in synchronous mode is configured differently from an SPI peripheral:

- Set **MSB-first** (`CR2.MSBFIRST`) — the ADXL367 is MSB-first, while a USART defaults to LSB-first.
- Match **CPOL/CPHA** (`CR2.CPOL`, `CR2.CPHA`) to ADXL367 SPI mode 0.
- Set **`CR2.LBCL`** so the clock pulse for the last data bit is actually emitted — the classic
  omission that makes the final bit of every byte fail.
- Confirm the clock-gating behaviour around frame start/stop bits against **RM0394**
  (not on disk here) before first bring-up.
- Drive PA4 actively. The ADXL367 **selects I²C mode if `SCLK` is tied low**, so it must never
  be strapped or left pulled low at reset.

**Note on BitTagNG**, the working reference: it solves the same problem differently, putting the
accelerometer on PA5/PA6/PA7 — the true `SPI1` SCK/MISO/MOSI pins — with CS on PA4. So the two
boards use different peripherals for the same part, and neither bit-bangs it.

---

### 4. ✅ **Fixed (inrush)** / ⚠️ **firmware contract (back-power)** — GPIO power-gating of the BMP585

U3's `VDD` and `VDDIO` are both fed directly from **STM32 PB1** (net `LPS_PWR`) with
C3 + C5 = 0.2 µF local decoupling and no series resistance. Drive capability is a non-issue —
the sensor draws 260 µA max (BMP585 datasheet p.13, `i_peak`, read from the rendered page)
against a pin rated for milliamps. Two other things do matter.

**(a) Inrush on repeated power cycles — and the BMP585 wording is stronger than I first
reported.** Working from the BMP581 datasheet, I quoted a *should* from an application
section. Now that the BMP585 datasheet is on hand, the same requirement appears as a
**normative footnote to the electrical characteristics table**:

> **BMP585 datasheet, Table 4 "Electrical characteristics", footnote a (p.12):**
> "For supply ramps < 0.01 ms, a 10 Ohm resistor **must** be connected in series to the power
> supply (see 6.2.5)."
>
> **Table 4:** `t_VDDramp` & `t_VDDIOramp`, 10% to 90% of target voltage — **min 0.01 ms
> (10 µs), max 10 ms.**
>
> **§6.2.5, p.48:** "If VDD or VDDIO ramp-up times are not controlled and are faster than
> 10 µs, like in a direct connection to battery, the BMP585 inrush current should be
> externally limited to avoid damages **from repeated power cycles** using a 10 Ohm resistance."

So 10 µs is the **specified minimum ramp time**, not advice. Repeated power cycling is
precisely this design's duty cycle. The GPIO's own output impedance does act as the limiter —
inferring R from the STM32L432 spec (V<sub>OH</sub> ≥ V<sub>DD</sub> − 0.4 V at 8 mA →
~50 Ω worst case, ~25 Ω typical):

```
t(10–90%) = 2.2 · R · C = 2.2 · (25…50 Ω) · 0.2 µF ≈ 11…22 µs
```

That clears 10 µs, but only by **1.1× to 2.2×**, and it rests on an *inferred* GPIO impedance
plus a firmware speed setting that can change it. Compliance with a datasheet "must" should
not depend on an inference this thin.

**✅ Fixed 2026-09-04.** `R2 = 10 Ω` (`RC0201FR-0710RL`, 0201) is now in series:
`PB1 → R2 → C3/C5/U3.4/U3.8`. The decoupling sits on the **load** side of the resistor, which
is the correct arrangement — the caps stay at the sensor where they belong, and R2 limits the
inrush into them. The requirement is now satisfied **by construction** (the datasheet asks for
exactly a 10 Ω series resistor) rather than resting on an inferred GPIO impedance and a
firmware speed setting. The 2.6 mV drop at the 260 µA peak is immaterial.

Keeping PB1 on a low GPIO output-speed setting is still worth doing for EMI and power, but it
is no longer load-bearing for datasheet compliance.

**(b) Back-powering, which is a firmware contract.** When PB1 is low, `LPS_SCK`, `LPS_MOSI`
and `LPS_CS` are still driven from the VIN domain. If firmware leaves any of them high while
the sensor's supply is at 0 V, current flows through the sensor's ESD diodes into its
unpowered `VDDIO` — partially powering the part, defeating the power saving, and stressing the
diodes.

**Required firmware sequence:** before clearing PB1, drive `LPS_SCK`, `LPS_MOSI` and `LPS_CS`
low (or set them analog/high-Z), and keep **PA6 (`lps_rdy`) as an input with no pull-up** so it
does not source current into the powered-down INT output. This is now recorded in the config
under `mating_design.firmware_contracts`.

---

### 5. **Warning** — `Value` and `MPN` name different devices on three parts

Fab and assembly consume `MPN` and treat `Value` as a label, so none of these breaks a build.
They do mislead human and automated review, and one of them is a genuine open question.

| Ref | `Value` | `MPN` (what gets ordered) | Problem |
|---|---|---|---|
| U1 | `at25ex321D-UUN` → AT25XE321D | `AT25FF321A-UUN-T` | **Two different Renesas families.** Only the AT25XE321D datasheet is on hand. Which part is intended? |
| U302 | `stm32l431kc` | `STM32L432KCU6` | L431 vs L432 differ in peripheral set — not a harmless typo |
| U3 | `BMP585` | `BMP585` | consistent with each other, but the **project name, the old config and the only available datasheet all say BMP581** |

On U3: the footprint is `LGA9_BMP585_BOS` (9 pins), while BMP581 is a *10-pin* metal-lid LGA
("Compact 10-pin metal-lid LGA package … 2.0 × 2.0 mm²"). **The board is built for a BMP585
and the project name is stale**, not the other way round.

**Fix:** make `Value` match `MPN` on all three. Settle the U1 question before the BOM is used
to order — if AT25FF321A is correct, its datasheet needs to be added to the shared store; if
AT25XE321D is correct, the MPN is wrong and the fab would receive the wrong part number.

---

### 6. ✅ **Fixed** — U3 pin 9 (`L/M`) is a lasermarking pad; leaving it unwired is correct

KiCad ERC: `[error] pin_not_connected: Symbol U3 Pin 9 [L/M, Passive]`.

**Resolved against the BMP585 datasheet** (`bst-bmp585-ds003.pdf`, supplied 2026-09-04).
`L/M` is not a metal-lid connection — an earlier draft of this review guessed that and
recommended tying it to GND, which would have been wrong and in fact unbuildable. The pin
table gives:

| Pin | Name | Type | Description | Connect to |
|---|---|---|---|---|
| 9 | `L/M Pad` | — | **Lasermarking** | **"No external connection possible due to S/R coverage"** |

The pad is covered by solder resist, so there is nothing to connect to. **Leaving it unwired
is the only option and is correct as drawn.**

**✅ Fixed 2026-09-04.** A no-connect flag is now on U3 pin 9 (the analyzer reports its net as
`NO_CONNECT`), clearing the last ERC error. No copper change, as expected.

While in that datasheet, the rest of U3's connections check out — this **verifies the BMP585
pinout**, which was previously a gap:

| Pin | Datasheet | Net | Correct |
|---:|---|---|---|
| 1 | SCX (SPI serial clock) | `LPS_SCK` | ✅ |
| 2 | SDX (SPI serial data in, 4-wire) | `LPS_MOSI` | ✅ |
| 3 | SDO (SPI serial data out, 4-wire) | `LPS_MISO` | ✅ |
| 4 | VDDIO (digital interface supply) | `LPS_PWR` | ✅ |
| 5 | INT (interrupt / data ready) | `lps_rdy` | ✅ |
| 6 | VSS (ground) | `GND` | ✅ |
| 7 | CSB (chip select, low active) | `LPS_CS` | ✅ |
| 8 | VDD (analog power supply) | `LPS_PWR` | ✅ |
| 9 | L/M Pad (lasermarking) | — | ✅ (no connection possible) |

Also satisfied: *"all VSS pins must be connected to GND"* ✅, and the INT pin is used rather
than floating, so the datasheet's recommendation to ground an unused INT does not apply.
The connection diagrams show **100 nF on each of VDDIO and VDD**; with both tied to `LPS_PWR`
here, C3 + C5 (0.1 µF each) on the common node matches that. ✅

Two firmware notes from the same tables: BMP585 SPI supports **modes 0 and 3 only**, and
f<sub>SPI</sub> max is **12 MHz** at VDDIO ≥ 1.62 V (7 MHz below that).

---

### 7. **Warning** — Q501's base has no series resistor, and there is no baseboard here

Net `RST` contains exactly two pins: **Q501 base (pin 1)** and **J201 pin 5**. Nothing else.

An external programmer asserting `RST` therefore drives a forward-biased base-emitter junction
with no current limiting on the board. Current is set only by the driver's own output
impedance — roughly (3.3 − 0.8) / 30 Ω ≈ **83 mA**. The transistor survives that (200 mA peak
base rating per the PMBT2222AMB datasheet); the risk is to the *programmer's* output driver.

The house convention is that this base resistor lives on the mating baseboard. But this board's
config describes it as self-contained, and **J201 is a 6-pin SWD/programming header**
(VIN, VBAT, SWDIO, SWCLK, RST, GND), so it is not clear that anything upstream provides it.

**Please confirm:** does the programming adapter that mates with J201 carry the base resistor?
If yes, that should be recorded in `mating_design` so this stops being re-raised on every
review. If no, add ~4.7–10 kΩ in series with Q501's base — at these currents the pull-down
behaviour is unchanged.

---

### 8. **Info** — flash CS relies on the PA15 internal pull-up

This is the documented house convention (no external chip-select pull-ups; firmware drives CS
high as its first GPIO action), and PA15's reset state does include a pull-up, which helps.
Worth recording that the datasheet is explicit about *why* it wants a real resistor:

> **AT25XE321D datasheet, p.8:** "To ensure correct power-up sequencing, it is recommended to
> add a 10k Ohm pull-up resistor from CS to VCC. This ensures CS ramps together with VCC
> during power-up."

The residual gap is narrower than the general convention suggests, but it is not zero: during
the VIN ramp, **before the STM32's own POR completes, PA15 is high-Z**, so CS floats for that
window while the flash powers up on the same rail. Firmware cannot close this window because
firmware isn't running yet.

**Accepted as house convention.** If a future respin has room for one 0201, the 10 kΩ removes
the ambiguity. Either way, configure PA15's pull-up explicitly rather than relying on the
reset default.

---

### 9. ◐ **Partly fixed** — wrong symbol pin types accounted for 4 of the 6 original ERC errors

ERC reports 6 violations; most are symbol metadata, not design problems:

| ERC violation | Cause |
|---|---|
| `pin_to_pin` ×2 — "Power output and Power output are connected" | U2 pins 7 & 11 (GND) and U501 pin 5 (GND) are declared **Power output** instead of power input/passive |
| `power_pin_not_driven` — U3 pin 4 VDDIO | Correct by construction — `LPS_PWR` is a GPIO, not a rail (finding 4) |
| `pin_not_connected` — U3 pin 9 | Real; finding 6 |
| `lib_symbol_issues` — `Q_NPN_BEC` not found in library `Device` | `sym-lib-table` has no `Device` entry; the symbol renders from the schematic's embedded cache only |
| `multiple_net_names` — VIN / +2V5 | Real; finding 2 |

Also wrong but not currently flagged: **U501 pin 1 `CLKOUT` is declared an input** when it is
the RTC's clock output, and U501 pins 3/4 (`SCL`/`SDA`) are declared inputs when SDA is
bidirectional open-drain.

**Status 2026-09-04 — ERC is now clean (0 violations).** U2 pins 7/11 were changed from
`power_out` to `power_in`, which cleared both `pin_to_pin` errors; the U3 pin 9 no-connect
cleared `pin_not_connected`; a second `PWR_FLAG` cleared `power_pin_not_driven`; and the
remaining two were excluded.

Three residual items, now **latent rather than erroring** — they no longer produce ERC output,
so they are easy to forget:

- **U501 pin 1 `CLKOUT` is declared an input** when it is the RTC's clock output; pins 3/4
  (`SCL`/`SDA`) are declared inputs when SDA is bidirectional open-drain; pin 5 `GND` is still
  `power_out`. The last one no longer errors only because U2's GND is now `power_in`, so just
  one `power_out` remains on the net — a second one anywhere would resurrect the error.
- **`sym-lib-table` still has no `Device` entry**, so Q501's `Q_NPN_BEC` resolves only from the
  schematic's embedded cache. Its pinout is **verified correct** against the PMBT2222AMB
  datasheet, so nothing is wrong today — but an unresolvable transistor symbol is fragile:
  SOT-23/SOT-883 NPNs exist in at least six pin orderings, and re-linking libraries could
  silently resolve it to a different variant. This is worth fixing precisely because it is the
  one class of error that passes DRC and ERC while killing the board.
- **Two ERC exclusions were added rather than fixed** (`lib_symbol_issues` for Q_NPN_BEC,
  `multiple_net_names` for VIN/+2V5). Both are the underlying items above. Exclusions are the
  right tool for accepted conditions, but these two are still open, so they will keep the ERC
  clean while the causes persist.

---

### 10. ⚠️ **New** — the switched sensor-supply node is an unnamed net

Adding R2 split the old `LPS_PWR` net in two:

```
PB1 ──┬── LPS_PWR ──── R2 ──┬── __unnamed_13 ──┬── U3.4 VDDIO
      │   (2 pins)          │                  ├── U3.8 VDD
                                               ├── C3
                                               └── C5
```

`LPS_PWR` now names only the two-pin stub between the GPIO and the resistor, while **the node
that is actually the switched sensor rail carries no label at all.** Two consequences:

1. **The schematic reads misleadingly.** `LPS_PWR` looks like the sensor supply but is the
   pre-resistor stub; the real supply node is anonymous.
2. **A suppression is now fragile.** The `PP-001` finding (U3's power pins have no DC path to a
   rail — correct by construction for a power-gated device) has to be suppressed against
   `__unnamed_13`. Unnamed net numbering is **not stable** across schematic edits, so that
   suppression will silently stop matching the next time the sheet changes, and PP-001 will
   reappear as two errors.

**Fix:** label the post-resistor node, e.g. `LPS_VDD`. One label, and both problems go away.
The config's `PP-001` suppression carries a note to update the net name when you do.

---

## STM32L432KCU6 pin map — U302

Generated with `stm32_pinmap.py`; alternate and additional functions cross-checked against
ST's `STM32_open_pin_data` (`mcu/STM32L432KCUx.xml` + `GPIO-STM32L43x_gpio_v1_0_Modes.xml`) —
the same source STM32CubeMX uses. **Pin numbering matches the package** (25 GPIO pins checked).

| Pin | Port | Net | Connects to | Function (AF) | Required state |
|----:|------|-----|-------------|---------------|----------------|
| 1 | VDD | `VCC`/`VIN` | rail (26 nodes) | supply | — |
| 2 | PC14 | `clkout` | U501.1 RV-3028 CLKOUT | **`RCC_OSC32_IN`** (additional fn) | LSE **bypass** input |
| 3 | PC15 | — | — | unused | analog/no-pull |
| 4 | NRST | — | C502.1, Q501 collector | reset | external network |
| 5 | VDDA/VREF+ | `VCC`/`VIN` | rail | analog supply | — |
| 6 | PA0 | `WKUP1` | U2.5 ADXL367 INT1 | GPIO / wake | match INT1 polarity |
| 7 | PA1 | `ACCEL_nCS` | U2.4 ADXL367 CS | GPIO CS *(also `USART2_RTS` AF7)* | hold high |
| 8 | PA2 | `ACCEL_MOSI` | U2.2 ADXL367 MOSI/SDA | **`USART2_TX` (AF7)** — sync mode = MOSI | drive low idle |
| 9 | PA3 | `ACCEL_MISO` | U2.3 ADXL367 MISO/ASEL | **`USART2_RX` (AF7)** — sync mode = MISO | input, no-pull |
| 10 | PA4 | `ACCEL_SCK` | U2.1 ADXL367 SCLK | **`USART2_CK` (AF7)** — sync mode = SCK | drive actively (never strap low) |
| 11 | PA5 | `LPS_SCK` | U3.1 BMP585 SCX | `SPI1_SCK` (AF5) | low before gating off |
| 12 | PA6 | `lps_rdy` | U3.5 BMP585 INT | GPIO input (`SPI1_MISO` unused) | input, **no pull-up** |
| 13 | PA7 | — | — | unused (`SPI1_MOSI`) | analog/no-pull |
| 14 | PB0 | `LPS_CS` | U3.7 BMP585 CSB | GPIO CS (SPI1_NSS capable) | high when powered |
| 15 | PB1 | `LPS_PWR` | **R2 (10 Ω)** → U3.4 VDDIO, U3.8 VDD, C3, C5 | **GPIO power switch** | low speed (EMI/power) |
| 16 | VSS | GND | rail (22 nodes) | ground | — |
| 17 | VDD | `VCC`/`VIN` | rail | supply | — |
| 18 | PA8 | — | — | unused | analog/no-pull |
| 19 | PA9 | — | — | unused | analog/no-pull |
| 20 | PA10 | — | — | unused | analog/no-pull |
| 21 | PA11 | `LPS_MISO` | U3.3 BMP585 SDO | `SPI1_MISO` (AF5) | no pull-up when gated |
| 22 | PA12 | `LPS_MOSI` | U3.2 BMP585 SDX | `SPI1_MOSI` (AF5) | low before gating off |
| 23 | PA13 | `SWDIO` | J201.3 SWD | `SWDIO` (AF0) | preserve SWD |
| 24 | PA14 | `SWCLK` | J201.4 SWD | `SWCLK` (AF0) | preserve SWD |
| 25 | PA15 | `AT25_nCS` | U1.B4 AT25 nCS | GPIO CS (SPI1/3_NSS capable) | **explicit** internal pull-up |
| 26 | PB3 | `AT25_SCK` | U1.F2 AT25 SCK | **`SPI3_SCK` (AF6)** — forfeits TRACESWO | drive low idle |
| 27 | PB4 | `AT25_MISO` | U1.D4 AT25 SO | **`SPI3_MISO` (AF6)** — forfeits NJTRST | input, no-pull |
| 28 | PB5 | `AT25_MOSI` | U1.E3 AT25 SI | **`SPI3_MOSI` (AF6)** | drive low idle |
| 29 | PB6 | `SCL` | U501.3 RV-3028 SCL | GPIO (bit-banged I²C) | internal pull-up |
| 30 | PB7 | `SDA` | U501.4 RV-3028 SDA | GPIO (bit-banged I²C) | internal pull-up |
| 31 | BOOT0 | GND | GND | boot strap | **hard low** |
| 32 | VSS | GND | rail | ground | — |
| 33 | GND | GND | rail (exposed pad, 2 vias) | ground | — |

**Three things fall out of this map:**

- **Shared buses / deselect contracts.** Three separate select lines on three *different*
  peripherals — accelerometer on **USART2 synchronous mode** (AF7), pressure sensor on **SPI1**
  (AF5), flash on **SPI3** (AF6). Assign them that way and the reported SPI1 collisions vanish
  and all three can be live at once. Each CS stays a firmware-owned GPIO.
- **BOOT0 is hard-tied to GND** — so, unusually for this family, **there is no option-byte
  concern on this board.** `stm32_pinmap.py` reports "PULLED via R1.2" only because R1 happens
  to sit on the GND net serving U501's `VBACKUP`; that is an artefact, not a strap resistor.
- **Unused GPIOs (5):** PC15, PA7, PA8, PA9, PA10 — set analog/no-pull for lowest leakage.
  PA15 is in use but carries a default pull-up worth setting explicitly.

**PC14 is not a plain GPIO.** ST lists `RCC_OSC32_IN` on it as an *additional* function
(enabled through RCC registers, not `GPIOx_AFR`). The RV-3028's 32.768 kHz `CLKOUT` drives the
**LSE in bypass mode**, giving a 1 PPM timebase with no crystal on the board — the RTC is the
`-1PPM` TCXO variant. Firmware must enable the RV-3028's CLKOUT and store the setting in its
EEPROM (datasheet §7.1, register 35h `CLKOE`); on a virgin part the default must be verified.

---

## Verification basis

**Verified against manufacturer PDFs** — these are settled; a future review need not re-derive them:

- **Q501 pinout — the highest board-killing risk, and it is correct.** The `Q_NPN_BEC` symbol
  assumes pin 1 = base, 2 = emitter, 3 = collector. PMBT2222AMB datasheet, Table 2 "Pinning
  information": **pin 1 B base, pin 2 E emitter, pin 3 C collector.** Exact match. The
  schematic wires it as a correct NPN reset inverter (base → `RST`, emitter → GND,
  collector → `NRST`), and the KiCad stock `SOT-883` footprint carries that through — confirmed
  by the pad/net cross-check.
- **U1 12-ball WLCSP ball map — correct, ball for ball.** Read from the rendered AT25XE321D
  Figure 2 bottom view (p.8), not from the text layer: B2 VCC, B4 CS, C3 GND, D2 HOLD/RESET,
  D4 SO, E3 SI, F2 SCK, F4 WP, A1/A5/G1/G5 NC. Matches the schematic exactly.
- **U1 `WP` floating is explicitly permitted** — "The WP pin is internally pulled high and can
  be left floating if not used." Not a defect.
- **U1 `RESET` tied to VIN** — correct; active-low reset held inactive.
- **U2 ADXL367 pin assignment** matches the datasheet pin-description table in order, all 12 pins.
  Pin 8 `ADC_IN` "can be left unconnected" — fine as drawn.
- **U501 RV-3028 backup network is exactly the datasheet's reference configuration.** My first
  reading of "VBACKUP through 10 kΩ to GND" looked odd; the datasheet (p.9) says: "Backup Supply
  Voltage. When the backup switchover function is not needed, **VBACKUP must be tied to VSS with
  a 10 kΩ resistor.**" R1 = 10 kΩ does exactly that. `EVI` tied to GND likewise matches §7.1
  "NO BACKUP SOURCE / EVENT INPUT NOT USED" (45 nA typ). **Not a defect.**
- **U3 BMP585 pinout — verified, all 9 pads** against `bst-bmp585-ds003.pdf` (supplied during
  this review): SCX, SDX, SDO, VDDIO, INT, VSS, CSB, VDD, and the L/M lasermarking pad. The
  8-pin-plus-L/M-pad arrangement matches the `LGA9_BMP585_BOS` footprint. Decoupling matches
  the datasheet's connection diagrams (100 nF per supply pin).
- **USART2 synchronous mode — verified** in the STM32L432 datasheet, Table 11 (USART2:
  Synchronous mode supported) and §3.x ("USART1 and USART2 also provide … SPI-like
  communication capability", DMA-served, up to 10 Mbit/s). PA2/PA3/PA4 = `USART2_TX`/`_RX`/`_CK`,
  all AF7, per ST's `STM32L432KCUx.xml`.
- **STM32L432KC supply range** 1.71–3.6 V — VIN stays in range across cell life.

**Verified by tooling:**

- `padnet_crosscheck.py` — **28 footprints, 0 mismatches** (26 before the revision). Every schematic pin-net matches its
  PCB pad-net. This is the check that catches library footprint pin-numbering errors, which are
  invisible to both DRC and ERC.
- **KiCad DRC** (run in place, with `--refill-zones`): **0 violations, 0 unconnected items,
  0 schematic-parity issues, 0 footprint issues** under the tightened rules — re-confirmed after
  the revision, now including the re-enabled `track_not_centered_on_via` rule.
- **KiCad ERC: 0 violations** after the revision (was 6; see finding 9 for how each cleared and
  which two were excluded rather than fixed).
- **Fab package verified by geometry, not mtime.** Per house practice the `.kicad_pcb` mtime
  always postdates the export it produced, so mtime carries no information. Instead I sampled
  the shipped Gerbers directly (transform X₀ = 140.0, Y₀ = 113.0, 1e-6 mm units):
  **50 of 50 sampled F.Cu and B.Cu track endpoints present**, 39/39 vias in the drill file at
  0.2007 mm, 4 NPTH at 1.0998 mm (the mounting holes), outline exactly 18.0 × 10.0 mm, and
  every via measuring a 0.1524 mm annular ring. The package `pcbway_production/2026-09-04-07-36-32`
  **postdates the rule change and matches the current board.**
- **Layer completeness:** all 4 copper layers, both masks, both pastes, both silks, edge cuts,
  and both PTH and NPTH drill files present.

**Stackup:** F.Cu 0.035 / prepreg 0.08 / In1.Cu 0.035 (**VIN plane**) / core 0.08 /
In2.Cu 0.035 (**GND plane**) / prepreg 0.08 / B.Cu 0.035 ≈ 0.4 mm. Both inner planes are
single contiguous fills covering the whole board. Zone stitching: 14 GND vias, 7 VIN vias.

**Decoupling** is dense and close — nearest cap 0.93 mm from U501. VIN bulk is
C4 22 µF + C404 22 µF + C6 47 µF plus six 0.1 µF, appropriately sized to support ~10 mA
flash-write pulses from a coin cell.

---

## Analyzer findings triaged as false positives

The raw analyzers produced 32 PCB + 54 EMC + 7 cross-domain findings. Most are artefacts.
I confirmed the big ones with hard evidence rather than assuming, and all are now recorded
as suppressions in `.kicad-happy.json` (which cut the EMC set from 54 active to 7 info-level).

| Rule | Claim | Why it is wrong |
|---|---|---|
| `GP-004` | "Low ground plane fill ratio" (0.298) | **Fill ratio is measured against the user-drawn zone outline (324 mm²), which is far larger than the 18 × 10 mm board.** Filled GND is 115.8 mm² of a 180 mm² board — a solid plane. |
| `PS-002`, `GP-001`, `RP-002` | "VIN plane split: 4 islands", "9 signals crossing plane gap", 15 × "significant reference plane gap" | **Both zones report `fill_region_count: 1`** — a single contiguous region each — and **DRC reports 0 unconnected items.** There are no gaps to cross. This is the known union-find artefact. |
| `GR-002` | "Width varies by 3.6 mm across copper/edge layers" | Copper is *inset* from the board edge, not misaligned. In1/In2 measure 17.399 × 9.399 mm inside an 18 × 10 mm outline — **exactly the new 0.3 mm edge clearance.** The finding is evidence the rule works. |
| `FD-001` (error ×2) | "No fiducials on F.Cu / B.Cu" | **House convention.** BitTagNG, PresTag and CompassTag all contain zero fiducial references and have all been fabricated and assembled. |
| `CK-003` ×11 | "Clock routed near connector J301/J302/J303/J304/J401" | J301–J304 are **1.1 mm NPTH mounting holes** (confirmed: 4 NPTH at 1.0998 mm in the drill file, and `CP-002` "no opposite-layer copper" for all four). J401 is the battery connector. |
| `CC-002` ×15, `DFM-001` | "Narrow signal: 0.1016 mm" | Deliberate on these dense tags; a process-selection note, never a current-capacity concern at ~10 µA. |
| `TV-001` | "U302 thermal vias insufficient (2/9)" | Thermal rule. Total board dissipation is microwatts; 2 vias on the exposed pad are electrically adequate. |
| `PU-001` | "U2 pin INT2 missing pull-up" | `INT2` is an interrupt **output** and is unused. Outputs need no pull-up. |
| `TE-001` | "Test point coverage 0/40 nets" | No room on an 18 × 10 mm tag; J201 SWD plus the flash are the bring-up path. |
| `RP-001` ×14, `CK-001` ×5 | stitching vias / clocks on outer layers | Accepted for a 4-layer tag over solid inner planes; return paths are millimetres and emissions at 10 µA and ≤1 MHz SPI are not a compliance risk. |
| `EP-AUD` | "ESD audit J201: none" | J201 is an internal programming header inside a sealed tag, not an exposed port. |

**Important process note:** the pre-existing `analysis/` run (2026-08-29) was **poisoned** —
`project_settings.source` read `BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro`, so every
rule-derived number in it was measured against the wrong rule set. That stray project file has
since been swept from the directory. All results in this review come from a fresh
2026-09-04_0738 run whose `rules_source` correctly reads `BitPresTagBMP581.kicad_pro`.

---

## Not performed / limits

- **SPICE simulation — not run.** No simulator installed (`ngspice`, `ltspice`, `xyce` all
  absent). Low impact: the board has no filters, dividers, op-amps or crystal load networks to
  validate. The one computed circuit (the LPS_PWR RC ramp) was done by hand above.
- **Thermal analysis — ran, produced nothing.** `analyze_thermal.py` skipped with "no components
  had quantifiable power dissipation data." Correct outcome: total board dissipation is
  microwatts and there is no regulator or power stage. Not a gap.
- **Component lifecycle audit — not possible.** No distributor API credentials are configured
  (`LC-007`). Obsolescence status of all 11 BOM lines is unverified. Worth a manual check on
  U1, given the AT25XE321D / AT25FF321A ambiguity.
- **Datasheet gaps — two parts unverified** (was three; BMP585 resolved 2026-09-04):
  - ~~**BMP585 (U3)**~~ — **resolved.** `bst-bmp585-ds003.pdf` supplied during review; U3's
    pinout is now fully verified and findings 4 and 6 have been corrected against it rather
    than against BMP581 text.
  - **AT25FF321A** — not on hand; only AT25XE321D. Resolve the MPN question (finding 5) first.
  - **CDBQC0130L-HF (D401)** — not on hand. Forward drop, and hence exact VIN headroom at
    end of cell life, is unverified. VIN ≈ 1.9 V at a 2.0 V cell still clears the STM32's
    1.71 V limit, so the margin is adequate on reasonable assumptions.
- **Previous-review delta — none available.** This is the first review of this board; there is
  no prior `deep_review.json` to diff, and the one earlier analyzer run was poisoned (above),
  so diffing against it would be misleading rather than informative.
- **Custom footprint geometry — deliberately not re-derived.** `LGA9_BMP585_BOS`,
  `adesto_wlcsp12`, `CC-12-4_ADI` and `RV-3028-C8` are vendor/UltraLibrarian-supplied and have
  shipped on sibling boards; their land, mask and paste geometry is treated as validated per
  house convention.

---

## Recommended actions

**✅ Done in the 2026-09-04 revision:** C8 (finding 1), R2 (finding 4 inrush), U3 pin 9
no-connect (finding 6), U2 GND pin types (finding 9), `track_not_centered_on_via` re-enabled
and its violation fixed.

**Still open — electrical / sourcing:**

1. **Settle U1's identity** — AT25XE321D or AT25FF321A? (finding 5) The fab orders by MPN, so
   this is the one open item that could produce the wrong physical board.
2. **Confirm the Q501 base resistor** lives in the programming adapter (finding 7).

**Still open — schematic hygiene, no copper change:**

3. **Label the switched sensor node** `LPS_VDD` (finding 10) — also un-breaks the `PP-001`
   suppression, which is currently keyed to an unstable unnamed-net number. This is the last
   item with a concrete failure mode attached.
4. Add a schematic text note giving the rail's voltage *range* (finding 2) — the one thing the
   `VCC` label cannot carry.
5. Fix `Value` vs `MPN` on U1, U302 (finding 5); decide whether to rename the project to BMP585.
6. Fix the residual U501 pin types and add `Device` to `sym-lib-table` (finding 9), then drop
   the `lib_symbol_issues` exclusion.

**Do not undo:** the `multiple_net_names` ERC exclusion. `VCC`/`VIN` on one net is a deliberate
alias (internal name vs environment-facing name), and the exclusion documents it correctly.

**Commit-ready now:**

8. **Commit the tightened design rules and the fab package.** DRC is clean and the Gerbers are
   verified against the board. Note `BoardDesigns/.gitignore` excludes `*.zip`, so the gerber
   archive needs `git add -f pcbway_production/2026-09-04-07-36-32/*_gerber.zip` (~46 kB) —
   otherwise the thing actually sent to the fab is not captured.
9. **Delete three committed, poisoned analyzer files** — left in place for you to action rather
   than removed unasked, since they are tracked in git:

   ```bash
   git rm analysis/pcb.json analysis/schematic.json analysis/cross_analysis.json
   ```

   `analysis/pcb.json` is committed and still reads
   `project_settings.source = "BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro"` — every rule-derived
   number in it was measured against **BitTagNG's** rule set, not this board's. It is superseded
   by `analysis/2026-09-04_0738/`, but until it is removed any tool or reviewer that opens the
   flat path gets wrong numbers that look authoritative.

**Suggested tag once the above is committed**, per house practice:
`review/BitPresTagBMP581-2026-09-04` (annotated), recording 0.3 mm edge clearance,
0.1524 mm annular ring, DRC/ERC state, drill reconciliation and the PCBWay order spec.

**Firmware hand-off** — see `mating_design.firmware_contracts` in `.kicad-happy.json`:
ADXL367 on **USART2 synchronous mode** (AF7; set MSBFIRST, CPOL/CPHA for mode 0, and LBCL),
BMP585 on **SPI1** (AF5), flash on **SPI3** (AF6); sequence the LPS SPI pins low before gating
PB1; keep PB1 at lowest output speed; enable RV-3028 CLKOUT in EEPROM and select LSE bypass on
PC14; set the 5 unused GPIOs analog/no-pull.

---

## Changes made to the repository by this review

- **`.kicad-happy.json` rewritten.** The previous config had been copied from a
  CompassTag-style board and was substantively wrong: it described an **AK09940A magnetometer
  on PA5–PA10**, a **TPS7A2018 LDO at U4**, a **+1V8 rail** and **USART2 nets**, none of which
  exist on this board, and it suppressed `RS-001` for a `+3V3` rail that also does not exist.
  It has been replaced with a 33-entry pin map derived from the actual schematic, correct rail
  voltages (the bogus `+2V5: 2.5` override removed), 21 evidence-backed suppressions, explicit
  firmware contracts, and a `reviewer_notes` block recording what is verified so the next
  review starts from the settled position.
- **`analysis/deep_review.json`** — 10 evidence-gated findings; passes `deep_review_gate.py`
  (10 verified, 0 quarantined).
- **`analysis/.gitignore`** replaced with a comment-only no-op, and `analysis.track_in_git`
  set `true`, so the analyzer JSON and the non-regenerable `deep_review.json` are tracked.
  The file must stay in place: `analyze_pcb.py` recreates a real ignore file whenever one is
  absent, regardless of `track_in_git`.
- **`datasheets/`** symlinked to the shared store at `../libraries/datasheets`.
