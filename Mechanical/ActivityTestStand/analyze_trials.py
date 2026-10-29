#!/usr/bin/env python3
"""Score a steps or gaps run: stand CSV against the tag's decoded edges.

steps -- per tilt angle, how often the tilt was detected (a rise between the
tilt command and the return), how often the tag then went inactive while held,
and how often the return was detected.  The change on the tilted axis is
sin(angle) g.  A return is only scored after a detected tilt: otherwise the
activity reference is still level and the return is no change to it.

gaps -- per pause, how often the tag was inactive at some point in it (already
inactive when the pause began, or a fall before 0.3 s after motion resumed --
a tag that dropped out at the last swing's turnaround has no fall in the
pause), the delay of any fall after motion stopped, and the delay of the fall
after the final stop.

nudge -- per nudge angle, when the tag went inactive: measured from the
moment it came to rest at level after the reset snap (still_start) and from
the end of the nudge (stop).  If the nudge restarted the inactivity countdown
the fall follows the stop by the full inactivity time; if not, it follows
still_start by it.

blip (--threshold G) -- per trial, how long the stand spent past the tilt at
which the change reaches G (asin G), from the logged positions, and whether a
rise followed; then detection rate against that time.

rock -- per rocking amplitude, the peak-to-peak change the stand actually
produced (sin of the extreme logged angles, from the second swing on), and whether the tag
went inactive while rocking: early (already inactive at the start, or a fall
in the first ROCK_SETTLE_S, while the countdown left from the snap can run
out before the first swing is under way) or during steady rocking.  The
steady count is the measure: rocking that holds the tag active has an
amplitude above the inactivity threshold.

  python3 analyze_trials.py runs/2026-10-29-act035
  python3 analyze_trials.py runs/2026-10-29-blip --threshold 0.35
"""

import argparse
import csv
import math
import statistics as st
import sys
from collections import defaultdict


def load(prefix):
    stand = list(csv.DictReader(open(f"{prefix}-stand.csv")))
    edges = list(csv.DictReader(open(f"{prefix}-edges.csv")))
    rises = [float(e["unix"]) for e in edges if e["edge"] == "rise"]
    falls = [float(e["unix"]) for e in edges if e["edge"] == "fall"]
    levels = [(float(e["unix"]), int(e["level"])) for e in edges]
    return stand, rises, falls, levels


def level_at(levels, t):
    """AWAKE level of the last record at or before t (None before the first)."""
    lv = None
    for tt, l in levels:
        if tt > t:
            break
        lv = l
    return lv


def trials(stand):
    """Split the stand log into trials: lists of rows, each starting at a 'trial' row."""
    out, cur = [], None
    for r in stand:
        if r["event"] == "trial":
            cur = [r]
            out.append(cur)
        elif cur is not None and r["event"] != "sample":
            cur.append(r)
    for i, t in enumerate(out):
        t_next = float(out[i + 1][0]["unix"]) if i + 1 < len(out) else math.inf
        t.append({"event": "next", "unix": str(t_next)})
    return out


def first(times, lo, hi):
    return next((t for t in times if lo <= t < hi), None)


def at(trial, event):
    return next(float(r["unix"]) for r in trial if r["event"] == event)


def fmt(v):
    return f"{v:.2f}" if v is not None else "-"


def steps(stand, rises, falls):
    rows = defaultdict(lambda: {"n": 0, "tilt": 0, "held_inactive": 0,
                                "ret": 0, "lat": []})
    for tr in trials(stand):
        angle = float(tr[0]["target"])
        t_tilt, t_ret, t_next = at(tr, "tilt"), at(tr, "return"), at(tr, "next")
        k = rows[angle]
        k["n"] += 1
        rise = first(rises, t_tilt, t_ret)
        if rise is None:
            continue
        k["tilt"] += 1
        k["lat"].append(rise - t_tilt)
        if first(falls, rise, t_ret) is not None:
            k["held_inactive"] += 1
            if first(rises, t_ret, t_next) is not None:
                k["ret"] += 1
    print("angle  delta_g  tilts_detected  inactive_while_held  returns_detected"
          "  rise_after_cmd_s")
    for angle in sorted(rows, key=abs):
        k = rows[angle]
        lat = f"{min(k['lat']):.2f}-{max(k['lat']):.2f}" if k["lat"] else "-"
        print(f"{angle:5.1f}  {math.sin(math.radians(abs(angle))):7.3f}  "
              f"{k['tilt']:>6}/{k['n']:<7}  {k['held_inactive']:>9}/{k['tilt']:<9}  "
              f"{k['ret']:>8}/{k['held_inactive']:<7}  {lat:>9}")


def gaps(stand, rises, falls, levels):
    rows = defaultdict(lambda: {"n": 0, "split": 0, "split_delay": [], "end_delay": []})
    for tr in trials(stand):
        gap = float(tr[0]["target"])
        s0, s1 = at(tr, "still_start"), at(tr, "still_end")
        stop, t_next = at(tr, "stop"), at(tr, "next")
        k = rows[gap]
        k["n"] += 1
        f = first(falls, s0, s1 + 0.3)
        if level_at(levels, s0) == 0 or f is not None:
            k["split"] += 1
        if f is not None:
            k["split_delay"].append(f - s0)
        f = first(falls, stop - 0.6, t_next)
        if f is not None:
            k["end_delay"].append(f - stop)
    print("pause_s  inactive_in_pause  fall_after_stop_s  final_fall_after_stop_s")
    for gap in sorted(rows):
        k = rows[gap]
        sd = (f"{min(k['split_delay']):.2f}-{max(k['split_delay']):.2f}"
              if k["split_delay"] else "-")
        ed = (f"{min(k['end_delay']):.2f}-{max(k['end_delay']):.2f}"
              if k["end_delay"] else "-")
        print(f"{gap:7.2f}  {k['split']:>6}/{k['n']:<6}  {sd:>18}  {ed:>22}")


def nudge(stand, rises, falls):
    rows = defaultdict(lambda: {"n": 0, "after_rest": [], "after_nudge": [], "none": 0})
    for tr in trials(stand):
        angle = float(tr[0]["target"])
        s0, stop, t_next = at(tr, "still_start"), at(tr, "stop"), at(tr, "next")
        k = rows[angle]
        k["n"] += 1
        f = first(falls, s0, t_next)
        if f is None:
            k["none"] += 1
            continue
        k["after_rest"].append(f - s0)
        k["after_nudge"].append(f - stop)
    print("nudge_deg  change_g  fall_after_rest_s  fall_after_nudge_end_s  no_fall")
    for angle in sorted(rows):
        k = rows[angle]
        rng = lambda v: f"{min(v):.2f}-{max(v):.2f}" if v else "-"
        print(f"{angle:9.1f}  {math.sin(math.radians(abs(angle))):8.3f}  "
              f"{rng(k['after_rest']):>17}  {rng(k['after_nudge']):>22}  "
              f"{k['none']:>4}/{k['n']}")


ROCK_SETTLE_S = 1.2   # level to +angle, then the first full swing begins


def rock(stand, falls, levels):
    rows = defaultdict(lambda: {"n": 0, "pp": [], "early": 0, "steady": 0,
                                "fall_after": []})
    for tr in trials(stand):
        angle = float(tr[0]["target"])
        r0, r1 = at(tr, "rock_start"), at(tr, "rock_end")
        # from the second swing: the first only goes from level to +angle
        w0 = [float(r["unix"]) for r in tr if r["event"] == "swing"][1]
        degs = [float(r["deg"]) for r in stand
                if r["deg"] and w0 <= float(r["unix"]) <= r1]
        sin = lambda d: math.sin(math.radians(d))
        k = rows[angle]
        k["n"] += 1
        k["pp"].append(sin(max(degs)) - sin(min(degs)))
        f = first(falls, r0, r1)
        if level_at(levels, r0) == 0 or (f is not None and f < r0 + ROCK_SETTLE_S):
            k["early"] += 1
        elif f is not None:
            k["steady"] += 1
        if f is not None:
            k["fall_after"].append(f - r0)
    print("rock_deg  nominal_pp_g  measured_pp_g  inactive_early  inactive_steady"
          "  fall_after_start_s")
    for angle in sorted(rows):
        k = rows[angle]
        fa = (f"{min(k['fall_after']):.2f}-{max(k['fall_after']):.2f}"
              if k["fall_after"] else "-")
        print(f"{angle:8.2f}  {2 * math.sin(math.radians(angle)):12.3f}  "
              f"{min(k['pp']):6.3f}-{max(k['pp']):.3f}  "
              f"{k['early']:>8}/{k['n']:<5}  {k['steady']:>9}/{k['n'] - k['early']:<5}"
              f"  {fa:>18}")


def blip(stand, rises, threshold):
    theta = math.degrees(math.asin(min(threshold, 1.0)))
    out = []
    for tr in trials(stand):
        t0, t_next = float(tr[0]["unix"]), at(tr, "next")
        pts = [(float(r["unix"]), abs(float(r["deg"]))) for r in stand
               if r["deg"] and t0 <= float(r["unix"]) < t_next]
        above = 0.0
        for (ta, da), (tb, db) in zip(pts, pts[1:]):
            if da >= theta and db >= theta:
                above += tb - ta
            elif da >= theta or db >= theta:      # interpolate the crossing
                frac = (max(da, db) - theta) / (abs(db - da) or 1)
                above += frac * (tb - ta)
        peak = max(d for _, d in pts)
        hit = first(rises, t0, t_next) is not None
        out.append((above, hit, peak))
    print(f"threshold {threshold} g = {theta:.1f} deg; {len(out)} trials")
    print("time_past_s  detected   (peak deg)")
    for above, hit, peak in sorted(out):
        print(f"{above:10.3f}  {'yes' if hit else 'no':>8}   ({peak:.1f})")
    edges = [0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 10]
    print("time_past_s     detected")
    for lo, hi in zip(edges, edges[1:]):
        sel = [h for a_, h, _ in out if lo <= a_ < hi]
        if sel:
            print(f"{lo:.2f}-{hi:.2f}  {sum(sel):>6}/{len(sel)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("prefix", help="runs/<name>, without the -stand.csv suffix")
    ap.add_argument("--threshold", type=float,
                    help="blip runs: the activity threshold in g")
    a = ap.parse_args()
    stand, rises, falls, levels = load(a.prefix)
    events = {r["event"] for r in stand}
    if "rock_start" in events:
        rock(stand, falls, levels)
    elif "nudge" in events:
        nudge(stand, rises, falls)
    elif a.threshold is not None:
        blip(stand, rises, a.threshold)
    elif "still_start" in events:
        gaps(stand, rises, falls, levels)
    else:
        steps(stand, rises, falls)


if __name__ == "__main__":
    sys.exit(main())
