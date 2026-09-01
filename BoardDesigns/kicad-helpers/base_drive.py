#!/usr/bin/env python3
"""Q501 base drive with no series resistor, and the base current actually needed.

Driver: 3.3 V push-pull debug adapter, output impedance 25-50 ohm.
Q501 VBE clamps near 0.8 V, so Ib = (3.3 - 0.8) / Rout.
Needed: Q501 need only sink the STM32 NRST internal pull-up (30-50 kOhm).
"""
from _common import load
s = load('schematic')
print('RST net pins:', [f"{p['component']}.{p['pin_number']}({p['pin_name']})" for p in s['nets']['RST']['pins']])
print('resistors on board:', sorted(c['reference'] for c in s['components'] if c['type'] == 'resistor'))
for rout in (25, 50):
    print(f'  Rout={rout:3d} ohm -> Ib = (3.3-0.8)/{rout} = {2.5/rout*1000:6.1f} mA   (BC847AMB IBM max 100 mA, tp<=1ms)')
for rpu in (30e3, 50e3):
    print(f'  NRST pull-up {rpu/1000:.0f}k -> Ic needed = 3.3/{rpu/1000:.0f}k = {3.3/rpu*1e6:5.1f} uA'
          f' -> Ib needed at hFE 110 = {3.3/rpu/110*1e9:5.1f} nA')
print('  With a 10k base resistor: Ib = (3.3-0.8)/10k = 250 uA -> margin over requirement > 1000x')
