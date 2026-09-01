#!/usr/bin/env python3
"""Via annular ring vs IPC-6012 Class 2 minimum (0.125 mm), and min track width."""
from _common import load
p = load('pcb')
ar = p['vias']['via_analysis']['annular_ring']
print('via size/drill distribution:', p['vias']['size_distribution'])
print('annular ring min/max mm:', ar['min_mm'], ar['max_mm'])
print('vias below IPC Class 2 (0.125 mm):', ar['below_0.125mm'], 'of', p['vias']['count'])
tw = sorted({w for e in p.get('power_net_routing', []) for w in e['widths_used']})
print('track widths in use (mm):', tw)
