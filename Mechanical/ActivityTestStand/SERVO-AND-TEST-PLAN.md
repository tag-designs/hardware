# Activity test stand — servo control and test plan

Status as of 2026-10-28. The stand is assembled, with a BitTag V6 on its tag
base, and its range of motion is confirmed (section 4a). A BitTag edge-log
build timestamps every activity and inactivity event (section 9), and the
first stand results are in section 13. The figures in sections 4 and 5 were
measured on 2026-10-25 on a bare LX-16A with nothing on its horn, driven
through the BusLinker V3.0 from this machine. Speed has not been re-measured
with the load on.

## Summary

- **The servo is fully controllable from Python.** [`lx16a.py`](lx16a.py)
  implements every command in the LX-16A bus protocol, and every read command
  answers. A position read takes about 1.7 ms, so motion can be logged at
  over 500 Hz.
- **The servo reaches positions to about ±3 counts (±0.7°)** on an adequate
  supply. At the servo's 5 V reading on the 6 V supply it stopped 3–5 counts
  short.
- **A 90° move takes about 0.38 s at full speed** (300–320 °/s, matching the
  rated 0.19 s/60°). Commanded move times of 300 ms or less are all
  speed-limited.
- **Full-speed moves jolt the tag by an estimated 0.4–0.75 g** for 10–40 ms,
  the same order as the gravity change being tested. Threshold tests must use
  slowed moves.
- **BitTag runs the ADXL362 in wake-up mode**, sampling about every 160 ms.
  That, not host polling latency, sets the timing resolution of every test.
- **Activity and inactivity events are timestamped to 1 ms** by a BitTag
  edge-log build, which keeps the AWAKE level of every wake in SRAM2 for
  [`edge_log.py`](edge_log.py) to read after the run (section 9). No
  tag-server is needed.
- **Continuous ±30° swings hold the tag active**: 15 of 15 5 s bouts gave one
  episode of 4.65–5.82 s on the replacement supply (section 13). A held tilt
  does not — the tag goes inactive about 0.5 s after motion stops.
- **Power versus activity needs no firmware change.** The tag runs detached
  under the Joulescope while [`stand_profile.py`](stand_profile.py) drives a
  logged stimulus. Each AWAKE edge wakes the MCU, so the expected cost of
  activity is per edge, and the inactivity setting — 1 sample by default —
  sets the edge rate (section 10).

## 1. Servo hardware and access

| | |
|---|---|
| Interface | BusLinker V3.0, CH9102 USB serial (USB ID 1a86:55d3) |
| Linux device | `/dev/ttyACM0`, stable name `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5CE5121761-if00` |
| Link | 115200 8N1, half duplex. The BusLinker does not echo our transmissions. |
| Servo | ID 1 |

**Access.** The device is `root:dialout`. Either add the user to `dialout`
(`sudo usermod -aG dialout $USER`, then log in again) or grant access for the
session (`sudo setfacl -m u:$USER:rw /dev/ttyACM0`, lost on replug). If the
board has been passed through to a VM, release it first; until then no tty
appears.

## 2. Driver: `lx16a.py`

Covers motion (immediate move, staged move and start, stop, continuous-rotation
mode, torque on/off), state readback (position, supply voltage, temperature,
mode, torque state, last target, angle offset, angle/voltage/temperature
limits, LED settings), and the stored configuration writes (ID, offset,
limits, LED).

```bash
python3 lx16a.py status            # everything readable
python3 lx16a.py move 500 1000     # position 500 over 1000 ms, waits to settle
python3 lx16a.py angle 30 2000     # +30° from centre over 2 s
python3 lx16a.py watch --hz 20     # position, voltage, temperature until ^C
python3 lx16a.py unload            # torque off
```

From Python: `LX16A()` with `move`, `move_deg`, `pos`, `pos_deg`, `vin`,
`temp`, `status`, `load`/`unload` and `wait_until_stopped(min_s=...)`.

**Units.** Position is 0–1000 counts over 240°, 0.24° per count, centre 500.
Move time is 0–30000 ms.

**Errata in the vendor protocol PDF**, corrected in the driver:

- The move commands' position range is 0–1000, not "0~100".
- `SERVO_ANGLE_OFFSET_READ` is command 19 with request length 3, not
  "command value 9, length 7".

**Settle detection** waits out the commanded move time before checking for a
steady position. Without that, a slow move's gentle start reads as "already
stopped".

### State as found

| | |
|---|---|
| Position | 501 |
| Mode | position, torque off |
| Angle offset | 0 |
| Angle limits | 0–1000 |
| Voltage limits | 4.5–14 V |
| Temperature limit | 85 °C |
| LED alarms | mask 7: over-temperature, over-voltage and stall |

The stored voltage limits are wider than the LX-16A's 6–8.4 V rating. Narrow
them to 6.0–8.4 V (`set_vin_limits(6.0, 8.4)`, saved in the servo) once a
meter has confirmed the servo's own voltage reading (section 3).

## 3. Supply voltage

**Resolved 2026-10-28 by a stronger supply**: 7.63 V at rest and 6.50–7.81 V
through 5 minutes of continuous swinging, inside the LX-16A's 6–8.4 V rating.
On the 7.5 V adapter described below, swinging pulled the supply to 4.2 V at
reversals and stalled the servo for about a second, 1–3 times per 15 bouts
(section 13). The history follows.

| Condition | On the "6 V" supply | On the "7.5 V" supply |
|---|---|---|
| Idle | 5.03 V | 8.07 V |
| Holding position | 5.03 V | 8.08 V |
| During a 24° move | 4.66–5.36 V | 6.94–8.31 V |

These are the servo's own readings. The first supply read about 1 V below its
label, the second about 0.6 V above, so this does not show a fixed drop on the
BusLinker. Most likely the supplies are not what their labels say (the 7.5 V
one may be unregulated and high at light load), but the servo's voltage
reading could also be off. Hiwonder publishes no BusLinker schematic.

**To settle it, measure with a meter**: at the barrel jack or screw terminal,
and at **+**/**–** on the servo header in use, and compare with the servo's
reading. Until then, DESIGN-NOTES' assumption that the BusLinker passes its
input straight to the servo is unconfirmed.

**The 7.5 V adapter is the working supply**; a regulated one is not readily
available. Instead, `stand_profile.py` logs the servo's voltage and
temperature on every row and warns, without stopping, when the voltage leaves
6.0–8.4 V or the temperature reaches 70 °C. The run ends with a summary of
the extremes. Check that summary before trusting a run.

The first logged run, 2 s bouts of fast ±30° swings (300 ms per swing), showed
two things:

- **Single-sample dips at move starts**, to 5.6 V and 4.8 V, recovering by
  the next sample about 100 ms later. These are the adapter sagging under the
  motor's starting current.
- **The resting reading crept up**, from 8.1 V at the start to 8.36–8.46 V
  while holding still after a few bouts, and 8.52 V once. That is at or just
  over the 8.4 V rating. An unregulated adapter rising at near-zero load is
  the likely cause, but the servo's own reading is unverified (see above).

Neither tripped the servo's own protection, whose stored limits are
4.5–14 V. Gentler moves will sag less. If the resting voltage stays above
8.4 V on long runs, a series diode (about 0.7 V) on the adapter is the
cheapest fix.

## 4. Positioning accuracy

±10° and ±30° moves from centre, 800 ms each. "Settled" is the reading when
motion stopped; the error is a fresh reading taken 0.5 s later. The 6 V run
only covered ±10°, and its moves to 500 were each run once.

| Commanded | 6 V supply: settled | 7.5 V supply: settled | 7.5 V error after 0.5 s |
|---|---|---|---|
| 542 | 537 | 538 | −3 |
| 500 (from above) | 504 | 504, 502 | +1, +1 |
| 458 | 461 | 461 | +2 |
| 500 (from below) | 495 | 497, 497 | −3, −2 |
| 625 | — | 623 | −3 |
| 375 | — | 377 | +2 |

- On adequate supply the servo lands within ±3 counts (±0.7°), stopping
  slightly short on the side it approaches from, and sometimes creeps a count
  or two closer over the next half second.
- **To land on a position repeatably, always approach it from the same side and
  allow about 0.5 s to settle.**
- Near level one count is about 4 mg on the tilted axis, so a threshold can be
  bracketed to about ±4 mg.

## 4a. Assembled stand: range of motion

Measured on 2026-10-27 with the rotor, U bracket, tag base and BitTag V6
mounted. The servo was centred at 500 before the U bracket was bolted on, and
the angle offset is still 0. Each move took 3–4.5 s from level, held 2 s, then
returned. The tag-base cable was watched throughout.

| Commanded | Reached | Supply |
|---|---|---|
| ±15° | +14.4° / −14.6° | 8.12–8.15 V |
| ±30° | +29.5° / −29.5° | 8.09–8.14 V |
| ±45° | +44.6° / −44.6° | 8.06–8.21 V |
| ±60° | +59.3° / −59.8° | 8.10–8.20 V |
| ±90° | +89.3° / −89.8° | 8.14–8.20 V |
| ±100° | +99.1° / −99.8° | 8.07–8.19 V |

- **±100° is the confirmed safe range.** Nothing hit anything and the cable did
  not snag. It covers every test here up to the full 1 g change on one axis
  (90°).
- Beyond ±100° is untested. The servo's own end stops are at ±120°, and the
  ±106.8° orientation case is not needed for routine testing.
- With the load on, the servo still stops within 3 counts (0.75°) of the
  target. It stops further short on the + side (0.5–0.9°) than on the − side
  (0.2–0.5°), consistent with the load resisting the motor on that side.
- The servo warmed from 30 °C to 38 °C over these sweeps.
- "Level" is still servo position 500. Levelling against gravity needs the tag
  to report its own tilt (section 12, step 2).

## 5. Speed and dynamics

### 90° moves (312 ↔ 688, 90.2°)

| Commanded time | Starts moving | 10–90% of travel | Within 5 counts | Overshoot | Peak speed |
|---|---|---|---|---|---|
| 0 ms | 13–20 ms | 270 ms | 387 ms | 5–8 counts | ~300 °/s |
| 100 ms | 10–20 ms | 270 ms | 384 ms | 5–10 counts | ~305 °/s |
| 200 ms | 11–21 ms | 268 ms | 379 ms | 6–10 counts | ~315 °/s |
| 300 ms | 21–25 ms | 268 ms | 388 ms | 6–8 counts | ~315 °/s |
| 400 ms | 11–22 ms | 262–321 ms | 452 / 645 ms | 5–9 counts | 270–325 °/s |
| 600 ms | 23–24 ms | 475 ms | 643 ms | 4–6 counts | ~205 °/s |

- Commanded times of 300 ms or less give the same speed-limited move; from
  400 ms the servo follows the commanded timing.
- Full-speed moves overshoot by 1–2.5°, most when moving down.
- The servo starts within about 25 ms of a command.
- The servo warmed from 27 °C to 33 °C over 12 full-speed 90° moves.

### Acceleration at the tag

Estimated by differentiating the logged position of a 30° move, with the tag
44 mm above the tilt axis (DESIGN-NOTES). These are rough — position is
quantised to 0.24° — and will change once the rotor's inertia is added.

| Move | Speed-up / slow-down | Jolt at the tag | Duration |
|---|---|---|---|
| Full speed (~230 °/s on 30°) | ~100–170 rad/s² | ~0.4–0.75 g | 10–40 ms |
| 30° commanded over 300 ms (~100 °/s) | ~20 rad/s² | ~0.09 g | ~80 ms |

The jolt is tangential, so it lands on the same in-plane axis as the gravity
change, in the direction of travel. **Use slowed moves for anything near a
threshold**, and characterise each move type from the tag's own data once the
stand is built (section 8).

## 6. Mapping gravity change to tilt

Tilting by θ from level changes the in-plane axis in the tilt direction by
sin θ and the vertical axis by 1 − cos θ. The axis along the tilt axis does not
change.

| Change on the in-plane axis | Tilt (asin) |
|---|---|
| 100 mg | 5.7° |
| 250 mg | 14.5° |
| 500 mg | 30° (125 counts) |
| 1 g | 90° |

The vertical axis needs 60° for the same 0.5 g change, so the in-plane axis
always crosses a threshold first — the stand produces a change on one axis.

## 7. The ADXL362 detector, as BitTag configures it

### Datasheet rules

- **Activity**: any one axis beyond `THRESH_ACT` for `TIME_ACT` consecutive
  samples. `TIME_ACT` 0 behaves as 1.
- **Inactivity**: all three axes within `THRESH_INACT` for `TIME_INACT`
  consecutive samples (16 bits).
- **Referenced mode** compares |a − reference| per axis, so gravity's static
  1 g does not count. The activity reference is captured when activity is
  enabled, and in linked or loop mode each time inactivity is detected.
- **Wake-up mode** samples "about six times per second", and ignores the
  activity timer: activity fires on a single sample.
- **Scale error** up to ±10% (sensitivity calibration error). **Clock**
  spread about 3% (one standard deviation) between parts.

### What BitTag sets

From `~/Research/software/embedded/tags/BitTag/src/bt_state_run.c`
(`adxl362_init()`) and `bt_config.c`:

| Setting | Value | Consequence |
|---|---|---|
| Power mode | wake-up mode | Samples about every 160 ms. The configured 50 Hz ODR does not apply. |
| Activity time | hard-coded 2, ignored in wake-up mode | Activity fires on one sample. `active_sec` has no effect on BitTag. |
| Inactivity time | `inactive_sec` is a **sample count**, clamped to 1–255 | About 0.16–42 s; the length in seconds depends on the chip's unspecified wake-up rate. |
| Range | fixed ±4 g, 2 mg per count | The Config range field is ignored. |
| Detectors | both referenced, loop mode (`ACT_INACT_CTL = 0x3F`) | Activity is measured from where the tag sat when inactivity last fired. |
| Output | INT2 = AWAKE, on `LINE_ACCEL_INT` | One line: rising edge = activity, falling edge = inactivity. |

**Bug: threshold conversion truncates.** `clampAdxl362Threshold()` converts g
to counts with a truncating cast. In single precision 0.35 / 0.002 is
174.99998, stored as 174 counts (0.348 g); 0.25 g and 0.5 g lose a count the
same way. A 2 mg error, fixed by rounding (add 0.5 before the cast).

## 8. Test design

### Tests

| Test | Stimulus | Result |
|---|---|---|
| **Wake-up rate** (do first) | Inactivity count N; trigger activity, return to level, time the falling edge | Real sample period = time / N. Every inactivity-time result depends on it. |
| **Activity threshold** | Slow tilt to a bracketed angle around asin(threshold), hold ≥ 0.5 s | Angle at which AWAKE rises = effective threshold in true g |
| **Inactivity threshold and time** | After activity, hold still; then repeat with a small mid-wait move below, then above, `THRESH_INACT` | Time to falling edge; whether the timer restarts |
| **Short-stimulus capture** | Tilt pulses of duration D, repeated | Capture probability ≈ D / 160 ms below one sample period |
| **Inactivity reference** | Tilt past threshold and hold | Whether inactivity fires while tilted (reference taken at activity) — decides how every sequence must be ordered |
| **Move characterisation** | Each move type, tag recording raw XYZ | The stimulus the detector actually sees, including the start/stop jolts |

Each trial starts at rest, level, with AWAKE low, so that the activity
reference is level.

### Error budget

| Source | Size | Handling |
|---|---|---|
| Wake-up sampling | ~160 ms | Dominant timing term; measure the period per tag |
| ADXL362 clock spread | ~3% per part (σ) | Measure the period, or use pass windows wider than ±10% |
| ADXL362 scale error | up to ±10% | The stand measures in true g; don't fail a part for missing the programmed value by a few percent |
| Threshold truncation | 2 mg | Fix in firmware |
| Servo positioning | ±3 counts, ~±10 mg near 30° | Approach from one side; log actual position |
| Move jolt | 0.1–0.75 g, 10–80 ms | Slow moves near thresholds |
| Hold jitter | unknown | Turn torque off after moves if it disturbs low inactivity thresholds — check on the assembled rotor |
| Host polling | a few ms | Negligible |

## 9. Implementation: the BitTag edge log

**The constraint**: a running tag cannot be observed — attaching resets it
(software repo `AGENTS.md`). So the tag runs detached and reports afterwards.

**Firmware.** BitTag already wakes from Standby on every edge of the ADXL362's
AWAKE line, and `Running()` reads the line on each wake. A build with
`BITTAG_EDGE_LOG=1` (software repo, `embedded/tags/BitTag/inc/edge_log.h`)
adds a record per RUNNING wake: RTC Unix seconds, milliseconds and the AWAKE
level, into a 2046-record ring at the start of SRAM2 (0x10000000).

- A change of level between consecutive records is an edge. The minute-alarm
  wakes repeat the level.
- The timestamp is the RTC subsecond counter (PREDIV_S 1024, so 1 ms). It is
  taken at the top of the main loop, a constant few milliseconds after the
  edge.
- SRAM2 is unused by the linker and crt0 never clears it, so the record
  survives the reset that reading it causes. It survives Standby only because
  the build also sets `TAG_RETAIN_SRAM2`, which makes `pwr-l432.c` set
  `PWR_CR3_RRS`. That costs Standby current: **never use this build for power
  runs.**
- The firmware string ends ", edge log", so `tag-info` shows which image is on
  the tag, and the build-options digest differs from a stock build's.

**Build and flash** (this Linux machine, 2026-10-27):

```bash
cmake -S ~/Research/software -B ~/Build/software-edgelog -DBUILD_HOST=OFF \
      -DBUILD_QT_APPS=OFF -DBUILD_EMBEDDED=ON -DREGENERATE_SOURCES=OFF
PATH=~/Software/arm-gnu-toolchain-15.3.rel2-x86_64-arm-none-eabi/bin:$PATH \
  BITTAG_EDGE_LOG=1 cmake --build ~/Build/software-edgelog --target BitTag
python3 embedded/tools/flash_release.py \
  ~/Build/software-edgelog/embedded/tags/BitTag/build/BitTag.elf \
  --programmer ~/Software/STM32CubeProgrammer/bin/STM32_Programmer_CLI --erase
```

The toolchain here is GCC 15.3, not the repo's pinned 14.2.1, so these images
are for testing only. `--erase` is right for BitTag: it has no calibration
table, and the edge-log code moves the stored-configuration region.

**A run:**

1. `tag-reset --set-rtc` (from FINISHED; the erase must be done by the image
   that wrote the log).
2. `tag-start --config runs/bittag-stand-config.json --set-rtc --start-now`.
3. `stand_profile.py ... -o runs/<date>-<name>-stand.csv`.
4. `edge_log.py --save-dump runs/<date>-<name>-sram2.txt -o runs/<date>-<name>-edges.csv`
   — reads SRAM2 under reset with STM32CubeProgrammer.
5. `tag-dwnld --stop -f text -o runs/<date>-<name>-log.txt` for the binned log.

**Attaches fail intermittently with `status=0x81`; retry.** The software
repo's DBG_SLEEP fix (0ba7dc22, in the Rust tools built from
`host/commandline-rs`) removed the in-session bursts, cutting failures from
5 in 10 to 3 in 10. What remains is a failed SWD enter that
`stlink.rs`/`linkadapt.cc` log as a warning and continue past. The Rust
`tag-dwnld` needs the C++ log writer, so downloads use the 3.2 release tool.

Keep run files in `runs/`, never in `/tmp`: a reboot wiped the first five runs.

## 10. Power analysis with the stand

The second use of the stand is completing BitTag's power analysis: what the
tag draws as a function of how much activity it sees. The BitTag
qualification so far measures only an undisturbed tag (0.507 µA running,
0.122 µA resting, at 2.5 V; `~/Research/software/embedded/tags/BitTag/design/power-results.md`).
Its Phase D, activity sensitivity, has never been run: "a stationary tag and an
unresponsive one produce identical data".

### Why the stand suits this

A running tag cannot be observed, but a power run doesn't need to observe it.
The tag runs detached with its production firmware, the Joulescope traces its
current, the stand supplies a logged stimulus, and the tag's `BITPERSEC`
download is read afterwards. The same run therefore gives two results:

- **Power** versus a controlled activity rate.
- **Phase D functional check**: the download's activity bits against the
  stand's log, to the second. Set the tag's clock from the same host
  (`tag-reset --set-rtc`) so the two timebases agree.

No firmware change is needed for this part.

### What the firmware predicts

From `bt_state_run.c`, `devices.c` and the board file:

- **The ADXL362 stays in wake-up mode whatever the motion.** BitTag sets
  `WAKEUP` without `AUTOSLEEP`, so the accelerometer's own current should not
  depend on activity.
- **AWAKE holding high should cost nothing static.** PA2 (`ACCEL_INT`, the
  L432's WKUP4) is a floating input with no standby pull, and the ADXL362
  drives it push-pull.
- **Every AWAKE edge wakes the MCU.** `tagDevicesConfigureWakeupSources()`
  arms the wake pin for the opposite of the current level, so each activity
  and each inactivity is a full `Running()` wake, on top of the minute alarm.

So the expected model is

  I ≈ I_floor + Q_minute / 60 s + Q_edge × (AWAKE edges per second)

and the measurement is the slope Q_edge, plus a check that the model is
linear.

**The inactivity setting decides the edge rate.** The default config's
`inactive_sec = 0.24` rounds to 0 and is clamped to **1 sample** (~160 ms). So
on a default-configured tag AWAKE falls about one sample after motion stops,
each motion costs two wakes, and continuous handling could toggle AWAKE every
few samples — potentially several wakes a second. A long inactivity count
(e.g. 255 samples, ~40 s) instead holds AWAKE high through handling and costs
two wakes per bout. This is the most consequential configuration choice for
field power, and the stand can measure it directly. It is a prediction from
the source; nothing here has measured it.

### Runs

All at 2.5 V, per the BitTag power-test plan: whole-minute windows of at
least 1200 s, `--settle 75`, two windows that agree, `charge/time` not the
window mean. Choose stimulus periods that divide 60 s, so each window holds a
whole number of both the minute alarm and the stimulus.

| Run | Stand profile | Config | Measures |
|---|---|---|---|
| P0 stand control | `still --unload`, servo powered; then servo unpowered | default | Floor on the stand matches the bench's 0.507 µA — rules out noise or ground loops from the servo supply and its USB link, and vibration from the hold |
| P1 single episodes | `pulses --period 60/30/20/10/5` | default | Q_edge from the slope of current against episode rate; wakes counted in the trace (one per 0.5 s block) |
| P2 inactivity setting | same pulse rates | inactivity 1, 25, 255 samples | Edges per episode, and current, against the inactivity count |
| P3 continuous handling | `agitate`, several amplitudes and speeds | default and 255 samples | Worst-case edge rate and current; the upper bound a field estimate needs |
| P4 duty-cycle profiles | bouts of agitation separated by still periods | as deployed | Validates the model against a field-like pattern |

For every run, count AWAKE episodes three ways — Joulescope wakes, download
bits, stand log — and treat any disagreement as a finding before trusting the
power number.

### Practical points

- The Joulescope leads and the tagbase cables ride on the rotor: give them a
  slack loop along the tilt axis (DESIGN-NOTES, cable drag).
- Before each run, follow the bench rules: detach qtmonitor and the Joulescope
  desktop app, use `joulescope_server.py`, confirm 2.5 V before the tag is
  connected, and attach twice to a sleeping BitTag.
- Threshold-crossing reliability matters more than jolt here: tilt well past
  the 0.35 g default threshold (30°, 0.5 g) with moderate move times
  (400–600 ms).

### Runner: `stand_profile.py`

[`stand_profile.py`](stand_profile.py) runs `still`, `pulses`, `agitate` and
`bouts` (section 11) profiles for a set number of minutes, starting stimuli on whole host seconds
(or the next whole minute with `--start-on-minute`), with optional torque-off
while level (`--unload`). It writes a CSV of every command and a position
trace (10 Hz by default) in host UTC.

```bash
python3 stand_profile.py pulses --period 30 --angle 30 --hold 2 --minutes 20 --start-on-minute -o p1-30s.csv
python3 stand_profile.py agitate --angle 30 --move-ms 600 --minutes 20 -o p3.csv
python3 stand_profile.py still --minutes 20 --unload -o p0.csv
```

Tried on the bare servo: stimuli started within 5 ms of the whole second. In
`agitate`, a reversal at 500 ms per 20° swing reached about ±17°, so analyse
logged positions, not commanded angles.

## 11. Verifying the activity bins

BitTag stores activity in bins. The check is that every bin holds the right
count under the right time label, in every log format. This runs from the
same detached runs as section 10.

### How the bins are built

From `bt_state_run.c` and the host decoder
(`host/libraries/tagcore/sqlitelog/bittag.cc`):

| Format | Bin | Value | Bins per record | Record every |
|---|---|---|---|---|
| `BITPERSEC` | 1 s | 1 bit, active or not | 60 | 60 s |
| `BITSPERMIN` | 60 s | active-second count, 6 bits | 10 | 600 s |
| `BITSPERFOURMIN` | 240 s | count, 8 bits | 8 | 1920 s |
| `BITSPERFIVEMIN` | 300 s | count, 9 bits | 7 | 2100 s |

- **Bins sit on an absolute grid**: multiples of the bin period since the
  epoch, with records on multiples of the record period. The first record of
  a run can start before the run, with those bins zero (already confirmed in
  BitTag's results).
- **Each row is labelled with its bin's end time.** The second s is stored as
  s + 1, and a 60 s bin covering [t, t + 60) is stored as t + 60. Comparing
  against start times gives a one-bin error that looks like a firmware fault.
- The counted formats are stored as a percentage, count × 100 / bin period.
- **What counts as active.** The firmware reads the RTC second, an integer, at
  each wake. When it wakes with AWAKE high it marks the run start; at the next
  wake it sets every second from that start up to, but not including, the
  current second. AWAKE edges are wakes, so an episode from t_rise to t_fall
  should count the whole seconds **floor(t_rise) ≤ s < floor(t_fall)**.
  Prediction from the source: an episode that starts and ends inside the
  same second counts **zero**.

### Reference times

The stand log gives when motion happened, not when AWAKE changed. AWAKE rises
up to one sample (~160 ms) after the tilt crosses the threshold, and falls the
inactivity count of samples after motion stops. Use the most direct reference
available:

1. **Joulescope wakes**: the actual AWAKE edges, in host time, to within one
   0.5 s block (finer from a raw trace). Compute expected bins from these.
2. **The stand log**, widened by one sample at each rise and by the inactivity
   time at each fall, where no trace is available.

Set the tag clock from the same host (`tag-reset --set-rtc`), and read the
tag's clock again after the run (`get_status` millis versus host time) to
measure any offset. The RV-3028 drifts about 1 ppm, which is negligible over a
run.

**Use a moderate inactivity count**, not the default 1 sample, so each bout is
one continuous episode with a known tail. With 1 sample, AWAKE may flicker
during agitation and drop sub-second gaps. That is worth measuring too, but
separately.

### Checks

| Check | Stimulus | Pass |
|---|---|---|
| Labels and alignment | Any run | Bin labels are bin end times on the absolute grid; record epochs are multiples of the record period |
| Contents | `bouts` with distinct durations per bin (e.g. 2, 5, 10, 20, 40 s), each well inside one bin | Each bin's count equals the expected active seconds, within ±1 s per episode edge. A count that matches a neighbouring bin's expected value means a one-bin shift. |
| No false activity | Still bins between bouts, and P0 | All zero |
| Bin boundaries | Bouts that straddle a bin boundary | Seconds split across the two bins as computed |
| Record boundaries | Bouts that straddle a record boundary | Split correctly across the two records; the firmware writes and clears its accumulator there |
| Full bins | Agitation through one whole bin | 100% (60, 240 or 300 counts), no wrap of the 6, 8 or 9-bit field |
| Sub-second episodes | Short `pulses` with `--offset` 0.1 versus 0.8 | Counted only when the episode crosses a second boundary, as predicted |
| Format consistency | The same `bouts` schedule under each format | Per-bin sums agree across formats |

The tag can only be configured with one format per run, so the format
consistency check needs one run per format, with the same schedule.

### Runner support

`stand_profile.py bouts --period P --bouts 2,5,10,20,40` agitates for each
duration in turn at the start of each period, then holds level. `--offset`
places the start inside the second; with `--start-on-minute` and a 60 s
period, each bout starts at the same point in its 60 s bin. Tried on the bare
servo: bouts began within 4 ms of the requested half-second and ended on
schedule.

A script to compute expected bins from the stand log and Joulescope wakes and
compare them with the SQLite download should be written once a first run
provides real data to check it against.

## 12. Next steps

When the stand is assembled:

1. Meter the servo supply (section 3); fit a regulated 7.4 V supply if the
   7.5 V adapter really idles near 8.1 V.
2. Level the stand: trim with the angle offset against the tag's own
   accelerometer. Already done: the servo was centred at 500 before the U was
   bolted on.
3. Re-run the speed measurements with the rotor loaded. Already done: the range
   and loaded accuracy (section 4a).
4. Check whether the servo holds position with torque off under the rotor's
   gravity load, and whether loaded hold jitter is visible to the tag.

Then, with a tag base connected:

5. Done: the BitTag (UUID `2035374D303150190059002F`) runs the edge-log build
   (section 9), and the first results are in section 13. The base powers the
   tag at 3.3 V, so power runs need the Joulescope at 2.5 V. tag-server was
   not needed.
6. Run a still-only test to explain the stray episodes (section 13).
7. Threshold and inactivity-time sweeps: step the tilt across the activity
   threshold, and vary `inactive_sec` against bout length.

For the power analysis, which needs a tag base and the Joulescope but no new
firmware:

8. Run P0 (stand control) before anything else; if the floor on the stand
   differs from the bench's 0.507 µA, fix the rig first.
9. Run P1–P4 (section 10), and append results to BitTag's
   `power-results.md` as its Phase D.
10. Check the bins (section 11) on the same runs, one run per log format for
    the format consistency check.

## 13. Results

### 2026-10-27: tilt pulses, 1 s bins (data lost with `/tmp`)

Configuration: activity 0.25 g, inactivity 0.15 g for 3 samples,
`BITTAG_BITPERSEC`, 3.3 V from the tag base. Profile `pulses --angle 30
--period 20 --hold 2 --move-ms 600` for 5 minutes, 15 pulses.

- **Every move produced exactly one activity episode**: 30 rises and 30 falls
  for 15 tilts and 15 returns, none missed or extra.
- **Activity was flagged 0.21–0.55 s after the move command** (median
  0.45 s); **inactivity about 0.5 s after motion stopped** (0.28–0.64 s).
- **Episode lengths are quantised in 0.166 s steps** (0.499, 0.665, 0.832,
  0.996 s): wake-up mode samples at 6 Hz, and 3 samples is the 0.5 s minimum.
- **The minute-alarm wakes landed on :00.000**, so tag and host clocks agree.
- **The 1 s log matched the edges exactly**: 14 logged seconds, each predicted
  by `floor(rise) ≤ s < floor(fall)`, none missing or extra.
- **But only 14 of 31 episodes appear in the log.** BitTag counts whole
  seconds from the active wake to the inactive wake, so an episode that starts
  and ends within one second logs nothing. A sub-second episode is recorded
  only if it crosses a second boundary — by design, but it matters when
  reading the bins.

### 2026-10-27/28: holding the tag active for 5 s

A held tilt cannot keep the tag active; continuous motion can. Profile
`bouts --bouts 5 --period 20 --angle 30 --move-ms 600` for 5 minutes: 5 s of
±30° swings every 20 s, then a return to level. Same configuration.

| Supply | Run | One ~5 s episode | Split by a servo stall | Split by the detector |
|---|---|---|---|---|
| 7.5 V adapter, 4.2–8.6 V | 2 | 12 of 15 | 2 | 1 |
| | 3 | 12 of 15 | 3 | 0 |
| | 4 | 13 of 15 | 1 | 1 |
| | 5 | 13 of 15 | 1 | 1 |
| Replacement, 6.5–7.8 V | [2026-10-28](runs/) | **15 of 15** | 0 | 0 |

- **Clean episodes last 4.65–5.82 s** for 5 s of swinging plus a 0.6 s
  return: activity flagged about 0.45 s after the bout starts, inactivity
  about 0.5 s after motion ends, in 0.166 s steps.
- **Servo stalls**: on the adapter, a reversal pulled the supply to 4.2–4.8 V
  and the servo held still for about a second, which the tag rightly reported
  as inactivity. The new supply removed them. `stand_profile.py` now also
  resends dropped writes (one in 150 swings) and restarts a swing that has not
  begun moving toward its target after 0.2 s, logging both.
- **Detector splits**: about once per run on the adapter, the tag went
  inactive for 0.5 s at the turnaround of the first swing, sitting within
  0.15 g of the reference it latched at activity for 3 samples. That is the
  detector working as configured. Faster or larger swings, or a longer
  inactivity time, avoid it.
- **Two stray 0.5 s episodes on 2026-10-28**, at 23:21:43 and 23:22:45 UTC,
  between bouts while the servo read a steady 498. Either an outside knock or
  something in the detector; a still-only run will tell.
