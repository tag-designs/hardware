#!/usr/bin/env python3
"""Trace the VBAT/VIN power path and identify the battery footprint."""
from _common import load
s = load('schematic')
for n in ('VBAT','VIN'):
    pins = s['nets'][n]['pins']
    print(f"{n}: " + ', '.join(f"{p['component']}.{p['pin_number']}({p['pin_name']})" for p in pins if not p['component'].startswith('#')))
for c in s['components']:
    if c['reference'] in ('J401','J201','D401'):
        print(f"{c['reference']:6s} {c['value']:14s} footprint={c.get('footprint')}")
