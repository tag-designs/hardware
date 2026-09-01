#!/usr/bin/env python3
"""Component-to-board-edge clearances flagged by the PCB analyzer (PM-002)."""
from _common import load
p = load('pcb')
for f in p['findings']:
    if f['rule_id'] == 'PM-002':
        print(f"[{f['severity']:8s}] {f['summary']}")
print('board:', p['statistics']['board_width_mm'], 'x', p['statistics']['board_height_mm'], 'mm')
