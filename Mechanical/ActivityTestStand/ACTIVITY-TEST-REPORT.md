# BitTag activity detection on the servo test stand — test report

Tests run 2026-10-25 to 2026-10-29 on a BitTag V6 (UUID
`2035374D303150190059002F`) mounted on the activity test stand. The working
notes and full tables are in [`SERVO-AND-TEST-PLAN.md`](SERVO-AND-TEST-PLAN.md)
(section 13); what to know before the next round is in
[`LESSONS-LEARNED.md`](LESSONS-LEARNED.md). Every run's raw files are in
[`runs/`](runs/).

## 1. Introduction

BitTag records activity, not acceleration. Its ADXL362 accelerometer decides
on its own when the tag is active or inactive and signals the change on one
line (AWAKE); the MCU wakes on each change and counts active seconds into
bins. Everything BitTag logs therefore depends on how the ADXL362's detector
behaves under the settings BitTag gives it: the activity threshold, the
inactivity threshold, and the inactivity time.

These tests measured that behaviour directly, with a known, repeatable
motion. A servo tilts the tag through programmed angles at programmed speeds,
logging its position throughout; a special BitTag build timestamps every
activity change to the millisecond; and scripts compare the two. The goals
were:

1. Confirm the stand and a way of observing a running tag.
2. Measure the activity threshold, inactivity time and inactivity threshold
   against their configured values.
3. Find out what kinds of motion the detector catches or misses: small,
   brief, held and continuous.
4. Check that BitTag's activity log records exactly what the detector
   reported, in all four log formats.

**In brief:** the detector does what it is configured to do, and the log
records it exactly. The surprises are all consequences of the ADXL362's
*referenced* detection — every change is measured from a reference that
moves — and of its 6 Hz sampling in wake-up mode. They matter for anyone
interpreting BitTag activity data from the field.

**Power** has begun: section 5.9 has the stand control and a first
field-like workload, on stock firmware under a Joulescope. **Not covered:**
the remaining power runs, and tilts about the tag's second horizontal axis,
which needs the tag remounted.

## 2. The test setup

| | |
|---|---|
| Tag | BitTag V6 on a tag base, powered at 3.3 V by the base |
| Tilt | Hiwonder LX-16A bus servo, tag 44 mm above the tilt axis; safe range ±100° |
| Servo interface | BusLinker V3.0 (CH9102 USB serial, `/dev/ttyACM0`), 115200 baud |
| Servo supply | Replacement supply, 6.1–8.3 V under load; the original 7.5 V adapter sagged to 4.2 V and stalled the servo |
| Host | This Linux machine; tag and host clocks set together with `--set-rtc` |

Tilting by θ changes the tag's in-plane axis by sin θ g, so 0.25 g is 14.5°
and 1 g is 90°. Unless stated, the tag ran BitTag's settings with the
activity threshold at 0.25 g, the inactivity threshold at 0.15 g, and 1 s
(`BITTAG_BITPERSEC`) bins.

## 3. Tools

### 3.1 Driving the stand

All Python, in this directory:

| Tool | Role |
|---|---|
| [`lx16a.py`](lx16a.py) | Driver for the full LX-16A bus protocol: moves, position, voltage and temperature read-back, torque on/off. Corrects two errata in the vendor's protocol PDF. `move_checked()` reads back each target and resends, since about one write in 150 is silently dropped. |
| [`stand_profile.py`](stand_profile.py) | Runs a motion profile and logs every command and a position, voltage and temperature sample every 30–100 ms to CSV. Profiles: `still`, `pulses`, `bouts`, `agitate`, `steps`, `gaps`, `nudge`, `blip`, `rock`. Detects and restarts stalled swings, and works in angles from true level (servo +3.2°, measured from the tag's own gravity vector). |

### 3.2 The edge-log tag binary

**The problem:** a running BitTag cannot be observed. Attaching the debug
probe resets it, and BitTag's own log is in whole seconds.

**The solution** is a BitTag build that records its own activity changes and
is read after the run. It is built from the software repo, branch
`accel-testing` (commits `757b1150` and `cc2fb9b9`), with `BITTAG_EDGE_LOG=1`:

- BitTag already wakes from Standby on every AWAKE edge and on a minute
  alarm. At each wake the edge-log build appends a 16-byte record: RTC
  seconds, milliseconds, the AWAKE level, and the ADXL362's current X/Y/Z
  sample. A change of level between records is an edge.
- The RTC runs from the RV-3028's 32.768 kHz output with a 1024 subsecond
  prescaler, so records resolve 1 ms. The minute alarms land on :00.000, and
  host and tag agreed to within the 0.02 s of `--set-rtc`.
- The records go into a 1023-slot ring in SRAM2 (0x10000000), marked
  "EDG2". SRAM2 is not used by the linker or cleared at boot, so it survives
  the reset that reading it causes. It survives Standby only because the
  build sets `PWR_CR3_RRS`, which costs Standby current: **this build is for
  timing runs only, never power runs.**
- The firmware string ends ", edge log", so `tag-info` shows which image is
  on a tag.
- The X/Y/Z on the minute-alarm records, taken while the tag is still, is
  its gravity vector. That is how the stand was levelled and the tag's zero-g
  offsets measured (X +82 mg, Z +187 mg), with no other instrument.

Build and flash (details in the plan, section 9):

```bash
PATH=~/Software/arm-gnu-toolchain-15.3.rel2-x86_64-arm-none-eabi/bin:$PATH \
  BITTAG_EDGE_LOG=1 cmake --build ~/Build/software-edgelog --target BitTag
python3 embedded/tools/flash_release.py \
  ~/Build/software-edgelog/embedded/tags/BitTag/build/BitTag.elf \
  --programmer ~/Software/STM32CubeProgrammer/bin/STM32_Programmer_CLI --erase
```

The image is built with GCC 15.3 rather than the pinned 14.2.1, so it is for
testing only. Before flashing, the disassembly was checked for the
`PWR_CR3_RRS` write before `wfi`, the magic constant and the SRAM2 address,
because link-time optimisation leaves no symbol to check.

### 3.3 Talking to the tag

Each run talks to the tag four times, all over the ST-Link in the tag base:

| Step | Tool | Notes |
|---|---|---|
| Erase and set the clock | `tag-reset --set-rtc` | Rust tools, built from `~/Research/software/host/commandline-rs` |
| Configure and start | `tag-start --config <json> --set-rtc --start-now` | Sets the thresholds, inactivity time and log format per run |
| Read the edge log | `STM32_Programmer_CLI -c port=SWD mode=UR -r32 0x10000000 0x4000` | Under reset, via [`edge_log.py`](edge_log.py), which decodes it to CSV |
| Download the activity log | `tag-dwnld --stop -f text` | The 3.2 release tool; the Rust `tag-dwnld` needs the C++ log writer |

**Attaches fail intermittently with status 0x81.** Two causes were found:

- Bursts of failures inside a session, which broke long commands, came from
  DBG_SLEEP being clear. The software repo fixed this (`0ba7dc22`), and the
  rebuilt Rust tools carry the fix.
- A failed SWD entry remains, about 3 attaches in 10. The tools log it as a
  warning, carry on, and fail at the first register read. A retry works, so
  the runner retries each step up to 10 times and keeps the last attempt's
  output.

STM32CubeProgrammer's connect-under-reset also fails occasionally; it
succeeded right after a `tag-info`.

### 3.4 Running and scoring a test

| Tool | Role |
|---|---|
| [`run_trial.py`](run_trial.py) | One test end to end: writes the configuration, resets and starts the tag, runs the profile, reads the edge log, downloads the activity log. All files go to `runs/<date>-<name>-{config.json, stand.csv, sram2.txt, edges.csv, log.txt}`. |
| [`analyze_trials.py`](analyze_trials.py) | Scores each trial's stand log against the tag's edges, by profile: detections per tilt, inactivity per pause, restarts per nudge, capture per blip time, inactivity per rocking amplitude. Scores the tag's *state* during each window, not just its edges, since a tag already inactive has no edge to find. |
| [`analyze_bins.py`](analyze_bins.py) | Predicts every bin of the activity log from the edges and compares, in all four formats. |

```bash
python3 run_trial.py 2026-10-29-inthr020-neg --act 0.6 --inact 0.20 --samples 6 \
  -- rock --angles=7.69,10.01,11.17,12.34,13.51,15.28,18.26 --reps 3 --shuffle 29 \
     --bout 6 --reset-angle=-60 --move-ms 600 --poll 0.03 --rest 4
python3 analyze_trials.py runs/2026-10-29-inthr020-neg
```

## 4. Tests run

| Test | Profile | Settings varied | Runs |
|---|---|---|---|
| Stand range and accuracy | servo only | ±15° to ±100° | 2026-10-27 |
| Tilt pulses | `pulses` | — | 2026-10-27 (lost with `/tmp`) |
| Holding the tag active | `bouts` | supply | 2026-10-27/28, 5 runs |
| Activity threshold | `steps` | 0.35, 0.5, 0.85 g | `act0{35,50,85}-*` |
| Inactivity time | `gaps` | 3, 6, 9 samples; 0.25 s and 0.1 s pause steps | `inact{3,6,9}`, `inact{6,9}-fine` |
| Still stand, torque on and off | `still` | torque | `still-torque`, `still-unload` |
| Levelling and offsets | held tilts ±30–90° | — | `gravity` |
| Small moves | `nudge` | size; out and back or held 3 s | `nudge`, `nudge-hold` |
| Brief moves | `blip` | time past threshold | `blip` |
| Inactivity threshold | `rock` | 0.1, 0.2, 0.3, 0.5 g; amplitude | `inthr*`, three passes |
| Activity log | `bouts` | all four formats | `bins-{sec,min,fourmin,fivemin}` |

About 35 tag runs in all, each scored from its own files.

## 5. Results

### 5.1 The stand

- **Range and accuracy:** ±100° is safe; the servo stops within 3 counts
  (0.75°) of its target under load, slightly short on the + side.
- **Level:** true level against gravity is servo +3.2°, from the tag's own
  X/Z at held tilts. Earlier results, measured from servo centre, shift by at
  most 0.03 g.
- **Holding still:** in 10 minutes with torque on (jitter ±0.8°) and 10 with
  torque off (drift ≤ 1 count per minute), the tag reported no activity.
- **Supply:** the original adapter sagged to 4.2 V at swing reversals and
  stalled the servo for about a second, 1–3 times per 15 bouts, which the tag
  correctly reported as inactivity. The replacement supply removed every
  stall (15 of 15 bouts clean).
- **Commanded is not reached:** short out-and-back moves turn round early (a
  10° nudge peaked at 8.1°), and small rocking falls 0.6–1° short. Results
  are scored against logged positions, not commands.

### 5.2 Sampling

**The ADXL362 samples at about 6 Hz in wake-up mode**, 0.163 s per sample,
and that sets every timing result:

- Activity episodes come in 0.166 s steps.
- `inactive_sec` is a sample count, not seconds: each 3 samples added
  0.47–0.51 s.

### 5.3 Activity threshold

Tilts from level to 0.8–1.2× each threshold, 3 reps, shuffled, with a reset
snap before each trial:

| Threshold | Never detected | Sometimes | Always detected |
|---|---|---|---|
| 0.35 g | ≤ 0.315 g | 0.332 g (1/3) | ≥ 0.367 g |
| 0.5 g | ≤ 0.475 g | — | ≥ 0.525 g |
| 0.85 g | ≤ 0.765 g | 0.807 g (2/3) | ≥ 0.893 g |

**Each threshold switches within ±5% of nominal**, inside the ADXL362's ±10%
sensitivity tolerance. Every detected tilt then went inactive while held: a
held tilt never keeps the tag active.

Two small items: BitTag's threshold conversion truncates instead of rounding,
so 0.35 g is stored as 0.348 g (a 2 mg error; fix by adding 0.5 before the
cast); and the tag's zero-g offsets are irrelevant to the detector, which
measures change.

### 5.4 Inactivity time

Two bouts of swinging separated by a still pause; does the tag go inactive in
the pause?

| Samples | Nominal | Fall after motion stops | Pause that splits two bouts |
|---|---|---|---|
| 3 | 0.5 s | 0.38 s median | every pause, even 0.25 s |
| 6 | 1.0 s | 0.89 s median | a band, 0.6–0.9 s |
| 9 | 1.5 s | 1.36 s median | a band, 0.8–1.6 s |

**Inactivity comes about 0.1 s sooner than N/6 s after motion stops, and a
pause well short of it can split an episode.** The tag counts still samples
as soon as it is within the threshold of its reference, which is while the
stand is still decelerating. How much of the countdown is done by the time it
stops varies by about 0.7 s, so the split point is a band, and 0.1 s steps
did not narrow it. At 3 samples, the dwell at a swing's turnaround was once
enough to drop out mid-swing (1 of 54 bouts).

### 5.5 Continuous motion and held changes

- **Continuous swinging holds the tag active:** ±30° swings at 600 ms each
  gave one unbroken episode per 5 s bout, 15 of 15, lasting 4.65–5.82 s.
- **A held change becomes the new normal.** Nudges of 0.1–0.3 g held for 3 s
  restarted the countdown, then the tag went inactive while still displaced.
  So a posture change on an animal shows as one short episode, not a long
  one.

### 5.6 Small and brief moves

**Small moves near the inactivity threshold restart the countdown with odds,
not certainty** (inactivity 0.15 g, 9 samples):

| Peak change | 0.03 g | 0.08 g | 0.11 g | 0.14 g | 0.17 g | 0.26 g |
|---|---|---|---|---|---|---|
| Countdown restarted | 0/3 | 1/3 | 2/3 | 3/3 | 2/3 | 3/3 |

Restarts below 0.15 g come from a reference latched a few degrees past level
while the previous move settled; the 0.17 g miss is a sample falling outside
the nudge's brief peak.

**A brief move is caught only if a sample lands on it.** Full-speed blips
just past the 0.25 g activity threshold:

| Time past the threshold | 0–0.05 s | 0.05–0.10 s | 0.10–0.15 s | 0.15–0.20 s |
|---|---|---|---|---|
| Detected | 2/5 | 8/13 | 7/7 | 5/5 |

That fits a capture probability of about D / 0.163 s for a move lasting D.

### 5.7 Inactivity threshold

After a snap wakes the tag, the stand rocks it ±A about level for 6 s. Does
the rocking keep it active? Steady-rocking trials that went inactive, pooled
over thresholds of 0.1, 0.2, 0.3 and 0.5 g, by amplitude (sin A) ÷ threshold:

| Amplitude ÷ threshold | < 0.7 | 0.7–0.9 | 0.9–1.0 | 1.0–1.1 | 1.1–1.2 | 1.2–1.35 | 1.35–1.6 | ≥ 1.6 |
|---|---|---|---|---|---|---|---|---|
| Went inactive | 22/27 | 16/25 | 6/15 | 5/17 | 2/7 | 0/17 | 0/22 | 0/9 |

**Rocking holds the tag active only when its amplitude exceeds about 1.2×
the inactivity threshold — about 2.4× peak-to-peak**, and that holds at every
threshold tested. The reason is the moving reference: each sample that
exceeds the threshold becomes the new reference, so the reference settles
mid-swing, and from there the largest change is the amplitude. A simulation
of that rule over each trial's logged motion puts the switch at 1.0–1.25×,
agreeing with the measurement.

Caveats: 110 of 249 trials went inactive in the first 1.2 s, before the
rocking was under way (the snap's countdown was already partly run), and are
excluded; and at 0.1 g the servo's jerky small reversals blur the switch.

### 5.8 The activity log

`bouts` of 2–40 s every 50 s, plus a first bout long enough to fill a whole
bin, one run per format, each crossing a record boundary:

| Format | Bins checked | Full bins | Active seconds, logged = predicted | Mismatched |
|---|---|---|---|---|
| 1 s (`BITPERSEC`) | 709 | 218 | 218 | 0 |
| 1 min (`BITSPERMIN`) | 8 | 2 | 238 | 0 |
| 4 min (`BITSPERFOURMIN`) | 6 | 1 | 1306 | 0 |
| 5 min (`BITSPERFIVEMIN`) | 9 | 1 | 2216 | 0 |

- **Every bin matches.** Labels are bin end times on an absolute grid, and
  each count is exactly the whole seconds from the active wake to the
  inactive wake. Full bins store 60, 240 and 300 without overflowing their
  6, 8 and 9-bit fields.
- Across all 20 1 s runs: 4,962 bins, no mismatch.
- **But a 1 s log does not record every episode.** An episode that starts
  and ends within the same second counts zero seconds. In one run, 14 of 31
  sub-second episodes appeared in the log. This is the design as written,
  and it matters when reading activity counts from the field.

### 5.9 Power (first runs)

Stock `fw-v0.6`, default config (activity 0.35 g; inactivity 0.35 g after 1
sample), 2.5 V through a Joulescope JS320 driven by `joulescope_server.py`;
two 1200 s windows per run, `charge/time`.

| Run | Window 1 | Window 2 |
|---|---|---|
| P0, stand still | 0.5126 µA | 0.5109 µA |
| P4, discrete-Pareto bouts, 20% scheduled | 0.7762 µA | 0.8106 µA |

- **The stand adds nothing**: P0 matches the bench qualification
  (0.507–0.508 µA) within 1%, with no logged activity.
- **The Pareto workload costs about 3.2 µC per bout**, 0.27–0.30 µA over
  still. Bout lengths 0–30 s with P(x) ∝ 1/(x+1)^α (α = 3.66), drawn once per
  still second, calibrated to be active 20% of the time.
- **The tag logged only 4.7% as active.** With the default inactivity
  setting, a ±30° bout breaks into sub-second episodes (holding active needs
  1.2 × 0.35 g amplitude, section 5.7), most of which a 1 s log does not
  record, while each still costs wakes.

## 6. What this means for BitTag data

1. **Activity counts are counts of whole seconds between detector changes**,
   exactly as logged. Short episodes can vanish in any format.
2. **The detector measures change, not motion.** A held posture change is
   one short episode. Continuous motion is needed to stay active, and it
   must keep moving more than about 1.2× the inactivity threshold from
   wherever it last was.
3. **Near any threshold, detection is a probability** — for brief moves
   (D / 0.163 s), small moves, and pauses near the inactivity time.
4. **`inactive_sec` is in samples of about 0.163 s.** The chip's sample rate
   is unspecified and varies by about 3% between parts, so inactivity times
   carry that uncertainty.
5. **Thresholds are accurate to ±5%**, within the ADXL362's tolerance.
6. **The default config under-records sustained motion.** Its 0.35 g, 1-sample
   inactivity setting split ±30° bouts into fragments: a workload scheduled
   20% active logged 4.7%.

## 7. Remaining work

- **Power versus activity** (plan section 10): P1–P3, and P4 at longer
  inactivity counts. Count the wakes behind P4 by re-running its seed on the
  edge-log build (which cannot itself measure power).
- **The second horizontal axis**, with the tag remounted at 90°.
- **An inactivity-threshold protocol in which the rocking itself starts each
  episode**, to recover the trials lost to the wake-up snap.
- **The threshold rounding fix** in `clampAdxl362Threshold()`.

## 8. Where things are

| | |
|---|---|
| Stand code, scripts, results | `hardware` repo, branch `accel-testing`, `Mechanical/ActivityTestStand/` (commits `c862a7e`, `99ba552`, `02ab890`, `92fc5be`) |
| Edge-log firmware | `software` repo, branch `accel-testing`, `embedded/tags/BitTag/inc/edge_log.h` and `src/bt_state_run.c` (`757b1150`, `cc2fb9b9`) |
| Run data | [`runs/`](runs/), one prefix per run; campaign scripts `runs/2026-10-29-*.sh` |
| Detailed tables | [`SERVO-AND-TEST-PLAN.md`](SERVO-AND-TEST-PLAN.md) section 13 |
| Lessons | [`LESSONS-LEARNED.md`](LESSONS-LEARNED.md) |
