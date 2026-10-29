#!/usr/bin/env python3
"""Score a pareto run: the tag's 1 s activity log against the stand's bouts.

Each bout runs from its bout_start row to its bout_end row (the return to
level is commanded there and takes move_ms).  A logged second counts toward a
bout if it lies between floor(bout_start) and the bout_end second + 1, which
covers detection latency, the return and the one-sample tail.  Reports the
active fraction the tag logged over the run, active seconds per bout length,
bouts that left no logged second (sub-second episodes do not register in 1 s
bins), and logged seconds outside every bout.  Only the span the download
covers is scored: it ends at the last complete record.

  python3 analyze_pareto.py runs/2026-10-29-p4-pareto
"""

import argparse
import csv
import math
import sys
from collections import defaultdict

from analyze_bins import logged_bins


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("prefix", help="runs/<name>, without the -stand.csv suffix")
    a = ap.parse_args()

    stand = list(csv.DictReader(open(f"{a.prefix}-stand.csv")))
    t_lo = math.ceil(float(stand[1]["unix"]))     # the start_at row
    t_hi = math.floor(float(stand[-1]["unix"]))
    bouts, cur = [], None
    for r in stand:
        if r["event"] == "bout_start":
            cur = (float(r["unix"]), int(r["target"]))
        elif r["event"] == "bout_end" and cur:
            bouts.append((cur[0], float(r["unix"]), cur[1]))
            cur = None

    bins = {k[1]: v for k, v in logged_bins(a.prefix).items() if k[0] == "SEC"}
    # the download ends at the last whole record; score only what it covers
    t_hi = min(t_hi, max(bins))
    bouts = [b for b in bouts if math.floor(b[1]) + 2 <= t_hi]
    # the log labels a second s as s + 1 (bin end)
    active = {end - 1 for end, v in bins.items() if v and t_lo <= end - 1 < t_hi}
    span = t_hi - t_lo
    covered = set()
    per_len = defaultdict(lambda: [0, 0, 0])   # n, logged seconds, bouts with none
    for b0, b1, n in bouts:
        secs = {s for s in range(math.floor(b0), math.floor(b1) + 2) if s in active}
        covered |= secs
        k = per_len[n]
        k[0] += 1
        k[1] += len(secs)
        k[2] += not secs
    stray = sorted(active - covered)
    sched = sum(b1 - b0 for b0, b1, _ in bouts)
    print(f"{len(bouts)} bouts over {span} s; swinging {sched:.0f} s ({sched / span:.1%}); "
          f"tag logged {len(active)} active s ({len(active) / span:.1%})")
    print("bout_s  bouts  logged_s_per_bout  bouts_with_none")
    for n in sorted(per_len):
        k = per_len[n]
        print(f"{n:6d}  {k[0]:5d}  {k[1] / k[0]:17.2f}  {k[2]:>9}/{k[0]}")
    print(f"logged active seconds outside every bout: {len(stray)}"
          + (f" (first {stray[:5]})" if stray else ""))


if __name__ == "__main__":
    sys.exit(main())
