# UIUCBreakout — design review

**Date:** 2026-09-05
**Board:** `UIUCBreakout.kicad_pcb` / `.kicad_sch`, 4 layer, 48.26 × 48.26 mm
**Role:** daughtercard for `tag-breakout-l432v2`, used to develop firmware for `BitPresTagBMP585`
**Reviewer brief:** confirm the header pinout reproduces `BitPresTagBMP585` on the L432; account for the
known SCL/SDA swap on the mating baseboard.

## Verdict

The board does the job it exists for. **Every signal on both headers lands on the same STM32L432 pin as
on `BitPresTagBMP585`** — 17 signal nets, no exceptions — so firmware moves between the dev rig and the
tag without a pin-map change. Netlist, packages, footprints, DRC and the schematic↔PCB pad-net
cross-check are all clean.

Two things to fix before ordering, one of which would produce a dead board if the committed files were
sent as-is. Neither is a schematic change.

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

On `tag-breakout-l432v2`, U6 (RV-3028-C7) pin 3 `SCL` → net `/stm32/rtc_scl` → J3.3 → **PB7**, which
is `I2C1_SDA`; U6 pin 4 `SDA` → `/stm32/rtc_sda` → J3.4 → **PB6**, which is `I2C1_SCL`. The net names
and the silkscreen are swapped relative to the MCU's pin functions.

UIUCBreakout leaves J3.3 and J3.4 unconnected, so nothing on this board is affected. But note the
consequence for firmware portability, since it is the one place the dev rig differs from the tag:

- On `BitPresTagBMP585`, PB6 = `/SCL` and PB7 = `/SDA` — correct.
- On the dev rig, the RTC (on the *baseboard*, U6) requires PB6 driven as SDA and PB7 as SCL.

So RTC driver code developed on this rig must be conditionally swapped for the tag. Everything else
ports unchanged. See finding **L1** — the silkscreen currently propagates the wrong names.

## 3. Findings

### M1 — The committed Gerber set is a 2-layer plot of a 4-layer board; it would fab a dead board

`jlcpcb/gerber/` as committed contains `CuTop` and `CuBottom` but **no `CuIn1` / `CuIn2`**. The
board is 4 layers, and In1.Cu carries the entire `+3.3V` plane.

This is not cosmetic. `+3.3V` has only 12.3 mm of F.Cu track and 4 vias down to the In1 plane, and
critically:

```
J3.7  on-layer-track = False
J4.1  on-layer-track = False      # the two +3.3V supply pins from the baseboard
```

Both header supply pins reach the rest of the board **only through the In1 plane**. Fabricated from
the committed Gerbers, the board would receive no power at all. (GND survives — it has F.Cu and
B.Cu pours as well as In2.)

The working tree is already correct: `UIUCBreakout-CuIn1.gbr` and `-CuIn2.gbr` were regenerated
today and are present but untracked, and `jlcpcb/production_files/GERBER-UIUCBreakout.zip` (the
archive you would actually upload) contains all four copper layers plus both drill files.

**Fix:** commit the two inner-layer Gerbers, force-add the archive
(`git add -f jlcpcb/production_files/GERBER-UIUCBreakout.zip` — `BoardDesigns/.gitignore` excludes
`*.zip`), and stage the two stale `TorporTagBreakout-*-drl_map.pdf` deletions.

### M2 — The tracked BOM/CPL in `production/` is missing R1 and C4; R1 is in the power path

`production/bom.csv` (2026-08-20, tracked) lists C1, C2, C3, C5, C7, U1, U2, U3 — and omits
**R1 (10 Ω)** and **C4 (0.22 µF)**. `production/positions.csv` omits them too.

- **R1 is in series in the BMP585's supply.** Not placing it leaves `LPS_PWR` open and U3 unpowered.
- **C4 is mandatory.** ADXL367 datasheet Table 9, note 1: VREG_OUT "is used as an internal supply
  decoupling pin, an external 0.2 μF capacitor is needed."

Today's regenerated `jlcpcb/production_files/BOM-UIUCBreakout.csv` and `CPL-UIUCBreakout.csv`
include both, and are correct. **Fix:** delete or replace the stale `production/` CSVs so the
incomplete pair cannot be picked up by mistake.

### M3 — U1 SIO2/SIO3 are hard-tied to +3.3V, not pulled up

`U1.3 (WP#/IO2)` and `U1.7 (HOLD#-RESET#/IO3)` connect directly to the `+3.3V` net. In single- and
dual-SPI this is the standard treatment and is fine. But per the AT25FF321A datasheet §3, when the
`QE` bit of Status Register 2 is set, both pins become **bidirectional quad-SPI I/O** — the device
would then drive them into a hard short to the rail.

On a board whose entire purpose is firmware development, "someone tries quad mode" is a realistic
path, and it is destructive rather than merely non-functional. This also produces the two ERC
`pin_to_pin` warnings (Bidirectional connected to Power output).

Note the target tag cannot hit this: `BitPresTagBMP585` uses the 12-ball WLCSP (`AT25FF321A-UUN-T`),
whose pinout breaks out only SO/SI — there is no IO2/IO3 to conflict.

**Recommendation:** replace the two direct ties with 10 kΩ pull-ups to +3.3V. Two 0603 parts, no
layout change of consequence, and quad-mode experiments become safe.

### L1 — Silkscreen at J3.3/J3.4 reproduces the baseboard's swapped names

The header silkscreen is otherwise excellent — every pin is labelled with both the L432 port and the
net (`PA5 LPS_SCK`, `AT25_nCS PA15`, …). But J3.3 and J3.4 are labelled `rtc_scl` and `rtc_sda`,
copied from the baseboard, which are exactly the names that are wrong. On a board that a student
will probe, that silkscreen will actively mislead.

Since both pins are NC here, label them `PB7` and `PB6` like every other pin, or `PB7 (rtc SDA)` /
`PB6 (rtc SCL)` to record the correction where someone will read it.

### L2 — ERC: 3 errors, 5 warnings, all cosmetic but worth clearing before ordering

```
ERROR   power_pin_not_driven   U3.4 VDDIO  (net /LPS_PWR)   ×2
ERROR   power_pin_not_driven   U2.10 VS    (net +3.3V)
WARNING pin_to_pin             U1.3 SIO2 / #FLG02           ] see M3
WARNING pin_to_pin             U1.7 SIO3 / #FLG02           ]
WARNING pin_to_pin             U2.7 GND / U2.11 GND         ] see L3
WARNING lib_symbol_mismatch    U2 ADXL367BCCZ-RL7           ]
WARNING four_way_junction      at (118.11, 181.61)
```

The single `PWR_FLAG` (#FLG02) sits on the U1 SIO2/SIO3 tie node. Moving it to J3.7/J4.1 — the
actual origin of `+3.3V` — and adding a second on `/LPS_PWR_IN` at J4.16 clears the three
`power_pin_not_driven` errors, and (with M3) the two `pin_to_pin` warnings.

### L3 — U2's cached symbol is stale; the library has since been corrected

`lib_symbol_mismatch` on U2 is benign. Diffing the embedded copy against
`libraries/tag_library.kicad_sym`: **pin numbers and names are identical**; only pins 7 and 11 (GND)
differ, `power_out` in the schematic's cached copy vs `power_in` in the library. The library is
right. Updating the symbol from the library clears both this warning and the `pin_to_pin` GND
conflict.

Pinout independently verified against the manufacturer PDF — see §4.

### L4 — No bulk capacitance on +3.3V; C7 is 10.7 mm from the flash it decouples

The `+3.3V` rail carries C1, C2, C7 — three 0.1 µF and nothing else. `BitPresTagBMP585` puts
22 µF + 47 µF on the equivalent VIN rail. The AT25FF321A draws ~15 mA during page-program and erase,
and its only local bypass is 10.7 mm away (C2 → U2 VDDIO is 12.3 mm; C1 → U2 VS is 2.6 mm, C3/C5 →
U3 are 4.1/4.2 mm, C4 → U2 VREG_OUT is 2.0 mm — those are fine).

The In1/In2 plane pair sits across a 1.24 mm core, so plane capacitance is ~65 pF and contributes
nothing. The baseboard's C10 (4.7 µF) is the nearest bulk, across two header pins.

Not a blocker on a plane-backed dev board at these currents, but a 4.7–10 µF 0603 on +3.3V near U1,
and C7 moved closer to U1.8, would make the flash's supply environment match the tag's.

### L5 — Value/MPN mismatch on C4, and the one that could actually bite

`C4` has `Value = "C"` with `MPN = CL10B224KA8NNNC` (0.22 µF). Per house convention the MPN is what
fab consumes, so the build is correct — but C4 is precisely the part where the required value is
unusual (0.2 µF, not 0.1 µF), and every other capacitor on the board reads `0.1uf`. Anyone hand-
populating from the schematic or the CPL (which prints `C4, C, C_0603_1608Metric`) will fit a
0.1 µF. Set `Value` to `0.22uf`.

### L6 — Cosmetic

- B.Silkscreen reads `Geoffrey Brown 95/2026` — presumably `9/5/2026`.
- J4.16 silk reads `LPS_PWR PB1`; the net at that pin is `LPS_PWR_IN` (pre-R1). `LPS_PWR` is the
  post-R1 rail. Minor, but it matters when probing which side of R1 you are on.
- Trailing whitespace/newline in the `PA7 ` and `PA6 LPS_RDY\n` silk strings.

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

## 6. Suggested order of work

1. **M1** — commit `CuIn1`/`CuIn2`, force-add the Gerber archive, stage the stale PDF deletions.
2. **M2** — remove the stale `production/` CSVs.
3. **M3** — 10 kΩ pull-ups on U1 SIO2/SIO3 (2 parts; schematic + a short reroute).
4. **L1, L5, L6** — silkscreen at J3.3/J3.4 and the date; C4 `Value` → `0.22uf`.
5. **L2, L3** — move/add PWR_FLAGs; update U2 from the library. Re-run ERC to zero.
6. **L4** — optional: 4.7–10 µF on +3.3V near U1; pull C7 closer to U1.8.
7. Re-run DRC and ERC on the **committed** state, then tag `review/UIUCBreakout-2026-09-05`.

Items 3 and 6 are the only ones touching copper. If you would rather order now, M1 and M2 alone are
sufficient to get correct boards — M3 is a safety margin against a firmware experiment, not a defect
in the board as drawn.
