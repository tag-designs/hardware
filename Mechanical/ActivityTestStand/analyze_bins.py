#!/usr/bin/env python3
"""Check a BitTag activity log, bin by bin, against the edge log.

The firmware (bt_state_run.c) adds one count per whole second from each wake
at which AWAKE was high to the next wake: seconds floor(t_k) .. floor(t_k+1)-1
for every pair of consecutive edge-log records with level 1.  So the edge log
predicts every bin of every format exactly.  This reads the tag's text
download (tag-dwnld -f text), whose lines are labelled with the *end* of their
bin -- per-second records as two 30-bit halves (SEC:0x...), the others as a
percentage of the bin (MIN:, FOURMIN:, FIVEMIN:) -- and compares.

  python3 analyze_bins.py runs/2026-10-29-bins-min
"""

import argparse
import csv
import math
import re
import sys
from collections import Counter

PERIOD = {"SEC": 1, "MIN": 60, "FOURMIN": 240, "FIVEMIN": 300}
FIELD_MAX = {"SEC": 1, "MIN": 63, "FOURMIN": 255, "FIVEMIN": 511}


def predicted_seconds(prefix):
    recs = [(float(r["unix"]), int(r["level"]))
            for r in csv.DictReader(open(f"{prefix}-edges.csv"))]
    secs = set()
    for (t0, l0), (t1, _) in zip(recs, recs[1:]):
        if l0:
            secs |= set(range(math.floor(t0), math.floor(t1)))
    return secs, recs[0][0], recs[-1][0]


def logged_bins(prefix):
    """{(kind, bin_end): count} from the text log."""
    bins = {}
    for line in open(f"{prefix}-log.txt"):
        m = re.match(r"(\d+),SEC:0x([0-9a-fA-F]+)", line)
        if m:
            end, v = int(m[1]), int(m[2], 16)
            for b in range(30):
                bins[("SEC", end - 30 + b + 1)] = (v >> b) & 1
            continue
        m = re.match(r"(\d+),(MIN|FOURMIN|FIVEMIN):([0-9.eE+-]+)", line)
        if m:
            kind = m[2]
            bins[(kind, int(m[1]))] = round(float(m[3]) * PERIOD[kind] / 100)
    return bins


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("prefix", help="runs/<name>, without the -edges.csv suffix")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every bin")
    a = ap.parse_args()

    secs, t_first, t_last = predicted_seconds(a.prefix)
    bins = logged_bins(a.prefix)
    if not bins:
        sys.exit("no data lines in the log")
    kind = next(iter(bins))[0]
    period = PERIOD[kind]

    pred = Counter()
    for s in secs:
        pred[(kind, (s // period + 1) * period)] += 1   # keyed by bin end, as the log

    # only bins the edge log fully covers
    lo, hi = t_first, t_last
    checked = sorted(k for k in bins if lo <= k[1] - period and k[1] <= hi)
    bad = [(k, bins[k], pred.get(k, 0)) for k in checked if bins[k] != pred.get(k, 0)]
    active = [k for k in checked if pred.get(k, 0)]
    full = [k for k in checked if pred.get(k, 0) == period]
    print(f"{kind}: {len(checked)} bins checked ({len(active)} with activity, "
          f"{len(full)} full, {len(checked) - len(active)} still); "
          f"{sum(bins[k] for k in checked)} active s logged, "
          f"{sum(pred.get(k, 0) for k in checked)} predicted; "
          f"{len(bad)} mismatched")
    over = [k for k in checked if bins[k] > FIELD_MAX[kind]]
    if over:
        print(f"  {len(over)} bins exceed the {FIELD_MAX[kind]}-count field")
    for (k, end), got, want in bad[:20]:
        print(f"  bin ending {end}: logged {got}, predicted {want}")
    if a.verbose:
        for k in checked:
            print(f"  {k[1]}: logged {bins[k]:3d} predicted {pred.get(k, 0):3d}")


if __name__ == "__main__":
    sys.exit(main())
