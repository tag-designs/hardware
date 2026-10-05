# tagbase-lipo-v1 — design review

**Date:** 2026-09-07
**Board:** `tagbase-lipo-v1.kicad_pcb` / `.kicad_sch` — 4 layer, 50.95 × 70.00 mm, 1.6 mm
**Role:** USB-powered base station that programs a tag over SWD and charges the tag's LiPo cell
through the 6-pin tagpoint connector.
**Status:** not previously fabbed; no `.kicad-happy.json` (one is offered with this review).

## Verdict

The design is coherent and the tricky parts are right — the op-amp pinout, the level-shifter
direction logic, and the charge-current resistor all check out against the manufacturers' own
documents. DRC is clean apart from one footprint issue, ERC is clean, and the schematic-to-PCB
netlist agrees on all 166 pads.

**Designer responses recorded 2026-09-07, and the XC6808 datasheet has since been added to the shared
store.** Of the six findings originally raised, one was real and is fixed, three were raised in error
and are withdrawn, and two are closed as intended behaviour.

The datasheet then produced two findings that outranked anything in the first pass, both against
explicit Torex requirements. **Both are now resolved**, and H3 was resolved by changing the part rather
than the circuit:

- **H3 — resolved by switching U2 to `XC6808A4C28R-G`.** On the `xN` variant pin 5 is `NF` and must be
  left open, which made R2 wrong. On the `A4` it is `THIN`, and R2 = 10 kΩ is the correct way to hold
  it in the normal-temperature window. The A4 is also less than half the price.
- **M3 — resolved.** C9 (1 µF) added at BAT, C10 (1 µF) added at VIN.

**All findings are now closed. The board is ready to order.**

The withdrawals are recorded in full below rather than deleted, because each one names a check that
looked conclusive and was not.

---

## 1. Board summary

| Block | Parts |
|---|---|
| MCU | U5 STM32L432KBU6, UFQFPN-32 (**128 KB** flash — the KB, not the KC) |
| USB | J104 Mini-B, U4 USBLC6-2P6 ESD, native USB on PA11/PA12 |
| 3.3 V | U1 XC6206P332MR from VUSB |
| 1.8 V | U3 AP2112K-1.8 from +3V3, enable on PB6 |
| Charger | U2 XC6808, 8.58 mA into the tag's cell, status on PA1 |
| Tag SWD | U7/U8 SN74LVC1T45 level shifters, 3.3 V ↔ 1.8 V |
| Tag sense | U6 TLV9001 unity-gain follower on TAG_3V3 → PA0 |
| Power select | SW1 (EXT_PWR / 3.3V), SW2 (→ TAG_3V3, or battery) |
| Debug | J102 FTSH-105 SWD, J5 UART TX, U105 DFU button, 2 LEDs |

The 3.3 V rail is derived from VUSB only — there is no battery path to the MCU. This is a bench
instrument, not a portable one, which is consistent with its purpose.

**The battery is on the tag, not on this board.** `/BAT` has exactly two pads — U2 pin 1 and SW2
pin 3 — and SW2 routes it to `TAG_3V3` → J101. I flag this because "LiPo Base" plus a charger and no
battery connector reads at first glance like a missing part; it is not.

## 2. Findings

### H3 — R2 grounds the NF pin, which Torex requires to be left open

`U2` is `XC6808ANC28R-G` — the **xN** variant. Pin 5's function depends on the variant, and the
datasheet is explicit about it in three separate places:

> **Pin assignment table:** `NF` — "No Function (**Please do not connect any terminal.**)"
>
> *"Pin name of #5 is THIN on the XC6808x2, XC6808x3 and XC6808x4, and **NF on the XC6808xN**."*
>
> **Notes on use, item 13:** *"On the XC6808xN, **please be sure to use the NF pin (pin #5) in the
> open state**."*

The board has **R2 = 10 kΩ from pin 5 to GND**. The typical application circuit for the `xN` variant
shows the NF pin with no external connection at all; only the `THIN` variants have a thermistor there.

This is the mirror image of H1. R2 makes sense for a `THIN` part, where 10 kΩ stands in for an NTC at
room temperature. Having settled that the `AN` (no thermal sensor) variant is the one you want, the
resistor that suited the other variant is now wrong.

It is not destructive — the absolute maximum on the pin is `-0.3 V to VIN + 0.3 V or 6.5 V`, so
grounding it cannot damage the part — but it contradicts an explicit instruction, and the safe
reading is that Torex does not characterise the part with the pin loaded.

### Resolution — U2 changed to `XC6808A4C28R-G`, R2 kept

Rather than depopulate R2, the part was changed to the variant that wants it. Decoding
`XC6808①②③④⑤⑥-⑦` from the datasheet's classification table, **the two options differ in exactly one
field**:

| Field | | `ANC28R-G` (was) | `A4C28R-G` (now) |
|---|---|---|---|
| ① | Status output on abnormal | A — 1 kHz ON-OFF | A — same |
| ② | **Battery temperature monitor** | **N — none** | **4 — 4-temp, JEITA** |
| ③ | Charge voltage | C — 4.20 V | C — same |
| ④ | Hold time / trickle | 2 — 10 h, enabled | 2 — same |
| ⑤⑥-⑦ | Package | 8R-G — USP-6B07 | same |

Charge voltage, hold time, trickle behaviour, status behaviour and package are identical.

**R2 = 10 kΩ puts the THIN pin in the middle of the normal-charge window.** The pin has an internal
pull-up of `RTHIN` = 10.0 kΩ (9.8–10.2) to `VTHIN_open` = 2.00 V (1.94–2.06), so an external 10 kΩ to
GND divides to **1.00 V = 50.0 %** of the open voltage. Thresholds are specified as percentages of
that:

| | VT60 | VT45 | **R2 gives** | VT10 | VT0 | VTD |
|---|---|---|---|---|---|---|
| % of `VTHIN_open` | 21–25 | 31–35 | **50** | 62–66 | 71–75 | 77–83 |

50 % sits between VT45 and VT10 — the normal, full-rate band — with roughly 15 points of margin to the
hot threshold and 16 to the cold. Even a ±5 % R2 holds 50 % ± 1.9 %, so no precision part is needed.
The datasheet's own default test condition is `VTHIN = 1.0 V`, this exact operating point.

**Cost:** the A4 is `$1.237` against `$2.7275` for the AN — less than half. LCSC stock at review time
was lower on the A4 (31 against 100), so check availability before a batch; both are standard
configurations, since the datasheet marks only options 2, 3, B and hold-times 1/3/4 as semi-custom.

**Two things to stay clear-eyed about.** The temperature monitor is *defeated*, not gained — a fixed
base-side resistor reads room temperature forever, and real JEITA protection would need the NTC at the
cell, which is on the tag, with no spare J101 pin to route it back. And battery insertion detection
stays unavailable: the datasheet notes it is sensed through THIN, and a fixed resistor never moves, so
re-applying VIN remains the way to restart. The genuine gain beyond price is that the A4 keeps that
door open — add a seventh tagpoint and a thermistor and you would have real JEITA charge protection.
The AN could never do that.

### H1 — BOM LCSC number for U2 — FIXED

The BOM ordered `C3682502` (`XC6808A4C28R-G`) against a schematic MPN of `XC6808ANC28R-G`. Cause: the
export tool had a mode that auto-selected LCSC numbers. That mode is now off, and the regenerated BOM
reads:

```
XC6808ANC28R-G,U2,xc6808,C7123934,1
```

`C7123934` is `XC6808ANC28R-G`. Correct, and verified in the current file.

**`AN` denotes the no-thermal-sensor variant**, which also closes the `THIN/NF` half of the question:
there is no thermistor input on this part, so pin 5 is the "NF" case and R2 (10 kΩ to GND) is not
setting a temperature threshold. Whether R2 is needed at all on an NF pin is a minor datasheet
question, harmless either way.

### H2 — J101 hole spacing — WITHDRAWN, RAISED IN ERROR

I claimed the 0.2032 mm NPTH gap was unproven because `tagbase:6pin_tagpoints_double_screws` is used
by only two boards, neither fabricated. **Both halves of that were wrong.** The spacing is what the
part requires, and it has shipped repeatedly.

The error was checking the footprint *name* instead of the *pattern*. Measuring the actual NPTH
geometry across every board with a tagpoint footprint:

| Board | Footprint | NPTH | Min gap | Fabricated |
|---|---|---|---|---|
| `tagbase-v7` | `6pin_tagpoints_new_offset` | 8 | 0.2032 mm | **yes** |
| `tagbase-jlcpcb-v7` | `6pin_tagpoints_new_offset` | 8 | 0.2032 mm | **yes** |
| `TagPwrMonitor` | `6pin_tagpoints_double_screws` | 10 | 0.2032 mm | **yes** |
| `Multicharger-jlcpcb` | `6pin_tagpoints_new_offset` | 8 | 0.2032 mm | fab output present |
| `MultiCharger` | `6pin_tagpoints_new_offset` | 8 | 0.2032 mm | — |
| `nucleoshield-c071-base-test` | `6pin_tagpoints_new_offset` | 10 | 0.2032 mm | — |
| `tagbase-lipo-v1` | `6pin_tagpoints_double_screws` | 10 | 0.2032 mm | — |

**0.2032 mm is the same in all seven, under two different footprint names, and three have shipped.**
It is a house-standard, fabricated geometry dictated by the connector, not a defect.

**A second lesson, worth more than the first: the presence or absence of fab artefacts in the repo
says nothing reliable about whether a board was built.** I used it both ways and it misled me both
times. `tagbase-lipo-v1` has a `production_files/*.zip` that is merely this review's own export, so
artefacts are not sufficient. `tagbase-jlcpcb-v7` has none and *was* fabricated, so their absence is
not necessary either. Fabrication history lives with the designer, not in the tree — ask.

**Now confirmed against Mill-Max's own drawings**, which the designer supplied as SVGs
(`libraries/datasheets/855_10_001101_0.svg` and `855_10_001101fp_1.svg`). The part is
`855-22-0XX-10-001101`, a mid-profile through-hole spring-loaded (pogo) connector.

| Item | Mill-Max spec | Board | |
|---|---|---|---|
| Signal through-hole | Ø 0.56 ± 0.08 mm | 0.610 mm | within tolerance |
| Signal pad | Ø 0.81 mm suggested | 0.940 mm | more generous |
| Pin pitch | 1.27 mm | 1.270 mm | exact |
| Row spacing | 1.27 mm | 1.270 mm | exact |
| Locating peg | Ø **1.04 mm** | 1.067 mm hole | 0.027 mm clearance |

**The 0.2032 mm gap is Mill-Max's geometry, not a choice.** The four 1.067 mm NPTH holes are the
connector's locating pegs — the dashed circles shown at each end of the pin array in the part drawing,
one per row. Two pegs of Ø1.04 mm on the connector's own 1.27 mm row pitch leave 0.23 mm between peg
bodies; drilled at 1.067 mm they leave 0.2032 mm of laminate. There is no way to open that gap without
abandoning the connector.

(The 110 MB Mill-Max catalog in the shared store is an image-only scan with no text layer on any of its
364 pages, so it cannot be searched. The two SVGs are the usable source.)

**Standing suppression:** the project's `min_hole_to_hole` is 0.254 mm, so these two DRC errors will
recur on every future review of any tagbase board. Recorded in `.kicad-happy.json` so the next
reviewer honours it by hand; a DRC exclusion or a relaxed rule for these pads would silence it at
source.

### M1 — 1.8 V level shifters — WITHDRAWN, RAISED IN ERROR

I read `TAG_3V3` as the tag's logic rail and concluded the 1.8 V shifter outputs would fail a 3.3 V
tag's V<sub>IH</sub>. **The tags carry their own internal 1.8 V regulators**, so `TAG_3V3` is the
regulator's *input* and the tag's processor runs at 1.8 V regardless of which switch position feeds
it. Level-shifting to 1.8 V is exactly right, and `VCCB = +1V8` is correct as drawn.

The lesson for the next review: on this board the net name `TAG_3V3` names a supply input, not the
logic domain of the pins next to it. The logic domain is set by the tag's own regulator and is always
1.8 V.

### M2 — R102 220 Ω — NOT A DEFECT; THE NOTE IS STALE

R102 = 220 Ω is deliberate: 100 Ω was found to be annoyingly bright on other boards, so the green was
dropped to roughly 2.7 mA on purpose.

The schematic note beside the LEDs originally read "Green 2.7Vf, 6mA, **100 ohm** (3.3V)", which is
what led me here — the resistor was right and the note did not say so. **The note has since been
amended** and now reads:

```
Red   2Vf, 6mA, 216 ohm (3.3v)
Green 2.7Vf, 6mA, 100 ohm (3.3V) == too bright, using 220
Green 2.7Vf, 6mA, 300 ohm (4.5V)
```

That is the right fix: it keeps the calculation and records the measurement that overrode it, so the
220 Ω no longer looks like an error to the next reader. Closed.

### M3 — No capacitor on the charger's BAT output, and its VIN bypass is 12.8 mm away

Measured nearest same-net capacitor to each supply pin:

| Supply pin | Net | Nearest | Then |
|---|---|---|---|
| STM32 VDD pin 1 | `+3V3` | C2 0.1 µF @ 1.73 mm | C8 @ 2.67 |
| STM32 VDD pin 17 | `+3V3` | C3 0.1 µF @ 1.36 mm | C8 @ 6.76 |
| STM32 VDDA/VREF+ | `+3V3` | C8 0.1 µF @ 1.72 mm | C2 @ 2.67 |
| XC6206 VOUT | `+3V3` | C104 1 µF @ 1.73 mm | |
| XC6206 VIN | `VUSB` | C1 1 µF @ 1.48 mm | |
| AP2112 VIN / VOUT | `+3V3` / `+1V8` | C4 1 µF @ 1.65 / C5 1 µF @ 1.60 mm | |
| U7 / U8 VCCA, VCCB | | 1.17 – 1.23 mm | |
| TLV9001 V+ | `+3V3` | C6 0.1 µF @ 1.09 mm | |
| USBLC6 VBUS | `VUSB` | C102 0.1 µF @ 1.63 mm | |
| **XC6808 VIN** | `VUSB` | **C102 @ 12.81 mm** | C1 @ 31.10 |
| **XC6808 BAT** | `/BAT` | **none on this net** | |

Everything else is tight — 1.1 to 2.9 mm. The charger is the outlier on both pins.

The BAT node has no capacitor at all, and when SW2 selects the non-battery position it is left
completely open. Linear chargers generally require an output capacitor for loop stability, and one
also softens the hot-disconnect when the switch is thrown. At 8.58 mA the VIN distance is not a
current-delivery problem, but a local 1 µF at each pin is cheap insurance.

**Needs datasheet confirmation — see §4.**

### L1 — TAG_RESET is not level-shifted

`PA10 → R104 (2.2 kΩ) → TAG_RESET → J101.1`, direct from the 3.3 V domain, while SWCLK and SWDIO
are translated to 1.8 V. If the tag runs at 1.8 V, driving this line high puts 3.3 V on its NRST pin.
The 2.2 kΩ limits injection to about (3.3 − 1.8 − 0.3) / 2.2 kΩ ≈ **0.5 mA**, inside the STM32's
±5 mA per-pin injection limit, so it survives — but it relies on the tag's clamp diode.

**Firmware contract:** drive PA10 low to assert reset and leave it as a high-impedance input
otherwise. Never drive it high. Worth recording, since it is invisible in the schematic.

### L2 — The tag-side shifter pins float when no tag is plugged in

TI's SN74LVC1T45 datasheet, §3: *"The input circuitry is always active on both A and B ports and
must have a logic HIGH or LOW level applied to prevent excess I<sub>CC</sub> and I<sub>CCZ</sub>."*
With J101 empty, `TAG_SCK` and `TAG_SWDIO` float.

This is benign on a USB-powered instrument, and you have a clean mitigation already: PB6 disables
the 1.8 V rail, and the datasheet's VCC-isolation feature then puts both ports in high impedance.
Worth making that the idle state in firmware.

### L3 — Minor

- **`lib_footprint_issues` on J1** — `JST_XH_B04B-XH-AM_1x04_P2.50mm_Vertical` is no longer found in
  the stock `Connector_JST` library. The footprint is embedded in the board, so fabrication is
  unaffected; only the library link is stale.
- **Pad-net cross-check reports 2 mismatches that are not real.** `Net-(U2-THIN/NF)` in the
  schematic versus `Net-(U2-THIN{slash}NF)` in the PCB is KiCad's escaping of `/` in net names — the
  same artifact seen on `U3-L{slash}M` in the UIUCBreakout review. 164 of 166 pads match exactly and
  these two are the same net.
- **No `MPN` fields in the schematic.** The BOM is built from `Value` + LCSC number, which works but
  means H1-style mismatches have nothing to check against. Populating `MPN` would make the BOM
  self-checking.
- **`tagbase-v7.kibot.yaml`** is named for an ancestor board.

## 3. Verified correct

**U6 TLV9001 — the pinout trap, checked and passed.** This is the finding I expected to raise and
could not. KiCad's `Amplifier_Operational:TLV9001IDCK` symbol extends `TLV172IDCK` and declares
pin 1 = `+`, 3 = `−`, 4 = OUT — the *reversed* single-op-amp arrangement, which looks wrong against
the familiar 1 = OUT convention. TI's datasheet (SBOS833R) Table 6-1 settles it:

| Package column | IN+ | IN− | OUT | V− | V+ |
|---|---|---|---|---|---|
| **SC70, SOT-23(U), SOT-553** — plain `TLV9001IDCK` | **1** | **3** | **4** | 2 | 5 |
| SOT-23, SC70(T) — `TLV9001T` DCK, `TLV9001` DBV | 3 | 4 | 1 | 2 | 5 |

The symbol matches the plain DCK exactly, and the circuit is a correct unity-gain follower:
`TAG_3V3 → R5 1 MΩ → IN+`, `OUT` tied to `IN−`, output → R107 2.2 kΩ → PA0 (ADC1_IN5).

**Two things fall out of that table worth keeping.** First, `TLV9001T`**IDCK** is the *same physical
package with inputs and output swapped* — a one-letter MPN change would silently break this circuit.
LCSC C398362 is `TLV9001IDCKR`, the correct plain variant. Second, R5 = 1 MΩ is doing real work: on
the `Vbat` switch position IN+ sees up to 4.2 V against a 3.8 V absolute maximum, and 1 MΩ limits
the clamp current to about 0.4 µA. (Note the follower saturates at the 3.3 V rail, so this is a
rail-present detector, not a battery voltmeter — if you wanted to *measure* cell voltage you would
need a divider ahead of it.)

The datasheet is now saved to the shared store as `libraries/datasheets/tlv9001.pdf`.

**Level-shifter direction logic.** TI's Table 7-1: DIR **L** = B→A, **H** = A→B — matching your
schematic note. U7 (SWCLK) has DIR tied to `+3V3`, permanently A→B, correct for a host-driven clock.
U8 (SWDIO) has DIR on PA15, firmware-controlled, correct for a bidirectional line. DIR is referenced
to VCCA (3.3 V) and is driven from the 3.3 V domain. Both correct.

**Charge current.** Your note gives `Rset = 351K × Icharge(mA)^-1.1`; R1 = 33 kΩ → **≈ 8.6 mA**,
which agrees with the note's own worked value of 8.58 mA and is sensible for a tag-sized cell.

**CSO** is pulled up by R3 (10 kΩ) to +3V3 into PA1 — consistent with an open-drain status output.

**BOOT0** has R105 (12 kΩ) to GND and U105 (tactile) to +3V3 — a standard DFU button, correctly
defaulting to boot-from-flash.

**AP2112 pin 4 NC** left unconnected, matching your schematic note and the datasheet.

**Electrical / layout**

| Check | Result |
|---|---|
| KiCad DRC (`--refill-zones`, `--severity-all`) | 3 violations — 2 are H2, 1 is the L3 library link. **0 unconnected** |
| ERC | 2 warnings, both library-link only |
| Schematic ↔ PCB pad-net cross-check | 166 pads, **0 real mismatches** (see L3) |
| Stackup | 4 layer, 1.6 mm — In1 = `+3V3` plane, In2 = GND, F.Cu/B.Cu GND pours |
| Vias | 62, all 0.505 / 0.2 mm → 0.152 mm annular ring |
| Track widths | 402 mm at 0.1016 mm, 39 mm at 0.1524, 39 mm at 0.3048 (VUSB) |
| Current capacity | not a concern — 8.6 mA charge, tens of mA total |

The 4 mil default is a house convention, and at these currents it is a fab process-selection matter
rather than an electrical one. On a 51 × 70 mm board with this much free area you could raise the
default to 6 mil almost for free and widen your fab options, but that is preference, not a finding.

## 4. M3 — confirmed, and now resolved

The XC6808 datasheet is now in the shared store as `libraries/datasheets/C3682502.pdf`. Its typical
application circuit for the `XC6808xN` is:

```
                     CSO
      VIN                         RISET
                     ISET
                                        Li-ion Battery Pack
                     BAT
  CIN      XC6808xN        CL
                                   Protection
  1µF                     1µF
4.5~6 V         NF                     IC
              VSS
```

**Both capacitors are 1 µF and both are required.** Measured against the board:

| Required | Was | Now | Verdict |
|---|---|---|---|
| `CL` = 1 µF on **BAT** | nothing at all on `/BAT` | **C9 1 µF at 1.56 mm** | fixed |
| `CIN` = 1 µF on **VIN** | C1 1 µF at 31.10 mm; 0.1 µF at 12.81 mm | **C10 1 µF at 2.15 mm** | fixed |

`/BAT` previously had exactly two pads — U2 pin 1 and SW2 pin 3 — so when SW2 selected a non-battery
position the charger's output was left completely open, with no capacitor and no cell. C9 now sits
1.56 mm from pin 1, which also softens the hot-disconnect when the switch is thrown.

**Also confirmed from the same document:**

- **Charge current.** `RISET (kΩ) = 351 × ICHG(mA)^-1.11`, matching your schematic note to within the
  exponent's second digit. R1 = 33 kΩ → **≈ 8.4 mA**, inside the datasheet's valid 5–40 mA window.
- **Note 11:** *"If the ISET pin is shorted to the GND, there is a possibility that the IC is
  destroyed before the over-current monitor function is activated."* R1 = 33 kΩ is nowhere near this,
  but it is worth knowing that ISET is a pin where a probe slip is destructive.
- **Operating range 4.5–6.0 V** — fine on USB VBUS.

## 5. Confirm intent

**SWD over SPI — CONFIRMED, and it is SPI1, not SPI3.** I had guessed SPI3; the designer confirms
**SPI1**. Both are available on these pins, so either would work:

| Pin | SPI1 (AF5) | SPI3 (AF6) | Role here |
|---|---|---|---|
| PB3 | `SPI1_SCK` | `SPI3_SCK` | → U7 A → `TAG_SCK` |
| PB4 | `SPI1_MISO` | `SPI3_MISO` | → U8 A → `TAG_SWDIO`, and R4 to PB5 |
| PB5 | `SPI1_MOSI` | `SPI3_MOSI` | R4 (100 Ω) to PB4 |
| PA15 | `SPI1_NSS` | `SPI3_NSS` | used as GPIO for U8 DIR |

R4 ties MOSI to MISO so the full-duplex peripheral drives a single half-duplex bidirectional line —
which is what SWDIO is — with the resistor limiting contention current during turnaround. U8's DIR on
PA15 flips the level shifter to match.

No peripheral collision: PA1 and PA15 also carry SPI1 functions (`SPI1_SCK`, `SPI1_NSS`) but are used
as plain GPIO here, so SPI1 is free for this bus. **Select AF5, not AF6.**

**Unused GPIOs:** PA4–PA8, PB0, PB1, PB7, PC14, PC15 — ten pins. On a USB-powered instrument leakage
is irrelevant, so this is housekeeping rather than a power concern; setting them analog/no-pull is
still the tidy default. PC14/PC15 remain available for a 32.768 kHz crystal if you ever want an RTC
timebase.

## 6. Closing state

**Nothing outstanding.** Every finding is closed: one real and fixed (H1), one resolved by a part
change (H3), one resolved by two capacitors (M3), three withdrawn as raised in error (H2, M1, and the
first-pass reading of M2), and the SWD-over-SPI question answered.

Verified against the working tree after the changes:

| Check | Result |
|---|---|
| KiCad DRC (`--refill-zones`, `--severity-all`) | 3 violations, **0 unconnected** — 2 are the accepted Mill-Max peg spacing, 1 is the stale J1 library link |
| ERC | 2 warnings, both library-link only |
| Schematic ↔ PCB pad-net cross-check | **170 pads, 0 mismatches** |
| `CL` on BAT | C9 1 µF at 1.56 mm from U2 pin 1 |
| `CIN` on VIN | C10 1 µF at 2.15 mm from U2 pin 6 |
| U2 | `XC6808A4C28R-G`, LCSC `C3682502` — MPN and part number now agree |
| R2 | retained, correct for the A4 variant |

Nothing is outstanding, including the LED note, which now records the 220 Ω choice and the reason for
it.

Ready to regenerate the fab package and tag `review/tagbase-lipo-v1-2026-09-07`.
