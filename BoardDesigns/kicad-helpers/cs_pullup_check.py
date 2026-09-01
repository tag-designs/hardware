#!/usr/bin/env python3
"""Check whether chip-select and I2C nets have any resistor on them."""
from _common import load
s = load('schematic')
res = {c['reference'] for c in s['components'] if c['type'] == 'resistor'}
print('resistors on board:', sorted(res) or 'NONE')
for n in ('AT25_nCS','ACCEL_CS','SCL','SDA'):
    pins = s['nets'][n]['pins']
    r = [p['component'] for p in pins if p['component'] in res]
    print(f"{n:10s} {len(pins)} pins: " + ', '.join(f"{p['component']}.{p['pin_number']}" for p in pins)
          + f"  -> resistor: {r or 'NONE'}")
