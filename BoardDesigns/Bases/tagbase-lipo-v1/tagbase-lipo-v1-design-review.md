# tagbase-lipo-v1 — design review

**Date:** 2026-09-07 — **updated 2026-10-12** for five added test pads, the U2 change to `XC6808ANC28R-G` (R2 not fitted), and the regenerated JLCPCB package
**Board:** `tagbase-lipo-v1.kicad_pcb` / `.kicad_sch` — 4 layer, 50.95 × 70.00 mm, 1.6 mm
**Role:** USB-powered base station that programs a tag over SWD and charges the tag's LiPo cell
through the 6-pin tagpoint connector.
**Status:** not previously fabbed. **Fab house: JLCPCB** (`jlcpcb/`); `pcbway_production/` is not
the order and is out of scope.

## Update 2026-10-12 — test pads J2, J3, J4, J6, J7

**Verdict: ready to order. Every finding is closed.** The first pass on these pads found one real
problem: they were in the JLCPCB BOM and CPL (N1). It is fixed at the source. The designer then added
function labels, hid the reference designators, moved J7 to the tag side of R104, and replaced the
mislabelled power symbol on the reset net (N3). Finally, **U2 was changed back to `XC6808ANC28R-G` with
R2 not fitted**, because the A4 went out of stock (see below).

### U2 → `XC6808ANC28R-G`, R2 not fitted — because the A4 is out of stock

At order time LCSC had **0** of `XC6808A4C28R-G` (C3682502). Every other standard XC6808 code
charges to 4.35 V or 4.40 V, or is semi-custom. That leaves `XC6808ANC28R-G` (C7123934; 9 in stock,
$2.64 @1, $2.24 @10) as the only footprint-compatible 4.20 V part. The XC6802 and XC6804 Torex
siblings LCSC suggests are 800 mA-class parts in different packages.

The AN differs from the A4 only in ordering-code field ② (temperature monitor: N instead of 4).
Charge voltage, hold time, trickle, status behaviour, package and the R1 charge-current formula are
identical. **On this board the charging behaviour is the same:** the A4's monitor only ever read R2's
fixed "room temperature". The only thing lost is the option of adding real JEITA protection later.

**This variant requires pin 5 to be open** (H3 below). So R2 is now not fitted at every level:
- **Schematic:** `dnp yes`, `in_bom no`.
- **Footprint:** `exclude_from_pos_files exclude_from_bom dnp`.
- **Plugin:** `1, 1` in `jlcpcb/project.db`.

Its footprint stays on the board.

| Check | Result |
|---|---|
| U2 fields (schematic and PCB) | Value, MPN, Datasheet = `XC6808ANC28R-G`; LCSC = `C7123934`. No `XC6808A4C28R-G` left anywhere in the design files |
| BOM | `XC6808ANC28R-G,U2,xc6808,C7123934,1`; the 10 kΩ line is R3 only |
| CPL | R2 removed, U2 relabelled at the same position and rotation; nothing else changed |
| PCB vs the committed board | 8 lines: U2 Value/Datasheet/LCSC/MPN and R2's attributes. **No geometry change** |
| Gerbers / drills | Content-identical to the committed set (sorted-line compare, timestamps ignored). Zip = loose files |
| DRC / ERC / pad nets | Unchanged: 3 accepted DRC items, 0 unconnected, 0 parity; ERC library-link only; 50 footprints, 0 mismatches |

**Low, at inspection:** R2's pads are still on the top paste layer, so the stencil puts solder on
two bare 0402 pads. A bridge there is unlikely. If one did form, the NF pin would be grounded: within
the absolute maximum ratings, but the condition Torex says to avoid. Look at it under magnification,
or ask JLCPCB to leave R2 off the stencil.

### What changed

The layout change is confined to the five test pads and their nets; no other footprint moved. Five
`TestPoint:TestPoint_Pad_D1.5mm` SMD pads (Ø1.5 mm, copper and mask only, no paste) were added on
schematic symbol `Conn_01x01`. Each has a hidden reference and a silkscreen label on its own side:

| Ref | Side | Label | Net | Other pads on the net | What you see there |
|---|---|---|---|---|---|
| J2 | bottom | `3v3 valid` | `/TAG_3V3_Valid` | U5 PA0, R107.1 | The ADC input, after the 2.2 kΩ (follower output → R107 → here) |
| J3 | bottom | `en1.8v` | `/en1.8v` | U5 PB6, U3 EN | The +1V8 regulator enable |
| J4 | bottom | `sck` | `TAG_SCK` | U7 B, J101.4 | SWCLK on the tag side, at 1.8 V |
| J6 | bottom | `swdio` | `TAG_SWDIO` | R106.2, J101.3 | SWDIO on the tag side of R106, at 1.8 V |
| J7 | **top** | `Reset` | `TAG_RESET` | R104.2, J101.1 | The tag's reset pin, on the tag side of R104 |

The change adds 67 vias in total (2 more than HEAD), all still 0.505/0.2 mm, and all new track is
0.1016 mm, the house default.

**Electrically correct.** J4 and J6 sit on the tag side of the shifters, where they show what the
tag actually receives. The stubs they add, 2–4 mm plus about 0.5 pF of pad, are negligible at SWD
clock rates. J2 is behind R107, so a scope probe on it cannot load the op-amp output.

**J7 on `TAG_RESET` is the better place.** It now shows the tag's reset pin itself, so an open R104
or a tag holding its own reset low is visible there. It also makes a manual reset easy: short J7 to
GND. R104 (2.2 kΩ) limits current from PA10 to about 1.5 mA even if firmware were driving it high.
The L1 contract still stands: firmware only ever drives PA10 low or leaves it as a high-impedance
input.

**J3 is for probing, not forcing.** PB6 drives this net push-pull, so clipping a supply onto J3 to
force the 1.8 V rail on fights the MCU pin.

**Placement is fine.** Each pad is at least 13.5 mm from the board edge and at least 2.4 mm from the
nearest other pad (J7 to R106.2). The closest vias are 0.46–0.47 mm from the J2 and J7 pad edges,
which is enough for a pogo or hook probe. Every label is 1.8–3.5 mm from its pad, on the same side.
`Reset` is left-justified and ends about 0.7 mm short of J7. The PCB analyzer raises no
silk-over-pad findings.

### U4 source → TECH PUBLIC `USBLC6-2P6` (C2827693) — ST part low on stock

ST's `USBLC6-2P6` (C15999) was down to 5 in stock. TECH PUBLIC's part of the same name (C2827693,
41,475 in stock, $0.16 against $0.25) is a drop-in. Both datasheets give the identical pin map:
1/6 I/O1 → `/DP`, `/USB_DP`; 3/4 I/O2 → `/DM`, `/USB_DM`; 2 GND; 5 VBUS → `VUSB`. Both packages are
SOT-666 at 0.5 mm pitch with matching body dimensions, so the stock footprint is unchanged.

| | ST C15999 | TECH PUBLIC C2827693 |
|---|---|---|
| VRWM / VBR | 5.25 V / ≥ 6 V | **5.0 V** / ≥ 6 V |
| Leakage | 150 nA max | 80 nA max |
| Clamp, I/O | 12 V @ 1 A, 17 V @ 5 A | 10 V @ 1 A, 14 V @ 5.5 A |
| ESD (IEC 61000-4-2) | 8 kV contact / 15 kV air | ±30 kV (claimed) |
| Capacitance | 2.5–3.5 pF I/O–GND; 1.2–1.7 pF I/O–I/O | 0.35–0.5 pF I/O–I/O; I/O–GND not given |

The lower VRWM sits under USB's 5.25 V ceiling, but breakdown is still at least 6 V, so it costs a
little leakage and nothing else. The missing I/O-to-GND capacitance does not matter at full-speed
USB. The TECH PUBLIC datasheet is a 4-page image-only scan, now in the shared store as
`libraries/datasheets/C2827693.pdf`.

`LCSC` and `MFN` were changed on the schematic, the PCB and in `jlcpcb/project.db`; `Value` and `MPN`
stay `USBLC6-2P6`. DRC/ERC are unchanged. The BOM was re-exported with C2827693, and U4's rotation was fixed in the preview (see the
rotations section below).

### JLCPCB placement rotations — six parts corrected at the source

The plugin's global community rules got six parts wrong, and they had to be fixed by hand in the
JLCPCB placement preview. The fixes now live in this board's own `jlcpcb/project.db`. It has a
`correction` table holding the 61 community rules plus six reference rules, and its presence
makes the plugin ignore the global database. A re-export now produces the right CPL with no
hand-editing.

| Part | Package / LCSC | Community rule | Board rule | Final CPL |
|---|---|---|---|---|
| U1 | SOT-23-3, C5446 | `^SOT-23` −90 (wrong) | `^U1$` +180 | 270 |
| U3 | SOT-23-5 | `^SOT-23` −90 (wrong) | `^U3$` +180 | 270 |
| U2 | USP-6B07 (`xc6808`), C7123934 | none | `^U2$` −90 | 270 |
| U4 | SOT-666, C2827693 | none | `^U4$` −90 | 270 |
| U6 | SC-70-5, C398362 | `^SOT-353` +180 (wrong) | `^U6$` −90 | 0 |
| J104 | USB Mini-B, C2681563 | none | `^J104$` −90 | 180 |

Verified on the final export: the CPL differs from the previous commit in exactly these six rows,
and the BOM only in U4's LCSC number. The Gerbers are content-identical. Placement models are per
LCSC part, so **any future part substitution needs its own preview check**. U4's rule was found on
the TECH PUBLIC part and may not hold for ST's C15999. The rules are mirrored in `.kicad-happy.json`
under `fabrication.rotation_corrections`.

### N1 — The test pads were in the JLCPCB BOM and CPL — FIXED

The first regeneration put five `Conn_01x01` lines with no LCSC number into the BOM, and four
bottom-side rows into a CPL that previously had none. That would make JLCPCB quote double-sided
assembly. The cause was `jlcpcb/project.db`, where the pads had `exclude_from_bom = 0,
exclude_from_pos = 0`, unlike every other connector.

**Fixed at all three levels:** `in_bom no` on the symbols (not DNP), `exclude_from_bom
exclude_from_pos_files` on the footprints, and `1, 1` in `project.db`. Verified in the
regenerated package:
- The BOM has no `Conn_01x01` lines.
- The CPL has **0** bottom-side rows.
- Both files are **identical to the committed 09-07 versions**.

### N2 — The pads were labelled only `J2`…`J7` — RESOLVED

Function labels added and references hidden, as tabulated above. A GND pad was not added, which is
optional. J5 pin 1 (a DNP header, plated hole, GND) remains the nearest place for a scope ground
clip.

### N3 — Net naming — RESOLVED

- **Resolved by the J7 move.** The PA10 net had been auto-renamed `Net-(J7-Pin_1)`. With J7 now on
  `TAG_RESET`, the net is back to its original `Net-(U5-PA10)`, holding R104.1 and U5.20.
- **Resolved, pre-existing:** C7 (0.1 µF) reached `NRST` through `#PWR038`, a `power:+3V3` symbol
  with its Value changed to `NRST`. KiCad merged it correctly, but on the sheet it looked like a
  +3V3 port: the designer could not find C7 at first, because it read as a rail decoupler. The
  symbol also split the analyzer's view of the net. **Fixed:** `#PWR038` was replaced by a third
  local `NRST` label. The net is now `/NRST` = C7.1, J102.10, U5.4 in KiCad's netlist, and the
  RS-001 warning and both `padnet_crosscheck` artifacts are gone. On the board, the only change is
  the net name; there is no geometry change.

### Re-verification, 2026-10-12 (final state: labels, J7 move, NRST label)

| Check | Result |
|---|---|
| Rules source | `pcb.json` `project_settings.source` and `rules_source` both `tagbase-lipo-v1.kicad_pro` |
| KiCad DRC (`--refill-zones --severity-all --schematic-parity`, in place) | **Unchanged from 09-07:** 3 violations (2 × J101 locating-peg `hole_to_hole`, 1 × J1 library link — both suppressed). **0 unconnected, 0 parity errors** |
| ERC | 2 warnings, both library-link only (J104 symbol, J1 footprint link) |
| KiCad netlist | `TAG_RESET` = J101.1, J7.1, R104.2; `Net-(U5-PA10)` = R104.1, U5.20; `/NRST` = C7.1, J102.10, U5.4 |
| Schematic ↔ PCB pad nets | **50 footprints, 0 mismatches** |
| Schematic analyzer | 0 errors; 1 warning (DS-002: the board has no `datasheets/` symlink; the datasheets this review relies on are in `libraries/datasheets/`) |
| Gerber set | 11 layers + PTH/NPTH, KiCad 10.0.2, regenerated 07:38. `GERBER-tagbase-lipo-v1.zip` is **byte-identical** to the 15 loose files in `jlcpcb/gerber/`. Copper net attributes carry `/NRST` |
| Gerber ↔ board geometry | Origin = aux origin (101.6, 50.8). **350/350** track-segment starts and **200/200** sampled zone-fill vertices found. All five test pads flash on copper and mask, none on paste (correct). J7 is at its new position |
| Drill reconciliation | 67 vias (0.2 mm) = 67 on board. PTH 6 × 0.61, 10 × 0.635, 4 × 0.95, 2 × 1.0; NPTH 2 × 0.9, 4 × 1.067, 1 × 1.2, 4 × 1.588, 2 × 2.16. **Every tool matches the board** |
| Annular ring / min track | 0.152 mm via ring, 0.1016 mm track: unchanged house convention |
| BOM / CPL | **Identical to the committed 09-07 package.** 0 bottom-side placements |

**False positives triaged this pass, not raised:**
- **Gerber analyzer GR-002**, "height varies by 26.3 mm across copper layers." This is In1.Cu, the
  +3V3 plane, which deliberately covers only the upper 35 mm of the board. The zone outline and fill
  are identical at HEAD.
- **PCB analyzer CC-002**, "narrow signal" on the test-pad nets. These are 4 mil house-convention
  tracks, already suppressed.
- **FD-001 (no fiducials) and PM-002 (D101/D102 at 0.48 mm from the edge).** Both are pre-existing
  and unchanged since the 09-07 sign-off. JLCPCB does not require fiducials on a single
  (unpanelised) board. The LEDs sit on the top edge on purpose. Their nearest pads are 0.73 mm
  from the edge (the 0.48 mm is the body), well clear of JLC's 0.3 mm copper-to-edge minimum.

**Not re-run, and why:** EMC, SPICE, thermal and lifecycle. The change adds five passive copper pads
and no components with electrical behaviour, so the 09-07 results stand. The STM32 pin map is
unaffected: PA0, PA10 and PB6 were already allocated, and the pads add no new functions. No
datasheets were needed.

**Tooling note:** `kicad-helpers/padnet_crosscheck.py` ends with a hard-coded `U302` debug print,
which raises `IndexError` on any board without a U302. It does so *after* the cross-check results
print, so the results are valid, but the traceback looks like a failure.

---

## Verdict (2026-09-07)

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

> **Superseded 2026-10-12.** The A4 went out of stock, so U2 is `XC6808ANC28R-G` again, and this
> time **R2 is not fitted**, which satisfies the NF requirement above. See the update at the top.

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

## 6. Closing state (2026-09-07 — superseded by the 2026-10-12 update at the top)

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
| U2 | `XC6808A4C28R-G`, LCSC `C3682502` — MPN and part number now agree (**superseded 2026-10-12:** `XC6808ANC28R-G` / `C7123934`, R2 not fitted) |
| R2 | retained, correct for the A4 variant |

Nothing is outstanding, including the LED note, which now records the 220 Ω choice and the reason for
it.

Ready to regenerate the fab package and tag `review/tagbase-lipo-v1-2026-09-07`.
