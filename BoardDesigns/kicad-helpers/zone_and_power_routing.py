#!/usr/bin/env python3
"""Report copper zone count and how the power nets are actually routed."""
from _common import load
p = load('pcb')
print('zone_count:', p['statistics']['zone_count'], ' zones list len:', len(p.get('zones', [])))
print('copper layers:', p['statistics']['copper_layer_names'])
for e in p.get('power_net_routing', []):
    print(f"{e['net']:6s} tracks={e['track_count']:3d} len={e['total_length_mm']:7.2f}mm "
          f"width {e['min_width_mm']}-{e['max_width_mm']}mm")
