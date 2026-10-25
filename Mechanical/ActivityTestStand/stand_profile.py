#!/usr/bin/env python3
"""Run a timed motion profile on the activity test stand and log it.

For power runs and activity-detection runs, where the tag runs detached and
is only read back afterwards: the stand supplies a known, logged stimulus, and
the CSV is the ground truth to line up with the Joulescope trace and the tag's
BITPERSEC download.  Times are host UTC; set the tag's clock from the same
host (tag-reset --set-rtc) so the two agree to about a second.

Profiles (angles in degrees from level, + or -):
  still    hold level for the whole run
  pulses   every PERIOD s: tilt to ANGLE over MOVE_MS, hold HOLD s, return
  agitate  swing continuously between +ANGLE and -ANGLE, MOVE_MS per swing
  bouts    every PERIOD s: agitate for the next duration in BOUTS (cycled),
           then hold level -- distinct, known amounts of activity per bin

Stimuli start on whole host seconds, so each lands in a known BITPERSEC bit.
--start-on-minute delays the first one to the next whole minute, and
--offset shifts every stimulus by a fraction of a second, to place a short
episode within one second or across a second boundary.

  python3 stand_profile.py pulses --period 60 --angle 30 --hold 2 --minutes 20 -o run.csv
  python3 stand_profile.py agitate --angle 30 --move-ms 600 --minutes 20 -o run.csv
  python3 stand_profile.py still --minutes 20 --unload -o run.csv
  python3 stand_profile.py bouts --period 60 --bouts 2,5,10,20,40 --offset 0.5 --minutes 20 -o run.csv
"""

import argparse
import csv
import datetime
import sys
import time

from lx16a import CENTER, DEG_PER_COUNT, DEFAULT_PORT, LX16A


def utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(
        timespec="milliseconds")


def counts(deg):
    return round(CENTER + deg / DEG_PER_COUNT)


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
        self.vin_lo = self.vin_hi = None
        self.temp_hi = None
        self.warned = set()

    def log(self, event, target=""):
        p = self.s.pos()
        t = time.time()
        v = self.s.vin()
        c = self.s.temp()
        self.w.writerow([utc(t), f"{t:.3f}", event, target, p,
                         f"{(p - CENTER) * DEG_PER_COUNT:.2f}", f"{v:.3f}", c])
        self.vin_lo = v if self.vin_lo is None else min(self.vin_lo, v)
        self.vin_hi = v if self.vin_hi is None else max(self.vin_hi, v)
        self.temp_hi = c if self.temp_hi is None else max(self.temp_hi, c)
        self.check("vin_high", v > VIN_MAX, f"servo supply {v:.2f} V above {VIN_MAX} V")
        self.check("vin_low", v < VIN_MIN, f"servo supply {v:.2f} V below {VIN_MIN} V")
        self.check("temp", c >= TEMP_WARN, f"servo at {c} C")
        return p

    def check(self, key, bad, msg):
        if bad and key not in self.warned:
            self.warned.add(key)
            print(f"WARNING {utc(time.time())}: {msg} (first occurrence)",
                  file=sys.stderr, flush=True)

    def summary(self):
        flags = f"; out of range: {', '.join(sorted(self.warned))}" if self.warned else ""
        return (f"servo supply {self.vin_lo:.2f}-{self.vin_hi:.2f} V, "
                f"max {self.temp_hi} C{flags}")

    def move(self, deg, ms, event):
        self.s.move(counts(deg), ms)
        self.log(event, counts(deg))

    def wait_until(self, t_end):
        """Sample position every poll interval until t_end (unix time)."""
        while True:
            now = time.time()
            if now >= t_end:
                return
            time.sleep(min(self.poll, t_end - now))
            self.log("sample")


def swing(r, a, t, t_end):
    """Swing between +angle and -angle, one move per move_ms, until t_end."""
    side = 1
    while t < t_end:
        r.move(side * a.angle, a.move_ms, "swing")
        if a.profile == "agitate":
            r.stimuli += 1
        t += a.move_ms / 1000
        r.wait_until(min(t, t_end))
        side = -side


def next_second(t):
    return float(int(t) + 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("profile", choices=["still", "pulses", "agitate", "bouts"])
    ap.add_argument("--minutes", type=float, required=True)
    ap.add_argument("--angle", type=float, default=30.0)
    ap.add_argument("--period", type=float, default=60.0, help="pulses: s between starts")
    ap.add_argument("--hold", type=float, default=2.0, help="pulses: s held tilted")
    ap.add_argument("--bouts", default="2,5,10,20,40",
                    help="bouts: comma-separated agitation durations in s, cycled")
    ap.add_argument("--move-ms", type=int, default=600, help="duration of each move")
    ap.add_argument("--poll", type=float, default=0.1, help="s between position samples")
    ap.add_argument("--unload", action="store_true",
                    help="torque off while level and still (removes hold jitter)")
    ap.add_argument("--start-on-minute", action="store_true")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="s added to each stimulus start, 0 <= offset < 1")
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()

    with LX16A(a.port) as s, open(a.output, "w", newline="") as f:
        r = Run(s, f, a.poll)
        s.load()
        s.move(CENTER, 1000)
        s.wait_until_stopped(min_s=1.0)
        r.log("level")

        t0 = time.time()
        if a.start_on_minute:
            t0 = (int(t0) // 60 + 1) * 60.0
        else:
            t0 = next_second(t0 + 1.0)
        t_end = t0 + a.minutes * 60.0
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
                while t0 + k * a.period < t_end:
                    t = t0 + k * a.period
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
                r.wait_until(t_end)

            else:  # agitate
                swing(r, a, t0, t_end)
        except KeyboardInterrupt:
            r.log("interrupted")
        finally:
            s.load()
            s.move(CENTER, 1000)
            s.wait_until_stopped(min_s=1.0)
            r.log("end")
            if a.unload:
                s.unload()

    print(f"{a.profile}: {r.stimuli} stimuli from {utc(t0)} to {utc(t_end)}; "
          f"log in {a.output}", file=sys.stderr)
    print(r.summary(), file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
