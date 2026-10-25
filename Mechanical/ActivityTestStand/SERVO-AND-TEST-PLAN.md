# Activity test stand — servo control and test plan

Status as of 2026-10-25. The stand is not yet assembled: every servo figure
below was measured on a bare LX-16A with nothing on its horn, driven through
the BusLinker V3.0 from this machine. Re-measure motion once the rotor, U
bracket and tagbase are mounted.

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
- **Testing needs a small BitTag firmware mode** to configure the
  accelerometer and timestamp its AWAKE line while the host is attached, plus
  a host script that combines the servo and tag-server.
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

## 3. Supply voltage — unresolved

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

## 9. Proposed implementation

**The constraint**: a running tag cannot be observed — attaching resets it
(software repo `AGENTS.md`). In IDLE the firmware shuts the ADXL362 down. So
the accelerometer has to be configured, and watched, while the host is
attached.

**Firmware: a BitTag stand mode**, behind a custom define so production
images are unchanged:

- While attached, call the same `adxl362_init()` as `Running`, with thresholds
  and count from the host, so the test exercises the production register
  setup.
- Timestamp AWAKE edges (EXTI on `LINE_ACCEL_INT`) into a RAM ring buffer:
  level and tag milliseconds.
- Optionally record raw XYZ for move characterisation.
- Open question: thresholds through the existing `Start(Config)` path or a new
  test request.

**Host: `activity_stand.py`** beside `lx16a.py`, using `tagclient` over
tag-server (run with `--enable-debug` for `read_memory`): configure, level
calibration, trial matrix, polling the edge buffer, one CSV of servo positions
and tag edges. Before the firmware exists, `read_u32` on the GPIO input
register can poll the AWAKE line directly, but something must still configure
the accelerometer.

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
2. Level the stand: centre the servo (500) before bolting on the U, then trim
   with the angle offset against the tag's own accelerometer.
3. Re-run the positioning and speed measurements with the rotor loaded.
4. Check whether the servo holds position with torque off under the rotor's
   gravity load, and whether loaded hold jitter is visible to the tag.

Then, with a tag base connected:

5. Build tag-server (`~/Research/software/host/tagserver/README.md`) and
   install the tag base udev rule (`host/linux/70-ultralight-tags.rules`,
   needs `sudo`).
6. Write the BitTag stand mode, following the software repo's flashing
   protocol (record UUID, erase, flash, self-test).
7. Write `activity_stand.py` and run the wake-up rate test first.

For the power analysis, which needs a tag base and the Joulescope but no new
firmware:

8. Run P0 (stand control) before anything else; if the floor on the stand
   differs from the bench's 0.507 µA, fix the rig first.
9. Run P1–P4 (section 10), and append results to BitTag's
   `power-results.md` as its Phase D.
10. Check the bins (section 11) on the same runs, one run per log format for
    the format consistency check.
