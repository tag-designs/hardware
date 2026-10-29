#!/usr/bin/env python3
"""Run a timed motion profile on the activity test stand and log it.

For power runs and activity-detection runs, where the tag runs detached and
is only read back afterwards: the stand supplies a known, logged stimulus, and
the CSV is the ground truth to line up with the Joulescope trace and the tag's
BITPERSEC download.  Times are host UTC; set the tag's clock from the same
host (tag-reset --set-rtc) so the two agree to about a second.

Profiles (angles in degrees from true level, + or -; LEVEL_DEG below):
  still    hold level for the whole run
  pulses   every PERIOD s: tilt to ANGLE over MOVE_MS, hold HOLD s, return
  agitate  swing continuously between +ANGLE and -ANGLE, MOVE_MS per swing
  bouts    every PERIOD s: agitate for the next duration in BOUTS (cycled),
           then hold level -- distinct, known amounts of activity per bin
  steps    for each angle in ANGLES, REPS times: tilt over MOVE_MS, hold HOLD
           s, return, rest REST s -- brackets an activity threshold
  gaps     for each pause in GAPS, REPS times: agitate BOUT s, hold level for
           the pause, agitate BOUT s, rest REST s -- brackets an inactivity time
  nudge    for each angle in ANGLES, REPS times: snap to RESET_ANGLE and back
           (activity), wait DELAY s still, nudge to the angle and back over
           MOVE_MS each way (holding HOLD s there), rest REST s -- does a
           small move restart the inactivity countdown?
  blip     for each angle in ANGLES, REPS times: out to the angle and straight
           back, MOVE_MS each way, no hold, rest REST s -- short stimuli;
           use a small --poll to time the excursion

steps, gaps, nudge and blip run every trial once per rep (--shuffle permutes
each rep) and take no --minutes.  Each trial starts on a whole second with a "trial" row
naming its angle or pause; gaps logs "still_start"/"still_end" around the
pause and "stop" when the last return to level ends.

Stimuli start on whole host seconds, so each lands in a known BITPERSEC bit.
--start-on-minute delays the first one to the next whole minute, and
--offset shifts every stimulus by a fraction of a second, to place a short
episode within one second or across a second boundary.

  python3 stand_profile.py pulses --period 60 --angle 30 --hold 2 --minutes 20 -o run.csv
  python3 stand_profile.py agitate --angle 30 --move-ms 600 --minutes 20 -o run.csv
  python3 stand_profile.py still --minutes 20 --unload -o run.csv
  python3 stand_profile.py bouts --period 60 --bouts 2,5,10,20,40 --offset 0.5 --minutes 20 -o run.csv
  python3 stand_profile.py steps --angles 16.3,18.4,19.4,21.6,22.6,24.8 --reps 3 --move-ms 1500 -o run.csv
  python3 stand_profile.py gaps --gaps 0.25,0.5,1,1.5,2 --reps 3 --bout 2 -o run.csv
"""

import argparse
import math
import random
import csv
import datetime
import sys
import time

from lx16a import CENTER, DEG_PER_COUNT, DEFAULT_PORT, LX16A


def utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(
        timespec="milliseconds")


# True level, against gravity, in servo degrees from CENTER. Fitted on
# 2026-10-29 from the BitTag's own X/Z samples held at -90..+90 deg
# (runs/2026-10-29-gravity-*): 3.2 deg, 13 counts. Runs before then used
# CENTER as level; the difference changes a tilt's effect by under 1%.
LEVEL_DEG = 3.2


def counts(deg):
    """Servo position for an angle in degrees from true level."""
    return round(CENTER + (deg + LEVEL_DEG) / DEG_PER_COUNT)


# LX-16A rating; outside it the run continues but is flagged.
VIN_MIN, VIN_MAX = 6.0, 8.4
TEMP_WARN = 70


class Run:
    """Servo plus CSV log; every command and position sample is timestamped.

    Each row also carries the servo's supply voltage and temperature, since the
    stand runs from an unregulated adapter; extremes are reported at the end.
    """

    def __init__(self, servo, out, poll):
        self.s = servo
        self.poll = poll
        self.w = csv.writer(out)
        self.w.writerow(["utc", "unix", "event", "target", "pos", "deg",
                         "vin", "temp"])
        self.stimuli = 0
        self.resends = 0
        self.restarts = 0
        self.last_pos = None
        self.vin_lo = self.vin_hi = None
        self.temp_hi = None
        self.warned = set()

    def log(self, event, target=""):
        p = self.s.pos()
        t = time.time()
        v = self.s.vin()
        c = self.s.temp()
        self.w.writerow([utc(t), f"{t:.3f}", event, target, p,
                         f"{(p - CENTER) * DEG_PER_COUNT - LEVEL_DEG:.2f}", f"{v:.3f}", c])
        self.vin_lo = v if self.vin_lo is None else min(self.vin_lo, v)
        self.vin_hi = v if self.vin_hi is None else max(self.vin_hi, v)
        self.temp_hi = c if self.temp_hi is None else max(self.temp_hi, c)
        self.check("vin_high", v > VIN_MAX, f"servo supply {v:.2f} V above {VIN_MAX} V")
        self.check("vin_low", v < VIN_MIN, f"servo supply {v:.2f} V below {VIN_MIN} V")
        self.check("temp", c >= TEMP_WARN, f"servo at {c} C")
        self.last_pos = p
        return p

    def check(self, key, bad, msg):
        if bad and key not in self.warned:
            self.warned.add(key)
            print(f"WARNING {utc(time.time())}: {msg} (first occurrence)",
                  file=sys.stderr, flush=True)

    def summary(self):
        flags = f"; out of range: {', '.join(sorted(self.warned))}" if self.warned else ""
        return (f"servo supply {self.vin_lo:.2f}-{self.vin_hi:.2f} V, "
                f"max {self.temp_hi} C, {self.resends} dropped moves resent, "
                f"{self.restarts} stalled swings restarted{flags}")

    def move(self, deg, ms, event):
        """Command a move and log it; returns the position when commanded."""
        sends = self.s.move_checked(counts(deg), ms)
        p = self.log(event, counts(deg))
        if sends > 1:
            self.resends += sends - 1
            self.log("resend", sends - 1)
        return p

    def wait_until(self, t_end):
        """Sample position every poll interval until t_end (unix time)."""
        while True:
            now = time.time()
            if now >= t_end:
                return
            time.sleep(min(self.poll, t_end - now))
            self.log("sample")


STALL_CHECK_S = 0.2   # s after a swing command to confirm the servo is moving
STALL_COUNTS = 5      # less movement than this by then is a stall


def swing(r, a, t, t_end):
    """Swing between +angle and -angle, one move per move_ms, until t_end.

    A move that reaches the servo just as the previous one completes is
    sometimes stored but not started -- move_target() reads back correct while
    the horn sits still for a whole swing (3 of 15 bouts on 2026-10-27), which
    the tag rightly reports as inactivity.  So each swing is checked for
    motion and resent over its remaining time if it has not begun.
    """
    side = 1
    while t < t_end:
        target = counts(side * a.angle)
        p0 = r.move(side * a.angle, a.move_ms, "swing")
        if a.profile == "agitate":
            r.stimuli += 1
        t_check = min(t + STALL_CHECK_S, t_end)
        r.wait_until(t_check)
        # progress toward the target; finishing the previous move does not count
        way = 1 if target > p0 else -1
        far = abs(target - p0) > 2 * STALL_COUNTS
        if far and (r.last_pos - p0) * way < STALL_COUNTS and \
                t_check < t + a.move_ms / 1000:
            left = round((t + a.move_ms / 1000 - time.time()) * 1000)
            r.move(side * a.angle, max(left, 100), "restart")
            r.restarts += 1
        t += a.move_ms / 1000
        r.wait_until(min(t, t_end))
        side = -side


def next_second(t):
    return float(int(t) + 1)


def trial_order(values, reps, seed):
    """values once per rep, each rep permuted when seed is given."""
    rng = random.Random(seed)
    order = []
    for _ in range(reps):
        rep = list(values)
        if seed is not None:
            rng.shuffle(rep)
        order += rep
    return order


def floats(text):
    return [float(v) for v in text.split(",")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("profile",
                    choices=["still", "pulses", "agitate", "bouts", "steps", "gaps",
                             "nudge", "blip", "rock"])
    ap.add_argument("--minutes", type=float,
                    help="run length; not used by steps and gaps")
    ap.add_argument("--angle", type=float, default=30.0)
    ap.add_argument("--period", type=float, default=60.0, help="pulses: s between starts")
    ap.add_argument("--hold", type=float, default=2.0,
                    help="pulses, steps, nudge: s held at the angle")
    ap.add_argument("--bouts", default="2,5,10,20,40",
                    help="bouts: comma-separated agitation durations in s, cycled")
    ap.add_argument("--angles", type=floats, help="steps: comma-separated tilts in degrees")
    ap.add_argument("--gaps", type=floats, help="gaps: comma-separated pauses in s")
    ap.add_argument("--reps", type=int, default=3, help="steps, gaps: repetitions")
    ap.add_argument("--rest", type=float, default=4.0,
                    help="steps, gaps: s still at level after each trial")
    ap.add_argument("--bout", type=float, default=2.0, help="gaps: s of agitation per bout; rock: s of rocking")
    ap.add_argument("--delay", type=float, default=0.3,
                    help="nudge: s still at level before the nudge")
    ap.add_argument("--shuffle", type=int, metavar="SEED",
                    help="steps, gaps: permute the trials of each rep")
    ap.add_argument("--move-ms", type=int, default=600, help="duration of each move")
    ap.add_argument("--reset-angle", type=float,
                    help="steps: before each trial, snap to this angle and straight "
                    "back to level (400 ms each way), then rest. Pick it well above "
                    "the activity threshold: the tag then goes inactive at level, "
                    "latching a level reference whatever the previous trial left")
    ap.add_argument("--return-ms", type=int,
                    help="steps: duration of the return to level (default --move-ms). "
                    "Keep it under the inactivity time, so the tag cannot declare "
                    "inactivity mid-return and latch an off-level reference")
    ap.add_argument("--poll", type=float, default=0.1, help="s between position samples")
    ap.add_argument("--unload", action="store_true",
                    help="torque off while level and still (removes hold jitter)")
    ap.add_argument("--start-on-minute", action="store_true")
    ap.add_argument("--align", type=int, metavar="S",
                    help="start the first stimulus 5 s before the next multiple of S "
                    "Unix seconds; with a first bout longer than S, one whole bin "
                    "of S seconds is active")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="s added to each stimulus start, 0 <= offset < 1")
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    trials = a.profile in ("steps", "gaps", "nudge", "blip", "rock")
    if not trials and a.minutes is None:
        ap.error(f"{a.profile} needs --minutes")
    if a.profile in ("steps", "nudge", "blip", "rock") and not a.angles:
        ap.error(f"{a.profile} needs --angles")
    if a.profile in ("nudge", "rock") and not a.reset_angle:
        ap.error(f"{a.profile} needs --reset-angle")
    if a.profile == "gaps" and not a.gaps:
        ap.error("gaps needs --gaps")

    with LX16A(a.port) as s, open(a.output, "w", newline="") as f:
        r = Run(s, f, a.poll)
        s.load()
        s.move(counts(0.0), 1000)
        s.wait_until_stopped(min_s=1.0)
        r.log("level")

        t0 = time.time()
        if a.align:
            t0 = math.ceil((t0 + 6.0) / a.align) * a.align - 5.0
        elif a.start_on_minute:
            t0 = (int(t0) // 60 + 1) * 60.0
        else:
            t0 = next_second(t0 + 1.0)
        t_end = t0 + (a.minutes * 60.0 if not trials else 0.0)
        t0 += a.offset
        r.log("start_at", utc(t0))
        if a.unload:
            s.unload()
        r.wait_until(t0)

        try:
            if a.profile == "still":
                r.wait_until(t_end)

            elif a.profile == "pulses":
                k = 0
                while t0 + k * a.period < t_end:
                    t = t0 + k * a.period
                    r.wait_until(t)
                    if a.unload:
                        s.load()
                    r.move(a.angle, a.move_ms, "tilt")
                    r.stimuli += 1
                    r.wait_until(t + a.move_ms / 1000 + a.hold)
                    r.move(0.0, a.move_ms, "return")
                    r.wait_until(time.time() + a.move_ms / 1000 + 0.5)
                    if a.unload:
                        s.unload()
                        r.log("unload")
                    k += 1
                r.wait_until(t_end)

            elif a.profile == "bouts":
                bouts = [float(b) for b in a.bouts.split(",")]
                k = 0
                t = t0
                while t < t_end:
                    r.wait_until(t)
                    if a.unload:
                        s.load()
                    r.log("bout_start", bouts[k % len(bouts)])
                    swing(r, a, t, t + bouts[k % len(bouts)])
                    r.move(0.0, a.move_ms, "bout_end")
                    r.stimuli += 1
                    r.wait_until(time.time() + a.move_ms / 1000 + 0.5)
                    if a.unload:
                        s.unload()
                        r.log("unload")
                    k += 1
                    # a bout longer than the period pushes the next one back,
                    # keeping the offset within the second
                    t_min = time.time() + 5.0
                    t = t0 + k * a.period
                    if t < t_min:
                        t += math.ceil(t_min - t)
                r.wait_until(t_end)

            elif a.profile == "nudge":
                for angle in trial_order(a.angles, a.reps, a.shuffle):
                    t = next_second(time.time())
                    r.wait_until(t)
                    r.log("trial", angle)
                    r.move(a.reset_angle, 400, "reset")
                    r.wait_until(time.time() + 0.4)
                    r.move(0.0, 400, "reset_return")
                    r.wait_until(time.time() + 0.4)
                    r.log("still_start")
                    r.wait_until(time.time() + a.delay)
                    r.move(angle, a.move_ms, "nudge")
                    r.wait_until(time.time() + a.move_ms / 1000 + a.hold)
                    r.move(0.0, a.move_ms, "nudge_return")
                    r.wait_until(time.time() + a.move_ms / 1000)
                    r.log("stop")
                    r.stimuli += 1
                    r.wait_until(time.time() + a.rest)
                t_end = time.time()

            elif a.profile == "rock":
                # wake the tag with a snap, then rock +/-angle for --bout s:
                # does the rocking keep it active?
                for angle in trial_order(a.angles, a.reps, a.shuffle):
                    t = next_second(time.time())
                    r.wait_until(t)
                    r.log("trial", angle)
                    r.move(a.reset_angle, 400, "reset")
                    r.wait_until(time.time() + 0.4)
                    r.move(0.0, 400, "reset_return")
                    r.wait_until(time.time() + 0.4)
                    # the return can lag; rock from level, not on the way down
                    t = time.time() + 1.0
                    while abs(r.last_pos - counts(0.0)) > 3 and time.time() < t:
                        r.wait_until(time.time() + r.poll)
                    r.log("rock_start")
                    a.angle = angle
                    t = time.time()
                    swing(r, a, t, t + a.bout)
                    r.log("rock_end")
                    r.move(0.0, a.move_ms, "stop")
                    r.stimuli += 1
                    r.wait_until(time.time() + a.move_ms / 1000 + a.rest)
                t_end = time.time()

            elif a.profile == "blip":
                for angle in trial_order(a.angles, a.reps, a.shuffle):
                    t = next_second(time.time())
                    r.wait_until(t)
                    r.log("trial", angle)
                    r.move(angle, a.move_ms, "tilt")
                    r.wait_until(time.time() + a.move_ms / 1000)
                    r.move(0.0, a.move_ms, "return")
                    r.stimuli += 1
                    r.wait_until(time.time() + a.move_ms / 1000 + a.rest)
                t_end = time.time()

            elif a.profile == "steps":
                for angle in trial_order(a.angles, a.reps, a.shuffle):
                    if a.reset_angle:
                        r.move(a.reset_angle, 400, "reset")
                        r.wait_until(time.time() + 0.4)
                        r.move(0.0, 400, "reset_return")
                        r.wait_until(time.time() + 0.4 + a.rest)
                    t = next_second(time.time())
                    r.wait_until(t)
                    r.log("trial", angle)
                    r.move(angle, a.move_ms, "tilt")
                    r.stimuli += 1
                    r.wait_until(t + a.move_ms / 1000 + a.hold)
                    ret_ms = a.return_ms or a.move_ms
                    r.move(0.0, ret_ms, "return")
                    r.wait_until(time.time() + ret_ms / 1000 + a.rest)
                t_end = time.time()

            elif a.profile == "gaps":
                for gap in trial_order(a.gaps, a.reps, a.shuffle):
                    t = next_second(time.time())
                    r.wait_until(t)
                    r.log("trial", gap)
                    swing(r, a, t, t + a.bout)
                    r.move(0.0, a.move_ms, "pause")
                    t = time.time() + a.move_ms / 1000
                    r.wait_until(t)
                    r.log("still_start", gap)
                    r.wait_until(t + gap)
                    r.log("still_end", gap)
                    t = time.time()
                    swing(r, a, t, t + a.bout)
                    r.move(0.0, a.move_ms, "trial_end")
                    r.wait_until(time.time() + a.move_ms / 1000)
                    r.log("stop")
                    r.stimuli += 1
                    r.wait_until(time.time() + a.rest)
                t_end = time.time()

            else:  # agitate
                swing(r, a, t0, t_end)
        except KeyboardInterrupt:
            r.log("interrupted")
        finally:
            s.load()
            s.move(counts(0.0), 1000)
            s.wait_until_stopped(min_s=1.0)
            r.log("end")
            if a.unload:
                s.unload()

    print(f"{a.profile}: {r.stimuli} stimuli from {utc(t0)} to {utc(t_end)}; "
          f"log in {a.output}", file=sys.stderr)
    print(r.summary(), file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
