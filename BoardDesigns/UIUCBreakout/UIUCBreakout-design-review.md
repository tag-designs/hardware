# UIUCBreakout — design review

**Date:** 2026-09-05 (findings raised) / 2026-09-05 (designer responses recorded)
**Board:** `UIUCBreakout.kicad_pcb` / `.kicad_sch`, 4 layer, 48.26 × 48.26 mm
**Role:** daughtercard for `tag-breakout-l432v2`, used to develop firmware for `BitPresTagBMP585`
**Reviewer brief:** confirm the header pinout reproduces `BitPresTagBMP585` on the L432; account for the
known SCL/SDA swap on the mating baseboard.

## Verdict

The board does the job it exists for. **Every signal on both headers lands on the same STM32L432 pin as
on `BitPresTagBMP585`** — 17 signal nets, no exceptions — so firmware moves between the dev rig and the
tag without a pin-map change. Netlist, packages, footprints, DRC and the schematic↔PCB pad-net
cross-check are all clean.

All findings are closed. M1, M2 and L1-L6 are fixed; **M3 is accepted as-is** on the designer's
reasoning, which is better than the review's - see below. One review finding, L4, was **raised in
error** and is corrected here.

Closing state: DRC 0 violations / 0 unconnected, ERC 2 warnings (both intrinsic to the accepted M3,
0 errors), pad-net cross-check 79/79, drill reconciliation 61 = 61. **Ready to order.**

---

## 1. Pin-map equivalence with BitPresTagBMP585

Chain: UIUCBreakout `J3`/`J4` pin → `tag-breakout-l432v2` `J3`/`J4` → `U3` STM32L432KCU6 port →
`BitPresTagBMP585` `U302` net. AF numbers from `kicad-helpers/af_tables/stm32l432.json`
(generated from `STM32_open_pin_data`).

| Hdr pin | L432 pin | UIUCBreakout net | Drives | BitPresTagBMP585 net | Match | AF available |
|---|---|---|---|---|---|---|
| J3.1 | PB4 | AT25_MISO | U1 AT25FF321A SO | AT25_MISO | yes | AF4:I2C3_SDA, AF5:SPI1_MISO, AF6:SPI3_MISO, AF7:USART1_CTS |
| J3.2 | PB5 | AT25_MOSI | U1 AT25FF321A SI | AT25_MOSI | yes | AF1:LPTIM1_IN1, AF4:I2C1_SMBA, AF5:SPI1_MOSI, AF6:SPI3_MOSI |
| J3.3 | PB7 | — (NC) | — | SDA | see §2 | AF1:LPTIM1_IN2, AF4:I2C1_SDA, AF7:USART1_RX |
| J3.4 | PB6 | — (NC) | — | SCL | see §2 | AF1:LPTIM1_ETR, AF4:I2C1_SCL, AF7:USART1_TX |
| J3.5 | PB8 † | — (NC) | — | (not bonded) | n/a | pin absent on UFQFPN-32 |
| J3.6 | PB9 † | — (NC) | — | (not bonded) | n/a | pin absent on UFQFPN-32 |
| J3.7 | — | +3.3V | rail | VIN | yes | — |
| J3.8 | PA0 | WKUP1 | U2 ADXL367 INT1 | WKUP1 | yes | AF1:TIM2_CH1; add'l SYS_WKUP1, ADC1_IN5 |
| J3.9 | PA1 | ACCEL_nCS | U2 ADXL367 CS | ACCEL_nCS | yes | AF4:I2C1_SMBA, AF5:SPI1_SCK, AF7:USART2_RTS |
| J3.10 | PA2 | ACCEL_MOSI | U2 ADXL367 MOSI | ACCEL_MOSI | yes | AF7:USART2_TX (no SPI) |
| J3.11 | PA3 | ACCEL_MISO | U2 ADXL367 MISO | ACCEL_MISO | yes | AF7:USART2_RX (no SPI) |
| J3.12 | PA4 | ACCEL_SCK | U2 ADXL367 SCLK | ACCEL_SCK | yes | AF5:SPI1_**NSS**, AF6:SPI3_NSS, AF7:USART2_CK |
| J3.13 | PA5 | LPS_SCK | U3 BMP585 SCX | LPS_SCK | yes | AF5:SPI1_SCK, AF14:LPTIM2_ETR |
| J3.14 | PA6 | LPS_RDY | U3 BMP585 INT | lps_rdy | yes | AF5:SPI1_MISO, AF7:USART3_CTS |
| J3.15 | PA7 | — (NC) | — | — (NC) | yes | AF4:I2C3_SCL, AF5:SPI1_MOSI |
| J3.16 | PB0 | LPS_CS | U3 BMP585 CSB | LPS_CS | yes | AF5:SPI1_NSS, AF7:USART3_CK |
| J3.17 | — | GND | rail | GND | yes | — |
| J4.1 | — | +3.3V | rail | VIN | yes | — |
| J4.2 | PB3 | AT25_SCK | U1 AT25FF321A SCK | AT25_SCK | yes | AF5:SPI1_SCK, AF6:SPI3_SCK, AF7:USART1_RTS |
| J4.3 | PA15 | AT25_nCS | U1 AT25FF321A CS | AT25_nCS | yes | AF5:SPI1_NSS, AF6:SPI3_NSS, AF3:USART2_RX |
| J4.4 | PA12 | LPS_MOSI | U3 BMP585 SDX | LPS_MOSI | yes | AF5:SPI1_MOSI, AF7:USART1_RTS |
| J4.5 | PA11 | LPS_MISO | U3 BMP585 SDO | LPS_MISO | yes | AF5:SPI1_MISO, AF7:USART1_CTS |
| J4.6 | PA10 | — (NC) | — | — (NC) | yes | AF4:I2C1_SDA, AF7:USART1_RX |
| J4.7 | PA9 | — (NC) | — | — (NC) | yes | AF4:I2C1_SCL, AF7:USART1_TX |
| J4.8 | PA8 | — (NC) | — | — (NC) | yes | AF7:USART1_CK, AF14:LPTIM2_OUT |
| J4.9–J4.15 | PB15…PB2 † | — (NC) | — | (not bonded) | n/a | pins absent on UFQFPN-32 |
| J4.16 | PB1 | LPS_PWR_IN | R1 (10 Ω) → U3 BMP585 VDD+VDDIO | LPS_PWR | yes | AF7:USART3_RTS, AF14:LPTIM2_IN1, ADC1_IN16 |
| J4.17 | — | GND | rail | GND | yes | — |

† These nine baseboard header pins carry nets named `/stm32/PB2`, `PB8`–`PB15`, but the
STM32L432KCU6 in UFQFPN-32 has no such pins — on `tag-breakout-l432v2` those nets reach the header
and nothing else. Leaving them NC on the daughtercard is correct.

`LPS_PWR_IN` vs `LPS_PWR` is a rename only: on both boards PB1 feeds a 10 Ω series resistor into the
BMP585's tied VDD/VDDIO rail. UIUCBreakout names the pre-resistor node separately because the
resistor is on this board (R1); BitPresTagBMP585 uses R2 in the identical position.

### What the pin map tells firmware

- **BMP585 can use hardware SPI1.** PA5/PA11/PA12 are `SPI1_SCK`/`SPI1_MISO`/`SPI1_MOSI` at AF5, and
  PA11/PA12 have no SPI3 alternative — so SPI1 is forced here. PB0 (CS) as GPIO.
- **AT25 flash should use hardware SPI3.** PB3/PB4/PB5 carry both SPI1 (AF5) and SPI3 (AF6). Because
  the BMP585 group has already claimed SPI1, put the flash on **SPI3 (AF6)**; PA15 (CS) as GPIO.
  This resolves cleanly — there is no bus collision on this board.
- **The ADXL367 bus cannot use any SPI peripheral.** PA4 is `SPI1_NSS`/`SPI3_NSS`, not SCK; PA2 and
  PA3 have no SPI alternate function at all. This is inherited from BitPresTagBMP585, not introduced
  here — but it is worth stating plainly because this board exists for firmware bring-up.
  **The non-obvious option: USART2 in synchronous master mode maps exactly onto this wiring** —
  PA4 = `USART2_CK` (AF7), PA2 = `USART2_TX` (AF7), PA3 = `USART2_RX` (AF7), PA1 = CS as GPIO.
  The ADXL367 is SPI mode 0 and USART sync master supports CPOL=0/CPHA=0 with `CR2.MSBFIRST`, so
  this is a hardware alternative to bit-banging. Worth prototyping on this rig, since the same
  option exists on the tag.
- **Reset states already work in your favour.** PA15 (AT25 CS) is JTDI with a default pull-up, and
  PB4 (AT25 MISO) is NJTRST with a default pull-up — the flash comes out of reset deselected without
  an external resistor. This is the "no external CS pull-ups" house contract holding by construction.
- **PB3 (AT25_SCK) forfeits TRACESWO** — it is JTDO/TRACESWO at AF0. SWD two-wire debug is unaffected.
- **PA9/PA10 (J4.7/J4.6) are free and carry USART1_TX/RX at AF7** — a console on the dev rig costs
  nothing and does not exist on the tag. Useful.
- BOOT0 is strapped to GND on the baseboard, same as on the tag. No option-byte work needed.

## 2. The known SCL/SDA swap on tag-breakout-l432v2

Confirmed in the files, and it does **not** touch this daughtercard.

**It is a wiring error, not a naming error** — a distinction worth stating precisely, because it
decides how the daughtercard should label these pins. The baseboard's net names are *accurate*:
`/stm32/rtc_scl` really does carry the RTC's SCL, and `/stm32/rtc_sda` really does carry its SDA. What
is crossed is which MCU pin each signal landed on.

| RTC signal | Net (accurate) | Header | MCU pin | That pin's I²C1 role |
|---|---|---|---|---|
| U6.3 SCL | `/stm32/rtc_scl` | J3.3 | **PB7** | `I2C1_SDA` |
| U6.4 SDA | `/stm32/rtc_sda` | J3.4 | **PB6** | `I2C1_SCL` |

Verified against the manufacturer PDF rather than the KiCad symbol, since a mislabelled symbol would
have inverted this conclusion — Micro Crystal RV-3028-C7 Application Manual §2.2 gives **pin 3 = SCL**
("I²C Serial Clock Input") and **pin 4 = SDA** ("I²C Serial Data Input-Output"). The symbol is correct,
so the baseboard really does put the RTC's clock on PB7.

UIUCBreakout leaves J3.3 and J3.4 unconnected, so nothing on this board is affected. Two consequences
matter.

**Hardware I²C1 cannot drive the RTC on this baseboard at all.** PB7 can only ever be `I2C1_SDA`, so
the MCU would have to clock out of its data pin. The RTC must be bit-banged, with **PB7 as the clock
and PB6 as the data line**. Because the house already drives the RV-3028 with a slow software I²C
driver, this costs nothing operationally — which is why it has been fine in the field.

For a future baseboard spin: `I2C1` also maps to PA9 (SCL) / PA10 (SDA) on this package, both of which
reach J4.7 and J4.6 and are unused. That is where a hardware-I²C RTC would go, short of uncrossing
PB6/PB7.

**For firmware portability**, this is the one place the dev rig differs from the tag:

- On `BitPresTagBMP585`, PB6 = `/SCL` and PB7 = `/SDA` — correct, and hardware I²C1 would work.
- On the dev rig, the RTC sits on the baseboard and needs PB6 driven as SDA, PB7 as SCL.

So RTC driver code developed on this rig must be conditionally swapped for the tag. Everything else
ports unchanged.

## 3. Findings and dispositions

M1 and M2 were the two that would have produced unusable hardware. Both are fixed and committed
(`cf3eb53`). Everything below records what the designer decided.

### M3 - U1 SIO2/SIO3 hard-tied to +3.3V - ACCEPTED AS-IS

`U1.3 (WP#/IO2)` and `U1.7 (HOLD#-RESET#/IO3)` connect directly to the rail. In single- and dual-SPI
this is standard. Per the AT25FF321A datasheet section 3, setting the `QE` bit of Status Register 2
makes both pins bidirectional quad-SPI I/O, and the device would then drive them into a hard short.

**Designer response, accepted:** the target tag has no room for the two pull-ups, and this breakout is
the *preferred* place for a quad-mode failure to happen - the flash here is an 8-lead SOIC that can be
desoldered and replaced by hand, where the tag's part cannot.

This is a better position than the review took. The review treated "someone tries quad mode on the dev
board" as a risk to be designed out. It is more useful as a **deliberately cheap failure mode**: the
experiment is only survivable *because* it happens on this board, and running it here is the only way
to learn what the tag would do. Nothing to change.

Two consequences to record, so neither is re-raised:

- The two `pin_to_pin` ERC warnings (Bidirectional connected to Power output, U1.3 and U1.7) are
  **permanent and expected**. They are inherent to tying bidirectional pins to a net carrying a
  `PWR_FLAG` and cannot be cleared by moving the flag - ERC evaluates net-wide.
- The tag itself cannot reach this state at all: BitPresTag uses the 12-ball WLCSP, whose pinout breaks
  out only SO and SI. There is no IO2/IO3 to conflict, so quad mode is not available there either way.

### L1 — silkscreen at J3.3/J3.4 — FIXED

`rtc_scl` / `rtc_sda` are gone and the two pins now carry port names: **J3.3 = `PB7`, J3.4 = `PB6`**,
matching the baseboard. (A first attempt had the two inverted — the same trap the finding was about,
since the baseboard runs this pair in the order PB7, PB6 rather than the PB6, PB7 that pin order
suggests. Worth checking positions rather than merely confirming the strings changed.)

Labelling by MCU port rather than by the baseboard's net name is the right convention here, for three
reasons: the port is an invariant physical fact about the header pin, independent of anyone's view of
the baseboard; it is what every other pin on this board does; and it leads a reader to a correct
conclusion — "PB7, so that is `I2C1_SDA`". The alternative label `rtc_scl` would have been equally
*true* and still misleading, because it invites "SCL is here, so this is the clock pin, so `I2C1_SCL`,
so PB6" — precisely the reasoning that produced the baseboard error. A label can be accurate and still
walk the reader into the trap.

Optional refinement, not done and not needed: `PB7 rtc_SCL` / `PB6 rtc_SDA` would record both facts and
put the surprising one where someone will read it. These pins are NC on this board, so it is
documentation only, with no electrical consequence.

Confirmed in the shipped artwork, not just the board file: every coordinate in a fresh `kicad-cli` plot
of F.Silkscreen is present in the packaged `SilkTop.gbr` (zero fresh-only points), and the glyph stroke
counts corroborate the direction — J3.4's label carries 44 points against J3.3's 31, as a `6` needs
more strokes than a `7`.

### L2 - ERC - FIXED

`PWR_FLAG` count went 1 -> 3. All three `power_pin_not_driven` errors are gone, as is the
`four_way_junction` warning. ERC is now 8 violations -> **2 warnings**, both of them the accepted M3.

### L3 - stale U2 symbol - FIXED

The schematic's embedded `ADXL367BCCZ-RL7` now matches `libraries/tag_library.kicad_sym` pin for pin
and type for type. The `lib_symbol_mismatch` and the GND `pin_to_pin` warning are both gone.

### L4 - decoupling - RAISED IN ERROR; BULK ADDED

**The first half of this finding was wrong.** The review claimed "C7 is 10.7 mm from the flash it
decouples". It is not: C7 is *U2's* cap, 1.61 mm from the ADXL367's VS pin. The flash has C2 at
2.42 mm. The error was pairing capacitors to parts by reading reference designators instead of
measuring - the same class of mistake the repo's own notes warn about, applied to decoupling rather
than to a pinout.

Measured, nearest same-net capacitor to every supply pin on the board:

| Supply pin | Net | Nearest | Then |
|---|---|---|---|
| U1 AT25FF321A VCC | `+3.3V` | **C2 0.1 uF @ 2.42 mm** | C6 4.7 uF @ 4.12 mm |
| U2 ADXL367 VS | `+3.3V` | **C7 0.1 uF @ 1.61 mm** | C1 0.1 uF @ 2.59 mm |
| U2 ADXL367 VDDIO | `+3.3V` | **C1 0.1 uF @ 1.89 mm** | C7 0.1 uF @ 2.73 mm |
| U2 ADXL367 VREG_OUT | `Net-(U2-VREG_OUT)` | **C4 0.22 uF @ 1.97 mm** | - |
| U3 BMP585 VDD | `/LPS_PWR` | **C5 0.1 uF @ 1.78 mm** | C3 0.1 uF @ 4.14 mm |
| U3 BMP585 VDDIO | `/LPS_PWR` | **C3 0.1 uF @ 1.71 mm** | C5 0.1 uF @ 4.22 mm |

Every supply pin has a 0.1 uF within 2.73 mm. High-frequency decoupling was never a problem on this
board.

The second half stands and has been addressed: there was no bulk capacitance on `+3.3V`, against
22 uF + 47 uF on the tag. **C6 (4.7 uF) added, 4.12 mm from U1.8** - the flash is the only part here
that draws real current, so that is the right place for it.

### L5 - C4 Value field - FIXED

`Value` now reads `0.22uf`, and the regenerated BOM line is `0.22uf,C4,C_0603_1608Metric,C21120,1`.
Anyone hand-populating now sees the right number.

### L6 - cosmetic - FIXED

Back silkscreen reads `Geoffrey Brown 9/5/2026`; J4.16 reads `LPS_PWR_IN PB1`, matching the net; the
trailing whitespace and newline in the `PA7` and `PA6 LPS_RDY` strings are gone.

## 4. Verified clean

**Pinouts, against manufacturer PDFs (not against the symbols):**

| Part | Source | Result |
|---|---|---|
| BMP585 | `bst-bmp585-ds003.pdf` Table 26, p.45 | 9/9 exact. Pin 9 `L/M` is the lasermarking pad — "No external connection possible due to S/R coverage" — correctly left NC |
| ADXL367 | `adxl367.pdf` Table 9, p.13 | 12/12 exact |
| AT25FF321A | `REN_DS-AT25FF321A-181R_DST_20241219.pdf` Fig. 2 / Table 1, p.8 | 8/8 exact for the SOIC-8 pinout |

**Package / footprint:** `AT25FF321A-SHN-B` is, per the ordering table (Table 37, p.104), the
**8-lead 208-mil wide EIAJ SOIC** — *not* the 150-mil narrow part (`-SSHN-B`). The assigned footprint
`Package_SO:SOIC-8_5.3x6.2mm_P1.27mm` is described in KiCad as "based on JEITA/EIAJ 08-001-BBA,
208 mils width". Pads at x = ±3.5 mm, 1.9 × 0.6 mm, 1.27 mm pitch cover the datasheet's
E = 7.70–8.26 mm lead span with correct heel and toe. **Correct part/footprint pairing** — this was
worth checking, since the two SOIC widths differ by an unmistakable 2.6 mm and share a datasheet.

**R1 is a datasheet requirement, not a stray part.** BMP585 datasheet §6.2.5 Figure 27: "If VDD or
VDDIO ramp-up times are not controlled and are faster than 10 µs … the BMP585 inrush current should
be externally limited … using a 10 Ohm resistance." Driving the rail straight off a GPIO is exactly
that case. Bosch shows 10 Ω on each of VDD and VDDIO; a single 10 Ω into the tied rail limits total
inrush at least as well. Matches `BitPresTagBMP585` R2.

**Mechanical mating with tag-breakout-l432v2 — verified, no offset.** Both boards place J3 at
(106.68, 76.2) and J4 at (149.86, 76.2). The daughtercard's headers are on B.Cu at 180°, the
baseboard's on F.Cu at 0°, which mirrors the ±0.127 mm stagger — so individual hole centres differ
by 0.254 mm between the boards. This does **not** affect mating: the stagger is a per-board
hand-soldering friction fit, and both boards' hole centrelines are at exactly X = 106.68 and 149.86,
so the connector bodies coincide. Pin *n* mates with pin *n* (dy = 0 on all 34 positions). The same
B.Cu/180°/(106.68, 76.2) placement is used by CompassTagBreakout, IMUTagBreakout, IMUBreakout-v2,
BitPresTagBreakout, TorporTagBreakout and IMUTagNandBreakout — house standard.

**Electrical / layout:**

| Check | Result |
|---|---|
| KiCad DRC (in place, `--refill-zones`, `--severity-all`) | **0 violations, 0 unconnected** |
| Schematic↔PCB pad-net cross-check | **77 pads compared, 0 mismatches** |
| Copper-to-board-edge, nearest | **1.563 mm** (J3 pads) — very generous |
| Via annular ring | 0.152 / 0.155 mm — well above the 0.102 mm house floor |
| Via-in-pad | none |
| Silkscreen over SMD pad | none |
| Track widths | 381 mm at 0.1524 mm; 27 mm at 0.1016 mm (BMP585 LGA escape only) |
| Stackup | 1.6 mm, F.Cu–In1 0.1 mm / core 1.24 mm / In2–B.Cu 0.1 mm — stock JLCPCB 4-layer |
| Planes | In1 = +3.3V (2033 mm²), In2 = GND (2041 mm²), F.Cu + B.Cu GND pours |
| ADXL367 VREG_OUT cap | C4 = 0.22 µF, 2.0 mm from U2.9 — meets the datasheet's 0.2 µF requirement |
| BMP585 decoupling | 100 nF on VDD and 100 nF on VDDIO per datasheet Fig. 24 |

**Peripheral wiring vs BitPresTagBMP585:** U2 (ADXL367) and U3 (BMP585) are pin-for-pin identical,
including the unconnected pins (U2 INT2, U2 ADC_IN, U3 L/M). U1 differs only in package.

## 5. Housekeeping — the board directory still thinks it is TorporTagBreakout

Not design issues, but they will mislead the next review:

- **`.kicad-happy.json` describes TorporTagBreakout**, not this board: `project.name` is
  `"TorporTagBreakout"`, `mating_design.name` is `"TorporTag"`, and `host_pin_map` documents a
  TMP119 on PA1/PA2/PA3 with LEDs on J4.8/J4.16 — none of which exist here. Per the repo convention
  this file is what the next reviewer reads first, so it is currently worse than absent. A corrected
  version is written alongside this report.
- Tracked files belonging to the ancestor design: `TorporTagBreakout-analysis.md`,
  `CompassTagBreakout.kibot.yaml`, `RV3028.step`, `UIUCBreakout-rescue.dcm`.
- `datasheets/` holds the wrong parts entirely — `REN_DS-AT25XE321D-160P` (this board uses
  AT25**FF**321A), `RV-3028-C7`, `adxl362` (this board uses ADXL3**67**), `lis2dw12`, `tmp119`.
  None of the three parts actually on this board have a datasheet here. All three exist in
  `BoardDesigns/libraries/datasheets/` (`REN_DS-AT25FF321A-181R_DST_20241219.pdf`, `adxl367.pdf`,
  `bst-bmp585-ds003.pdf`); symlink to the shared store as other boards do.
- `jlcpcb/production_files/` still holds `BOM-`, `CPL-` and `GERBER-TorporTagBreakout.*`
  (gitignored, so cosmetic).
- No `analysis/` directory. If you want the analyzer JSON tracked, set `analysis.track_in_git: true`
  in the board's own config and leave a comments-only `.gitignore` in `analysis/` — `analyze_pcb.py`
  recreates that file unconditionally otherwise.

## 6. Closing out

**Nothing outstanding.** All nine findings are dispositioned: seven fixed, one (M3) accepted as a
design decision, one (L4) withdrawn as raised in error.

M3 is recorded in `.kicad-happy.json` under `accepted_decisions` rather than as an open finding, so the
two remaining ERC warnings are this board's expected steady state, not something for the next review to
chase.

Ready to tag `review/UIUCBreakout-2026-09-05`.

### Closing state, verified against the working tree

| Check | Result |
|---|---|
| KiCad DRC (`--refill-zones`, `--severity-all`) | 0 violations, 0 unconnected |
| ERC | 2 warnings, both the accepted M3 (was 8) |
| Schematic-to-PCB pad-net cross-check | 79 pads, 0 mismatches |
| Gerbers vs. saved board | 120/120 track starts; CuIn1/CuIn2 carry 2960 / 2739 coordinates |
| Drill reconciliation | 61 = 61 (0.2 mm x5, 0.3 mm x22 vias, 1.0 mm x34 header pins) |
| BOM / CPL | 11 parts each, including C4 0.22 uF and C6 4.7 uF |
