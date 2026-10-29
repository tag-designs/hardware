# Activity test stand — lessons learned

From the first week of testing ADXL362 activity detection on BitTag V6 with the
servo tilt stand, 2026-10-25 to 2026-10-28. The measurements are in
[`SERVO-AND-TEST-PLAN.md`](SERVO-AND-TEST-PLAN.md) section 13 and
[`runs/`](runs/). This page is what to know before the next test, and why.

## The short version

1. **A running tag cannot be watched, so make it record and read it after.**
   The BitTag edge-log build timestamps every activity and inactivity change
   to 1 ms in retained SRAM2. It worked first time and needs no tag-server.
2. **The ADXL362 measures change from a remembered reference.** That
   reference is wherever the tag last went inactive. Most of the confusing
   results this week came from a reference left somewhere unexpected.
3. **Supply first.** Every servo misbehaviour traced back to the 7.5 V
   adapter sagging at reversals. Logging the servo's own voltage on every row
   is what found it.
4. **Score by state, not by events.** A tag that is already inactive has no
   edge to find.
5. **Keep data in the repo, never in `/tmp`.** A reboot deleted the first five
   runs.

## Observing the tag

**Attaching resets the tag, so record during the run and read afterwards.**
BitTag already wakes from Standby on every AWAKE edge, so the cheapest record
is one per wake: the RTC time and the AWAKE level. The record lives in SRAM2,
which survives the reset that reading it causes. It survives Standby only if
`PWR_CR3_RRS` is set, and stock BitTag clears it. That retention costs current,
so the edge-log build is for timing runs only, never for power runs.

**Check the built image, not the source.** With link-time optimisation the
Standby path has no symbol of its own. Before flashing, the disassembly was
checked for:

- the `orr #0x100` into `PWR_CR3` just ahead of the `wfi`;
- the magic constant and the SRAM2 address;
- the ", edge log" firmware string.

The string also lets `tag-info` show which image is on a tag, and the
build-options digest separates it from a stock build.

**The RTC is good enough to timestamp edges.** It runs from the RV-3028's
32 kHz clock with a 1024 subsecond prescaler, so it resolves 1 ms. The
minute-alarm wakes landed on :00.000, and host and tag clocks agreed to within
the 0.02 s that `--set-rtc` achieves.

## Talking to the tag

**There were two different 0x81 attach faults; only one is fixed.**

- **0x81 bursts inside a session** came from DBG_SLEEP being clear. They broke
  long commands such as `tag-start` and `tag-test`. The software repo fixed
  them (0ba7dc22), and the Rust tools built from `host/commandline-rs` carry
  the fix.
- **A failed SWD enter** remains. It is logged as a warning and the attach
  carries on, then fails at the first register read. About 3 attaches in 10
  still fail this way. Retrying works.

**When a retry loop fails every time, read the error before blaming the
link.** Twelve consecutive "attach failures" one morning were really "Cannot
open config file": the reboot had emptied `/tmp`. The retry loop had been
discarding each attempt's output. Keep the last attempt's output, and treat a
streak of identical failures as information.

**Building and flashing on this Linux box:**

- The firmware build is CMake-driven. Configure with `BUILD_HOST=OFF`, and
  pass `BITTAG_EDGE_LOG=1` through the environment, which make reads.
- The toolchain here is GCC 15.3, not the pinned 14.2.1, so these images are
  for tests only.
- Flash with `flash_release.py --erase`, which checks the image against its
  build manifest first.
- CubeProgrammer's connect-under-reset also fails now and then, and succeeded
  right after a `tag-info` woke the tag.

## The stand

**Servo writes are never acknowledged, so confirm them.** About one move in
150 was silently dropped. `move_checked()` reads the target back and resends.

**A stall that persists after a resend is the supply, not the bus.**

- Three to five bouts in every run on the old adapter froze the servo for
  about a second. The read-back target was correct; the horn simply did not
  move.
- The voltage column showed why: 4.2–4.8 V at the moment of each stall, with
  the servo rated 6–8.4 V.
- A software restart could not fix it. A stronger supply did: 15 of 15 bouts
  clean, at 6.5–7.8 V.
- Fixing a fault in software can hide its cause. Change one thing at a time:
  the re-run with only the resend fix added is what showed that dropped writes
  were not the explanation.

**Move speed is part of the stimulus.**

- Full-speed moves jolt the tag by an estimated 0.4–0.75 g, the same size as
  the thresholds being tested. Threshold tilts use 1.5 s moves.
- Returns use 400 ms, for the reference reason below.

## The detector

**A steady tilt is not activity.** After any tilt, held or not, the tag went
inactive about 0.5 s after the motion stopped. Keeping a tag active takes
continuous motion. ±30° swings at 600 ms each held it for 5 s in 15 of 15
bouts, and those episodes ran 4.65–5.82 s.

**Everything is quantised by wake-up mode's 6 Hz sampling.**

- Episode lengths come in 0.166 s steps.
- `inactive_sec` is a count of samples, not seconds: each 3 samples added
  0.47–0.51 s.

**Thresholds are accurate.**

- 0.35, 0.5 and 0.85 g each switched within about ±5% of nominal, inside the
  ADXL362's ±10% sensitivity tolerance.
- The stand's level (servo 500, never calibrated against gravity) and the
  tag's alignment on the platform also contribute at the few-percent level.

**Referenced detection remembers.** Each change is measured from the sample
at which the tag last went inactive. That made the first threshold runs
inconsistent in two ways:

- A slow return to level let inactivity be declared mid-return. The reference
  latched a few degrees off level, and the next trial's tilt looked smaller
  than it was.
- A just-detected tilt was followed by a return below threshold, which was not
  detected. The reference stayed tilted, and the next trial measured from
  there.

**The fix is to reset before every trial:** a quick snap past the threshold,
back to level in 400 ms, then rest. That is faster than the inactivity time,
so the tag always settles at true level. The same will happen on an animal:
what counts as a change depends on where it last came to rest.

**The inactivity time comes out shorter than it reads.**

- The tag starts counting stillness as soon as it is within the inactivity
  threshold of the reference, which is before the servo has fully stopped.
- So falls came about 0.1 s under N/6 s, and pauses about 0.4 s short of N/6 s
  were enough to split two bouts.
- At 3 samples (0.5 s) the dwell at a swing's turnaround can be enough on its
  own: one bout in 54 dropped out mid-swing.

## The activity log

**A 1-second log does not record every activity episode.** BitTag counts the
whole seconds from the wake at which AWAKE went high to the wake at which it
went low. An episode that starts and ends within the same second therefore
logs nothing.

- In one run, 14 of 31 episodes appeared in the log, and those 14 matched the
  edge times exactly.
- Short episodes are counted only when they happen to cross a second
  boundary.
- This is the design working as written, but it matters when reading activity
  counts from the field.

## Analysis

**Score by state, not by edges.** The first inactivity-time analysis searched
each pause for a falling edge. It reported 3-sample pauses of 1.5 s with "no
inactivity". In fact the tag had gone inactive at the last turnaround, before
the pause began, so there was no edge to find. `analyze_trials.py` now asks
what the tag's state was during the window.

**Match each trial to its own stimulus.** Look at the outliers trial by trial
before believing the summary table. Each anomaly this week (the 0.55 g miss,
the 0.42 g miss, the stalls) was explained by the trial or bout before it, or
by the voltage column.

## Practice

- **Keep run files in `runs/`, named by date and test.** `run_trial.py` writes
  every file for a configuration in one go: the configuration, the stand log,
  the SRAM2 dump, the decoded edges and the tag's own log.
- **Log the stand's own state on every row**: position, supply voltage and
  temperature. Each stall was diagnosed from that column after the fact.
- **State the interpretation of an ambiguous request in the result.** For
  example, "the thresholds" was taken to mean activity thresholds, with the
  inactivity threshold held at 0.15 g. The reader can then say if it was
  wrong.

## Open questions

- **Two 0.5 s activity episodes on 2026-10-28 while the servo was still.** An
  outside knock, or something in the detector? A still-only run would tell.
- **The inactivity threshold** has not been swept.
- **The pause that splits two bouts at 6 and 9 samples** is only resolved to
  about ±0.25 s. Finer pauses would sharpen it.
- **Power versus activity** (plan section 10) is still to run, on stock
  firmware at 2.5 V under the Joulescope.
