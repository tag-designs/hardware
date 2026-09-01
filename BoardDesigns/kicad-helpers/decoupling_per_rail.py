#!/usr/bin/env python3
"""Nearest VIN-rail bypass cap to each IC, split by cap value class."""
import json, glob, sys
p = json.load(open(sorted(glob.glob('analysis/*/pcb.json'))[-1]))
for e in p.get('decoupling_placement', []):
    vin = [c for c in e['nearby_caps'] if 'VIN' in c['shared_nets'] and 'GND' in c['shared_nets']]
    small = [c for c in vin if c['value'].rstrip('uf') in ('0.1', '0.22')]
    bulk = [c for c in vin if c['value'].rstrip('uf') in ('22', '47')]
    print(f"{e['ic']:6s} {str(e['value'])[:16]:18s} "
          f"nearest 100n={small[0]['cap']+'@'+format(small[0]['distance_mm'],'.2f') if small else 'NONE':>14s}  "
          f"nearest bulk={bulk[0]['cap']+'@'+format(bulk[0]['distance_mm'],'.2f') if bulk else 'NONE':>14s}  "
          f"(VIN caps within 5mm: {len([c for c in vin if c['distance_mm']<5])})")
