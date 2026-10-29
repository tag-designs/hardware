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

  python3 analyze_trials.py runs/2026-10-29-act035
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("prefix", help="runs/<name>, without the -stand.csv suffix")
    a = ap.parse_args()
    stand, rises, falls, levels = load(a.prefix)
    if any(r["event"] == "still_start" for r in stand):
        gaps(stand, rises, falls, levels)
    else:
        steps(stand, rises, falls)


if __name__ == "__main__":
    sys.exit(main())
