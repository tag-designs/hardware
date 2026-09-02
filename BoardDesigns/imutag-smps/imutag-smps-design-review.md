# imutag-smps Design Review

## Review 2 — 2026-09-02: switching converter and magnetics

Scope: the SMPS power stage and the current state of the board, following the
2026-08-26 review. Updated 2026-09-02 after the L1 reroute and the first PCBWay
export. This board has **not** been fabricated.

Datasheets: `BoardDesigns/libraries/datasheets`.

### Verdict

The board is in good shape and the geometry is fab-ready. KiCad DRC run in the
project directory is **0 violations / 0 unconnected / 0 schematic-parity**, and the
edge-clearance and annular-ring work carried over from `imutag-nand-bmp581` is
already applied here: inner copper 0.3005 mm from the profile, all 47 vias at
0.1524 mm (6.00 mil).

Two things are worth your attention, neither of them a layout defect.

**First, the previous review's rule-derived findings were measured against the
wrong rules.** `analysis/2026-08-26_0809/pcb.json` records
`rules_source: BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro`. Findings 7 and 8 of
Review 1 — the advanced-process and edge-clearance items — came from that run and
should not be trusted as stated. They are moot now anyway, since the rules and
geometry have both moved.

**Second, and more substantive: this package cannot be forced into PWM mode.**
The TPS62840 datasheet §8.3.3 says the MODE pin "is not available in the YBG
package, where the device automatically transitions between power-save and PWM
modes." `U4` is a `TPS62840YBGR`. That removes an option the family-level
SMPS-versus-LDO decision was resting on, and it makes the choice between this
board and `imutag-nand-bmp581` starker than the record suggests. Finding 1 below.

### What changed since Review 1

The board is now electrically and geometrically identical to
`imutag-nand-bmp581` except for the power stage:

```text
only in imutag-smps          L1  2.2 uH  (DFE201612E-2R2M=P2)
only in imutag-nand-bmp581   C9  0.1 uF
differing                    U4  TPS62840YBGR   vs  TPS7A02185PDQNR
                             C7  4.7 uF (in)    vs  10 uF
                             C8  10 uF (out)    vs  1 uF
```

Everything else — sensors, MCU, NAND, RTC, connectors, mounting holes — matches.
So every settled position in `imutag-nand-bmp581/.kicad-happy.json` applies here
unchanged, and this review does not re-derive any of it.

Applied since Review 1, verified in the current files:

```text
min_copper_edge_clearance   0.0    -> 0.3      (geometry: 0.3005 mm on In1/In2)
min_via_annular_width       0.1016 -> 0.1524
net class Default via       0.4572/0.254 -> 0.5048/0.20
vias on board               47, all 0.1524 mm (6.00 mil), single drill size
```

### Findings

#### 1. The YBG package has no MODE pin — forced PWM is not available

Severity: **medium — architectural, not a defect** · Confidence: high · Evidence:
TPS62840 datasheet §8.3.3, netlist pin map

`U4` is `TPS62840YBGR`, the WCSP-6 variant. Its six balls are fully accounted for:

```text
A1 GND  -> GND        B1 VIN -> VBAT       C1 EN   -> VBAT   (always enabled)
A2 VOS  -> +1V8       B2 SW  -> Net-(U4-SW) C2 VSET -> GND    (selects 1.8 V)
```

There is no MODE ball. The datasheet is explicit:

> Connecting the MODE input to GND enables the automatic PWM and power-save mode
> operation... Pulling the MODE pin high forces the converter to operate in PWM
> mode even at light load currents, allowing lower ripple compared to PFM mode
> switching. **This pin is not available in the YBG package, where the device
> automatically transitions between power-save and PWM modes.**

At this board's 1–2.2 mA average load the converter will sit in power-save (PFM),
which is exactly what you want for efficiency and exactly what you do not want for
predictable magnetic noise. PFM bursts are load-dependent and asynchronous with the
magnetometer's sampling, so the interference is broadband and non-stationary rather
than a clean 1.8 MHz tone you could filter or notch.

**Why this matters beyond this board.** The `imutag-nand-bmp581` review records the
family-level reasoning as: *forced-mode SMPS efficiency is essentially LDO-like, so
the LDO variant is the cleaner magnetic choice at little energy cost.* That is
sound reasoning, but it evaluates an option this part does not offer. The real
comparison is:

| | imutag-smps (TPS62840YBG) | imutag-nand-bmp581 (TPS7A02185) |
|---|---|---|
| Battery current at 2 mA load, 3.7 V | ~1.08 mA | 2.00 mA |
| Battery life | ~1.85× | baseline |
| Switching noise | PFM bursts, not selectable | none |
| Magnetic sources near U2 | L1 at 11.15 mm | none |

So the SMPS keeps its **full** efficiency advantage — roughly halving battery
current — precisely because you cannot force it into the mode that would have
erased it. And it keeps unpredictable switching noise with no setting that makes it
deterministic. There is no middle position on this part.

If a middle position is wanted, it has to come from a different package: the SON-8
(`TPS62840DLC`) and HVSSOP variants do expose MODE, at the cost of board area on a
21.5 × 11.5 mm tag. Worth knowing before committing this variant to fab.

#### 2. Switching-loop layout review — the item Review 1 deferred

Severity: **pass, with one observation** · Confidence: high · Evidence: routed
segments, zone definitions, via positions

Review 1 closed the TPS62840 check with "layout still deserves a visual/current-loop
review around VIN, SW, L1, C7, C8, and GND." Doing that now:

```text
C7 4.7 uF (input)  -> U4      1.60 mm centre-to-centre
U4 -> L1                      3.39 mm centre-to-centre
L1 -> C8 10 uF (output)       2.24 mm centre-to-centre

SW node   2.58 mm total, 2 segments, 0.254 mm wide, F.Cu only, no vias
```

This is a good switching layout for a board this size:

- **The SW node is short, wide and single-layer.** 2.58 mm of 0.254 mm trace with
  no via transitions keeps both the dV/dt radiating area and the parasitic
  inductance small. The high-impedance node is the one you most want to keep tight,
  and it is.
- **The input cap is tight to VIN.** 1.60 mm on a 0402 is about as close as the
  DSBGA allows, and the input loop is the high-dI/dt path that actually radiates
  magnetically.
- **There is a local F.Cu GND pour at U4** — 2.80 × 1.29 mm at priority 2, giving
  the input loop a short return before it drops to the In2 plane. Four GND vias sit
  within 2.9 mm of U4, the nearest at 1.15 mm.
- **There is an F.Cu copper keepout under L1** — 1.70 × 0.48 mm, centred on the
  part, keeping trace copper out of the region directly beneath the winding.
- **In2.Cu is a solid GND plane** under the whole cluster, so the return path is
  directly beneath the forward path on every segment.

One observation, low severity, **improved by the 2026-09-02 reroute**: SPI flash
traces run close to the inductor.

```text
                      before      after
/AT25_MOSI   B.Cu     1.13 mm  -> 1.38 mm
/AT25_SCK    B.Cu     1.57 mm  -> 1.69 mm
/AT25_SCK    F.Cu     1.59 mm  -> 1.59 mm  (unchanged)
```

L1's body is 1.6 × 2.0 mm, so its half-extent is 0.8 mm in x and 1.0 mm in y. Before
the reroute `/AT25_MOSI` passed essentially under the part; it is now clear of the
body outline, though still close. Seven vias remain within 3 mm of L1, in the same
positions as before — the reroute moved traces, not vias.

This was already low severity and is now lower. The In2 GND plane sits between L1 and
the B.Cu traces, giving real eddy-current shielding at 1.8 MHz, and flash traffic is
intermittent. I had said I would not re-route for this; the change does no harm and
buys a little margin, so it is a reasonable place to have spent the effort. If flash
behaviour is ever marginal during heavy write bursts, this remains the first place to
look.

#### 3. Magnetometer: separate the offset from the noise

Severity: **medium — validation item** · Confidence: medium-high · Evidence:
placement geometry, BMM350 and inductor datasheets

Review 1 finding 5 treats this as "magnetometer offset... primarily a
calibration/validation item," with L1 at 11.15 mm and rotated so its axis is ~89°
off the vector to U2. That analysis is right about offset and worth keeping. But it
runs two different effects together, and only one of them calibrates out.

**Static offset — calibratable.** L1 is a Murata DFE201612E, a metal-alloy power
inductor. Its core is a ferromagnetic body 11.15 mm from the sensor, so it distorts
the ambient field whether or not the converter is switching. This is soft-iron
distortion: stable for a given assembly, correctable by per-unit calibration, and
the 89° axis orientation already minimises it. No action beyond calibration.

**Switching noise — not calibratable.** The ripple current in L1 produces a
time-varying field at the sensor. Order of magnitude, treating the winding as a
dipole with roughly 10 turns enclosing ~0.8 mm² at ~100 mA ripple:

```text
m  ~ I x A x N   =  0.1 x 8e-7 x 10   =  8e-7 A.m2
B  =  (u0/4pi)(2m/r^3)  at r = 11.15 mm   ~  0.1 uT   (unshielded equivalent)
```

Against the BMM350's ~0.065 µT noise floor and Earth's ~50 µT, that is around
0.1–0.2° of heading error — *before* accounting for the metal-alloy core's
shielding, which will pull it down substantially. Call the realistic figure
0.01–0.1 µT. **Treat these numbers as an order-of-magnitude sanity check, not a
specification** — the assumed turn count and ripple current are estimates, and
Murata does not publish leakage for this series.

The reason it still matters at that magnitude is finding 1: in PFM the bursts are
load-dependent and asynchronous to the BMM350's per-ODR-tick flux-guide reset, so
the error is non-stationary. Averaging reduces it slowly and calibration does not
remove it at all.

Recommendation, sharpening Review 1's:

- Measure with the converter in three states — quiescent, at 1 mA, and during a
  flash-write burst — not just idle and peak. The interesting case is a *changing*
  load, because that is where PFM burst rate moves.
- Compare directly against an assembled `imutag-nand-bmp581`. You have the LDO
  sibling; it is the control experiment, and it makes the comparison empirical
  rather than theoretical.
- Decide on measured data whether the ~1.85× battery life is worth the noise floor
  for the intended deployment. Both boards are otherwise identical, so this is a
  clean either/or.

#### 4. BMP581 symbol — FIXED, and it exposed a latent GND modelling error

Severity: **low — hygiene** · Confidence: high · **Resolved 2026-09-02** · Evidence:
KiCad ERC in place, symbol diff against `tag_library.kicad_sym`

The cached symbol typed VSS pins 3, 8 and 9 as `power_out` where
`libraries:BMP581` has `power_in`. Pin numbers, names and every other property
matched. Updating from the library brought them into line — the pin maps are now
identical and `lib_symbol_mismatch` is gone.

**That update exposed a real error, exactly as it did on the sibling:**

```text
[error] power_pin_not_driven: Symbol U1 Pin B1 [GND, Power input, Line]
```

Same pin, same part — U1, the TPS22916 load switch. The mistyped VSS pins had been
silently acting as the GND net's driver, satisfying ERC's power-driven check. The
board's only `PWR_FLAG` sat on a wire at `(104.14, 21.59)`, not on GND, so nothing
else was holding it up. This was not a regression from the symbol fix; the fix
*revealed* a modelling error that had always been there.

Resolved by adding a second `PWR_FLAG` (`#FLG02`) coincident with the GND symbol at
`(20.32, 66.04)`. **That fix is real** — with all ERC exclusions cleared, the
`U1 Pin B1 [GND]` error is gone.

> **A correction on my own work.** I reported this update as "verified safe — no new
> ERC violations," having simulated it on a copy. That was wrong. The copy could not
> resolve its symbol libraries, and `lib_symbol_mismatch` persisted in my test even
> after I had made the symbols match — which was the evidence that the comparison was
> not running. I explained it away rather than investigating. **Verify ERC and DRC
> changes in the board's own directory, never on a copy**; the same trap already
> applies to DRC, where a copy without `fp-lib-table` produces phantom findings.

### ERC reads 0, but that is 22 exclusions — finding 5

Severity: **low — bookkeeping, not electrical** · Confidence: high · Evidence:
`erc_exclusions` in `.kicad_pro`, ERC re-run with exclusions cleared

ERC now reports 0 violations. That is with **22 `erc_exclusions`** recorded in
`.kicad_pro`, covering the `VBAT`/`VIN` merge, the U6 `WP`/`HOLD` pattern and others.
Suppressing them is a legitimate call — both were already-accepted house positions —
and because the exclusions live in `.kicad_pro` rather than the gitignored
`.kicad_prl`, they travel with the repo. Two things are worth recording anyway.

**A future reviewer running ERC sees 0 and learns nothing.** The reasons live only in
`.kicad-happy.json`. That is what it is for, and both positions are recorded there, so
this is working as intended — but "ERC clean" now means "clean given 22 accepted
exclusions," and the review should say so rather than implying an unqualified pass.

**Clearing the exclusions reveals two errors, and neither is what the GND fix
addressed:**

```text
[error] power_pin_not_driven   U1 Pin A2 [VIN, Input]
[error] pin_to_pin             U1 Pin A1 [VOUT, Output]  <->  #FLG01 [Power output]
```

Both are pin-type modelling artifacts rather than electrical defects:

- **`+1V8` has no ERC driver.** The TPS62840 symbol types its `VOS` pin as `input`
  — correct, it is a sense pin — so nothing in the model drives the rail the buck
  actually produces. Hence U1's `VIN` reads as undriven.
- **`#FLG01` sits on `/Flash 1V8`,** which U1's `VOUT` already drives. A `PWR_FLAG`
  belongs on a net with no driver; on one that has one it creates an
  Output-to-Power-output conflict. Electrically harmless — `PWR_FLAG` is a virtual
  symbol — but it means `#FLG01` is on the wrong net.

**Worth trying: move `#FLG01` from `/Flash 1V8` to `+1V8`.** That should clear both
errors at once — removing the conflict on `/Flash 1V8` and giving `+1V8` the driver
it lacks — and let you drop two of the 22 exclusions rather than carrying them. I
have not verified this, so treat it as a proposal to test in place rather than a
result.

Separately, `TPS22916BYFPR` now shows a `lib_symbol_mismatch` of its own, currently
excluded. Same class as the BMP581 drift in finding 4 and worth the same treatment.

### STM32U375KGU6 pin map

`U302`, UFQFPN-32. All 33 pins from the netlist, with the alternate-function number
each signal needs, cross-checked against the **`STM32_open_pin_data` submodule** —
ST's own machine-readable pin data, `mcu/STM32U375KGUx.xml` plus
`mcu/IP/GPIO-STM32U375x_gpio_v1_0_Modes.xml`.

| Pin | Port | Net | Needs | AF | Check |
|---|---|---|---|---|---|
| 1 | VDD | `+1V8` | supply | — | ok |
| 2 | PC14 | `/clkout` | RCC_OSC32_IN | additional fn | ok — LSE bypass |
| 3 | PC15 | — | — | — | unused |
| 4 | NRST | `Net-(Q501-C)` | reset | — | ok |
| 5 | VDDA/VREF+ | `+1V8` | analog supply | — | ok |
| 6 | PA0 | `/WKUP1` | WKUP1 | additional fn | ok |
| 7 | PA1 | — | — | — | unused |
| 8 | PA2 | — | — | — | unused |
| 9 | PA3 | — | — | — | unused |
| 10 | PA4 | `/AT25_nCS` | GPIO out | AF5 = SPI1_NSS avail. | ok |
| 11 | PA5 | `/AT25_SCK` | SPI1_SCK | **AF5** | ok |
| 12 | PA6 | `/AT25_MISO` | SPI1_MISO | **AF5** | ok |
| 13 | PA7 | `/AT25_MOSI` | SPI1_MOSI | **AF5** | ok |
| 14 | PB0 | — | — | — | unused |
| 15 | PB1 | `/LSM_CS` | GPIO out | no SPI AF exists | ok — must be GPIO |
| 16 | VSS | `GND` | ground | — | ok |
| 17 | VDD | `+1V8` | supply | — | ok |
| 18 | PA8 | `/FLASH_PWR` | GPIO out | — | ok |
| 19 | PA9 | `/LPS_DRDY` | GPIO in | AF3 = SPI2_SCK unused | ok |
| 20 | PA10 | `/LPS_CS` | GPIO out | no SPI NSS exists | ok — must be GPIO |
| 21 | PA11 | `/LPS_MISO` | SPI1_MISO | **AF5** | ⚠ **collides with PA6** |
| 22 | PA12 | `/LPS_MOSI` | SPI1_MOSI | **AF5** | ⚠ **collides with PA7** |
| 23 | PA13 | `SWDIO` | JTMS/SWDIO | **AF0** | ok |
| 24 | PA14 | `SWCLK` | JTCK/SWCLK | **AF0** | ok |
| 25 | PA15 | — | — | — | unused |
| 26 | PB3 | `/LPS_CK` | SPI1_SCK | **AF5** (AF6 = SPI3_SCK) | ⚠ **collides with PA5** |
| 27 | PB4 | `/LSM_TRG` | **LPTIM1_CH2** | **AF1** | ok — forfeits NJTRST |
| 28 | PB5 | `/BMM_INT` | GPIO in | — | ok |
| 29 | PB6 | `/SCL` | I2C1_SCL | **AF4** | ok |
| 30 | **PB7 / BOOT0** | `/SDA` | I2C1_SDA | **AF4** | ok — strap, see below |
| 31 | VCAP | `Net-(U302-VCAP)` | regulator cap | — | ok |
| 32 | VSS | `GND` | ground | — | ok |
| 33 | GND | `GND` | exposed pad | — | ok |

#### The AF check finds one real constraint: both SPI groups are SPI1

This is the finding worth the exercise. The `/LPS_*` group looks like a second SPI
bus, but the datasheet says otherwise:

```text
AT25 group   PA5 SPI1_SCK    PA6 SPI1_MISO    PA7 SPI1_MOSI     all AF5
LPS  group   PB3 SPI1_SCK    PA11 SPI1_MISO   PA12 SPI1_MOSI    all AF5
```

**PA11 and PA12 carry SPI1_MISO and SPI1_MOSI — the same peripheral signals as PA6
and PA7.** There is no second SPI on those pins: across AF0–AF15, PA11's only other
peripheral is FDCAN1_RX and PA12's is FDCAN1_TX. An STM32 routes each SPI signal to
exactly one pin at a time, so `/AT25_MISO` and `/LPS_MISO` cannot both be live.

Nor is SPI3 an escape route. PB3 does offer `SPI3_SCK` on AF6, but SPI3's data pins
are `SPI3_MISO` on PB4 and `SPI3_MOSI` on PB5 — and those are wired to `/LSM_TRG`
and `/BMM_INT`.

So the BMP581 can be reached in one of two ways, and firmware has to pick:

1. **Remap SPI1 at runtime** — rewrite `GPIOA->AFR` to move MISO/MOSI between
   PA6/PA7 and PA11/PA12, and SCK between PA5 and PB3, whenever switching between
   the flash/IMU group and the BMP581. Correct, but the mode switch has to be
   airtight against leaving two devices' pins in AF mode simultaneously.
2. **Bit-bang the BMP581 bus in software** — consistent with the house convention
   already used for the RV-3028 I²C, and at BMP581 data rates entirely adequate.

Neither is a board defect and no rework is implied — the wiring supports both. But
this is not "two SPI buses," and firmware written on that assumption will not work.
Worth settling before firmware bring-up rather than during it.

#### The symbol's pin numbering is correct

ST's data also carries the package pin positions, which is a free check on something
DRC and ERC both pass silently: a symbol whose pin numbering does not match the real
package. **All 25 GPIO positions agree** — PA5 on pin 11, PB7 on pin 30, and so on
through the whole map. This is the automated form of the "verify pinouts against the
manufacturer, never the symbol" rule.

#### The 32 kHz timebase: RTC → LSE bypass → LPTIM1 → LSM

This is the part of the design the pin map exists to make visible, and it is worth
stating explicitly because two pins look inert until you see how they connect.

```text
U501 RV-3028 CLKOUT (32.768 kHz, 1 PPM)
   -> PC14 / OSC32_IN, LSE in bypass mode
      -> LPTIM1, divided
         -> PB4 / LPTIM1_CH2 (AF1)
            -> U5 LSM6DSV trigger
```

**PC14 carries `RCC_OSC32_IN`.** It has no *alternate* functions — every AF column
is empty except EVENTOUT — but ST lists `RCC_OSC32_IN` as an **additional function**,
selected through peripheral registers rather than `GPIOx_AFR`. DS14861 confirms the
mode: *"In bypass mode, the LSE oscillator is switched off and the input pin is
directly connected to the LSE clock detector."* So the RV-3028's output is not being
read as a GPIO signal — it is **driving the LSE**, giving the MCU a 1 PPM timebase
with no crystal anywhere on the tag.

**PB4 is `LPTIM1_CH2` on AF1**, not a GPIO. LPTIM1 divides that 32 kHz and drives the
LSM6DSV trigger in hardware, so sampling continues while the CPU is stopped — which
is what makes the 1–2.2 mA budget achievable. The trigger interval inherits the
RV-3028's 1 PPM accuracy rather than an internal RC oscillator's.

The alternative `LPTIM1_CH2` pin is PA1, which is unused, so nothing is contended.

> **Correction.** An earlier revision of this review called PC14 a plain GPIO input
> that "costs you the LSE," and then reasoned that the accurate 32 kHz could not
> reach LPTIM1 because `LPTIM1_IN1`/`IN2`/`ETR` (PB5/PB6/PB7) are all occupied. Both
> claims were wrong, and from the same root cause: the check read only *alternate*
> functions and ignored *additional* functions, so `RCC_OSC32_IN` was invisible. The
> clock reaches LPTIM1 through the RCC tree, not through an LPTIM input pin. The
> helper now reads both, and reports additional functions explicitly.

#### One pin gives something up

**PB3's AF0 is JTDO/TRACESWO.** Using it for `/LPS_CK` forfeits SWO trace output.
SWD itself is unaffected — PA13/PA14 are untouched on AF0 — so debugging works, you
just cannot use single-wire trace. Similarly PB4's AF0 is NJTRST, given up for
`LPTIM1_CH2`, which is irrelevant under SWD.

#### The rest of the map

**Two device groups, one peripheral.** U5 (LSM6DSV) and U6 (NAND) share
`/AT25_SCK`, `/AT25_MISO` and `/AT25_MOSI` on PA5–PA7 with independent selects —
PA4 for the NAND, PB1 for the IMU. Both selects are plain GPIO, correctly: PB1 has
no SPI alternate function at all, and PA10 has no `SPI_NSS`. With no external
pull-ups, keeping both inactive is a reset-state and first-GPIO-action contract.

**PB7 is BOOT0**, carrying `/SDA` on AF4 (`I2C1_SDA`) with a 10 kΩ pull-up to
`+1V8`, so the strap is high at reset. Production programming must write and read
back the option bytes. Unchanged from Review 1 and still the most important
firmware-side item on the board.

**Six GPIOs are unused** — PC15, PA1, PA2, PA3, PB0, PA15. Configure them
analog/no-pull for lowest leakage. PA15 is the one to be deliberate about, being the
only unused pin with a default pull-up on STM32.

### Production package — 2026-09-02-08-29-52

Current PCBWay export, verified against the board on disk.

| Check | Result |
|---|---|
| Inner-plane fill vs board | **300/300** sampled vertices match on both In1.Cu and In2.Cu |
| Track geometry | **412/412** F.Cu + B.Cu segment starts present |
| Superseded exports | pruned — only the current one is kept |
| Copper to board edge | **0.3005 mm** on both inner planes |
| Drill reconciliation | PTH **47 holes = 47 vias**, single 0.20 mm tool; NPTH **4 × 1.1 mm** |
| BOM / CPL | 17 lines, **30 placements**, exact CPL match, every line with MPN and LCSC |
| KiCad DRC | 0 violations, 0 unconnected, 0 parity |
| KiCad ERC | 0 violations with 24 exclusions; **0 errors with exclusions cleared** — finding 5 |

The board was saved 5 seconds *after* the export ran; the geometry match confirms the
export is current, so that gap was just the save landing after the plot. Same pattern
as the previous two exports — worth checking each time rather than assuming.

Three exports are now retained. Per `CLAUDE.md`, prune to the one actually ordered
once that decision is made, and force-add its gerber archive past the repo-wide
`*.zip` ignore rule so the fabricated package is recoverable from the commit.

There is no `.gbrjob`, as with every PCBWay-plugin export in this repo — not a defect.

**Not yet ordered, and one architectural question is still open** — see finding 1.
The files are ready; the decision behind them is not.

### Verified correct

Checked and fine — recorded so the next review does not redo them.

- **TPS62840 configuration matches the datasheet.** VSET tied directly to GND
  selects **1.8 V** on the TPS62840YBG variant — confirmed against Table 1, whose
  first row reads `0.8 | 1.8 | 1.8 | 0 | GND | 0.01 k`, the only row where the
  nominal resistance is "GND". EN tied to VBAT means the rail is always on when the
  battery is present. 2.2 µH with 4.7 µF in and 10 µF out.
- **KiCad DRC is clean in place** — 0 violations, 0 unconnected, 0 parity.
- **Edge clearance and annular ring are done** — 0.3005 mm on both inner planes,
  all 47 vias at 6.00 mil, single drill size.
- **Plane structure is the house standard** — In1.Cu `+1V8`, In2.Cu `GND`, with a
  local F.Cu GND pour at the converter and an F.Cu keepout under L1.
- **The two ERC `pin_to_pin` warnings** on U6 `WP`/`HOLD` against a power flag are
  the accepted pattern from Review 1, unchanged.
- **`VBAT`/`VIN` on one net** is the deliberate fixed-interface inheritance, same
  as the sibling.

Not re-examined, because they are settled house conventions recorded in
`imutag-nand-bmp581/.kicad-happy.json` and `CLAUDE.md`: zero solder-mask expansion,
vias inside exposed pads, exposed-pad paste ratios, UltraLibrarian and vendor
footprint land geometry, absence of a `.gbrjob`, no external I²C or chip-select
pull-ups, panel fiducials, and `/clkout` as a low-risk 32 kHz net.

### Corrections to Review 1

- **Findings 7 and 8 were derived from a poisoned analysis run.**
  `analysis/2026-08-26_0809/pcb.json` has
  `project_settings.source = BitTagNG-LIS2DU12.kicad_pcb-back.kicad_pro`, so its
  DFM thresholds and rule comparisons are against BitTagNG's project, not this
  board's. The stale file was removed repo-wide on 2026-09-01; re-run the analyzer
  before relying on any rule-derived number here.
- **Finding 5's premise needs the qualifier in finding 1.** "Keep the SMPS if the
  energy budget requires it" is still the right call, but the energy advantage is
  larger than a forced-PWM comparison implies, and the noise is less controllable.

### Before-fab checklist

1. Decide finding 1 deliberately: accept PFM-only operation, or move to a package
   that exposes MODE. This is the one architectural question left.
2. Measure magnetometer noise against an assembled `imutag-nand-bmp581` before
   committing a build quantity.
3. Re-run the analyzer now that the poisoned project file is gone, and check
   `project_settings.source` names `imutag-smps.kicad_pro`.
4. Update U3's BMP581 symbol from the library and re-export — verified safe, no new
   ERC violations. ~~Pending~~ **still open after the 2026-09-02 pass.**
5. State on the order: 4 layers, 0.4 mm finished thickness, surface finish. The
   stackup still reads `copper_finish "None"`, and the immersion-silver reasoning
   from the sibling review applies here with more force, since this board has an
   inductor as well.
6. Commit and tag before ordering, per `CLAUDE.md`.

Done since Review 2 opened: the L1 reroute (finding 2) and the first PCBWay export,
both verified above.

---

## Review 1 — 2026-08-26

Retained below. Note the correction above: findings 7 and 8 were measured against
BitTagNG's design rules, not this board's, and both are superseded by the
2026-09-01 rule and geometry changes.

Review date: 2026-08-26  
Project: `BoardDesigns/imutag-smps`  
Primary design files: `imutag-smps.kicad_sch`, `imutag-smps.kicad_pcb`, `imutag-smps.kicad_pro`  
Datasheet source used: `BoardDesigns/libraries/datasheets`  
Current analysis run: `analysis/2026-08-26_0809`

### Verdict

The design is electrically close: schematic and PCB component counts match, all nets are routed, KiCad DRC reports zero violations and zero unconnected items, and the main power topology matches the relevant datasheets. I would not treat the raw analyzer "U6 has no DC power path" and "LSM6DSV SPI pins need I2C pull-ups" reports as real electrical blockers.

I would still do a focused documentation/manufacturing cleanup before fab. The main remaining issues are the required STM32 BOOT0 option-byte programming step, the stale schematic pin-map note, and several assembly/process constraints that need an intentional fab/assembly decision. The SMPS rearrangement improves the magnetometer tradeoff: the inductor axis no longer points at the BMM350.

The analyzer's "plane split", "island", and "plane gap" language has been manually downgraded. GND and +1V8 are understood to be fully connected planes. The reported "gaps" occur where vias and antipads exist at layer changes, which is expected PCB geometry rather than a plane-connectivity defect. The `/clkout` net is also only 32 kHz, so its flagged crossing is not a high-speed EMC concern.

### Review Basis

Tools and files checked:

- KiCad ERC: 3 warnings, 0 errors.
- KiCad DRC: 0 violations, 0 unconnected items.
- Schematic analyzer: 22 findings, including 3 errors that were manually triaged against datasheets.
- PCB analyzer: 49 findings, including 2 fiducial findings that are covered by the fab house's panel process, plus DFM warnings.
- Cross-analysis: 10 findings after the U5 metadata fix; remaining return-plane/plane-split findings are geometry heuristics and were manually downgraded.
- EMC analyzer: 64 findings, risk score 26.5. The plane/reference findings remain manually downgraded as geometry heuristics.
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

User-confirmed design intent: U5 is `LSM6DSV`. The PCB metadata has since been updated and now reports U5 value and MPN as `LSM6DSV`.

### Previous Review Delta

Compared with the initial 2026-08-25 analysis:

- U5 metadata is fixed: PCB value and MPN now both report `LSM6DSV`.
- L1 was rotated from 0 degrees to -90 degrees.
- U2-to-L1 center spacing is essentially unchanged, moving from about 11.49 mm to about 11.15 mm.
- The L1 axis is now about 89 degrees from the L1-to-U2 vector, so the inductor axis is effectively perpendicular to the direction of the BMM350.
- U4 output-cap placement improved: C8 moved from about 3.97 mm from U4 to about 1.18 mm from U4. C7 remains close at about 1.21 mm.
- DRC remains clean: 0 violations and 0 unconnected items.
- ERC remains at 3 warnings, matching the earlier review.

### Current Findings

#### 1. U5 metadata is resolved

Severity: resolved  
Confidence: high  
Evidence: raw PCB file, refreshed PCB analyzer output, shared datasheet library, user-confirmed design intent

The intended part is `LSM6DSV`. The schematic/BOM and PCB footprint properties now identify U5 as `LSM6DSV`, and the shared datasheet directory contains `lsm6dsv.pdf`.

Original concern:

- The earlier PCB metadata identified U5 as `LSM6DSV16X` / `LSM6DSV16XTR`.
- That has been corrected in the PCB file and in the refreshed PCB analyzer output.

Remaining action:

- None for U5, other than using the refreshed manufacturing outputs.

#### 2. Analyzer plane-gap findings are not plane-connectivity defects

Severity: low / advisory  
Confidence: high for the manual override; medium for any residual EMC margin concern  
Evidence: cross-analysis and EMC analyzer, user layout review, user-confirmed `/clkout` frequency, KiCad DRC is clean

The cross-check still reports several "plane gap" and "plane split" findings:

- `/clkout` crosses a VBAT plane gap, but this is user-confirmed as a 32 kHz clock and is therefore low risk.
- `SWCLK` crosses a GND plane gap.
- `/LPS_MOSI`, `/LPS_MISO`, `/AT25_MISO`, `/AT25_SCK`, and `/AT25_MOSI` cross GND plane gaps.
- Plane split summary: VBAT has 4 islands, GND has 18 islands, and +1V8 has 6 islands.

Manual interpretation:

- "Islands" means the analyzer found separate filled polygon/reference-sampling regions. It is not proof that GND, +1V8, or VBAT are electrically disconnected.
- The GND and +1V8 planes are understood to be fully connected.
- The flagged crossings occur at routing-layer changes, where via antipads necessarily create local holes in adjacent copper.
- A perfectly continuous plane reference directly through a via transition is impossible; the practical question is whether the transition has adequate nearby return-current path for the signal edge rates.

Why it matters:

- These are short traces on a very small board, so the absolute loop sizes are limited.
- The 32 kHz `/clkout` trace is not a high-speed EMC driver.
- SPI and SWD nets can still have fast edges, so nearby return continuity is useful for EMC margin, but this is an advisory layout-quality item rather than a blocker.

Recommendation:

- Do not treat the analyzer's island counts as disconnected-plane evidence.
- Optionally add nearby GND return vias at fast-edge signal layer transitions if EMC margin becomes important.
- Treat `/clkout` as low priority unless it is routed off-board or used as a sensitive timing reference.

#### 3. Fiducials are supplied by the fab panel, not the board

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

#### 4. PB7/BOOT0 use requires an option-byte programming step

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

#### 5. Magnetometer offset is an accepted SMPS tradeoff, improved by the rearrangement

Severity: very low / validation item  
Confidence: high  
Evidence: PCB footprint coordinates, BMM350 datasheet role as geomagnetic sensor, user-confirmed power architecture tradeoff

U2 BMM350 is placed on the right side of the board. After the SMPS rearrangement, the center-to-center spacing from U2 to the TPS62840 inductor L1 is about 11.15 mm; spacing to U4 is about 12.66 mm. L1 is now rotated to -90 degrees, and the L1-to-U2 vector is almost horizontal, so the inductor axis is about 89 degrees away from pointing at the BMM350.

Why it matters:

- The buck inductor, battery current path, nearby ferromagnetic parts, and assembly hardware can create magnetic offset.
- BMM350 accuracy may vary with regulator load state and mechanical mounting.
- The alternative is using an LDO, which would carry a significant energy cost for this design.
- The revised inductor orientation is the right direction for this tradeoff; residual error is now primarily a calibration/validation item.

Recommendation:

- Keep the SMPS if the energy budget requires it.
- Measure magnetometer offsets with the buck enabled at idle and at expected peak load.
- Treat calibration data as assembly-specific.
- Revisit the LDO option only if measured magnetic error cannot be calibrated out for the intended use case.

### Medium Priority Findings

#### 6. I2C pull-ups are acceptable for light capacitance but should be verified at 400 kHz

Severity: medium  
Confidence: medium-high  
Evidence: schematic analyzer and protocol check

The real I2C bus is `/SDA` and `/SCL`, shared by U2 BMM350, U501 RV-3028-C8, and U302. R2 and R3 are 10 kOhm to +1V8.

The analyzer estimates about 212 ns rise time at 25 pF, which fits 400 kHz fast-mode rise-time limits. At higher bus capacitance, 10 kOhm can become marginal.

Recommendation:

- Keep 10 kOhm if the bus is short and measured rise time is acceptable.
- If using 400 kHz and the measured rise time is slow, consider 4.7 kOhm or lower-power firmware scheduling tradeoffs.

#### 7. Advanced PCB process assumptions are baked into the layout

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

#### 8. Edge clearance and via-in-pad details need assembly review

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

#### 9. Test coverage is minimal

Severity: medium  
Confidence: high  
Evidence: PCB analyzer

The analyzer found 0 dedicated test points across 36 signal nets. The design does have connectors/SWD access, but production test and bring-up would benefit from intentional pads.

Recommendation:

- At minimum, make VBAT, +1V8, GND, RST/NRST, SWDIO, SWCLK, `/SDA`, `/SCL`, and `/FLASH_PWR` easy to probe.
- If board area is too tight, document which connector pads are the official test access points.

#### 10. Schematic pin-map note is stale

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

### Checks That Passed

#### TPS62840 1.8 V buck configuration

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

#### TPS22916 flash load switch

Confidence: high  
Evidence: TPS22916 datasheet and net trace

U1 is wired consistently:

- VIN: +1V8
- VOUT: `/Flash 1V8`
- ON: `/FLASH_PWR` from U302 PA8
- GND: GND

The B variant has fast turn-on behavior. With about 1.1 uF on `/Flash 1V8` near the flash, estimated inrush is modest. Firmware must still ensure the flash is not powered down during write/erase/program operations.

#### GD5F2GM7RE SPI NAND pinout and power

Confidence: high  
Evidence: GD5F2GM7RE datasheet and U6 pad nets

U6 pin mapping matches the datasheet for standard SPI:

- CS#, SO/SIO1, SI/SIO0, and SCLK route to the AT25 SPI bus nets.
- VCC is on `/Flash 1V8`.
- WP#/SIO2 and HOLD#/SIO3 are tied high to `/Flash 1V8`.

This is acceptable for standard SPI operation and explains the KiCad ERC warnings about bidirectional pins connected to a power flag. The tradeoff is that Quad SPI/DTR modes are unavailable unless SIO2/SIO3 are routed to the MCU.

#### BMM350 CRST implementation

Confidence: high  
Evidence: BMM350 datasheet and U2/C4 net mapping

The analyzer warning that U2 CRST needs a pull-up is a false positive. The BMM350 datasheet requires a 2.2 uF capacitor on CRST. The design has C4 = 2.2 uF from `Net-(U2-CRST)` to GND and places it near U2, about 1.9 mm by analyzer distance and about 2.37 mm center-to-center from U2.

#### STM32U375 supply support

Confidence: high  
Evidence: STM32U375 datasheet and schematic/PCB net mapping

The MCU supply arrangement is broadly correct:

- VDD and VDDA are tied to +1V8, within the 1.71 V to 3.6 V operating range.
- VCAP has C12 = 4.7 uF to GND.
- Decoupling capacitors are present near U302.
- NRST is pulled/controlled through Q501, and the PMBT2222AMB pinout matches the intended collector/emitter/base use.

### Analyzer False Positives and Overrides

#### U6 VCC no DC path to power rail

Raw finding: schematic `PP-001` and `RS-001` for `/Flash 1V8`  
Disposition: false positive / documentation cleanup

The analyzer does not understand that U1 TPS22916 VOUT is the source for `/Flash 1V8`. The datasheet and net trace confirm that U1 A1/VOUT feeds U6 VCC and the local flash capacitors.

Recommended cleanup:

- Add a PWR_FLAG or improve the U1 symbol pin type/regulator mapping so ERC-style tools understand `/Flash 1V8`.

#### AT25_MOSI / AT25_SCK missing I2C pull-ups

Raw finding: schematic `PR-001`  
Disposition: false positive if U5 is operated in SPI mode

The LSM6DSV-family pins are dual-use I2C/SPI pins. Its datasheet states that CS high selects I2C and CS low selects SPI. In this design, U5 has `/LSM_CS`, so SPI use is plausible and no I2C pull-ups are needed on `AT25_MOSI` or `AT25_SCK`.

Firmware contract:

- Keep all chip selects inactive except the selected device.
- Drive U5 CS appropriately so the IMU stays in the intended serial mode.
- U5 PCB metadata now consistently names the intended LSM6DSV part.

#### KiCad ERC warnings on U6 WP/HOLD tied high

Raw finding: ERC bidirectional pins connected to power output flag  
Disposition: acceptable for standard SPI; update symbols/flags if desired

The flash datasheet says unused WP#/SIO2 and HOLD#/SIO3 must be driven high or pulled high. Tying them to `/Flash 1V8` is correct for standard SPI.

### Datasheet and Library Hygiene

- The shared library path used for this review was `BoardDesigns/libraries/datasheets`.
- U302's datasheet property points at an older absolute path under `hardware/libraries/datasheets/stm32u375ce.pdf`; the actual shared file is under `BoardDesigns/libraries/datasheets/stm32u375ce.pdf`.
- U5 datasheet coverage is complete for the intended `LSM6DSV` part, and PCB metadata now matches.
- No missing MPNs were reported by the schematic analyzer.

### Suggested Before-Fab Checklist

1. Add/read-back-verify the STM32 BOOT0 option-byte write in the programming flow.
2. Update the stale schematic pin-map text note.
3. Confirm advanced PCB process assumptions with the intended fab.
4. Review J401 via-in-pad and exposed-pad paste/via treatment with the assembler.
5. Document that the fab house supplies panel fiducials for both assembled sides.
6. Add probe/test access or document connector-based test access.
7. Treat the analyzer's return-plane findings as advisory geometry checks unless later EMC testing points back to them.
8. Run fresh ERC, DRC, cross-analysis, and EMC checks after any further layout edits.

