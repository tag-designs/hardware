#!/usr/bin/env python3
"""Pool the 2026-10-29 inactivity-threshold passes: steady-rocking falls by
measured amplitude / threshold.  Run from Mechanical/ActivityTestStand."""
import sys, math
sys.path.insert(0, '.')
from analyze_trials import load, trials, at, first, level_at, ROCK_SETTLE_S
from collections import defaultdict
bins = [0, 0.7, 0.9, 1.0, 1.1, 1.2, 1.35, 1.6, 9]
tab = defaultdict(lambda: [0, 0, 0])   # (T, bin) -> steady trials, fell, early
for T in ("010", "020", "030", "050"):
    for sfx in ("", "-amp", "-neg"):
        stand, rises, falls, levels = load(f"runs/2026-10-29-inthr{T}{sfx}")
        Tg = int(T) / 100
        for tr in trials(stand):
            r0, r1 = at(tr, "rock_start"), at(tr, "rock_end")
            w0 = [float(r["unix"]) for r in tr if r["event"] == "swing"][1]
            d = [float(r["deg"]) for r in stand if r["deg"] and w0 <= float(r["unix"]) <= r1]
            amp = (math.sin(math.radians(max(d))) - math.sin(math.radians(min(d)))) / 2
            b = next(i for i in range(len(bins) - 1) if amp / Tg < bins[i + 1])
            f = first(falls, r0, r1)
            k = tab[(Tg, b)]
            if level_at(levels, r0) == 0 or (f is not None and f < r0 + ROCK_SETTLE_S):
                k[2] += 1
            else:
                k[0] += 1; k[1] += f is not None
hdr = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
print("amp/T   " + "".join(f"{h:>10}" for h in hdr))
for Tg in (0.1, 0.2, 0.3, 0.5):
    print(f"T={Tg:<4}  " + "".join(f"{(f'{tab[(Tg,b)][1]}/{tab[(Tg,b)][0]}' if tab[(Tg,b)][0] else '-'):>10}" for b in range(len(hdr))))
tot = [sum(tab[(Tg, b)][0] for Tg in (0.1,0.2,0.3,0.5)) for b in range(len(hdr))]
fell = [sum(tab[(Tg, b)][1] for Tg in (0.1,0.2,0.3,0.5)) for b in range(len(hdr))]
print("all     " + "".join(f"{f'{f}/{t}':>10}" for f, t in zip(fell, tot)))
print("early falls excluded:", sum(v[2] for v in tab.values()), "of", sum(v[0]+v[2] for v in tab.values()))
