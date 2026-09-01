#!/usr/bin/env python3
"""Test point and fiducial coverage."""
from _common import load
p, s = load('pcb'), load('schematic')
for f in p['findings']:
    if f['rule_id'] in ('TE-001','FD-001'):
        print(f"[{f['severity']:8s}] {f['rule_id']} {f['summary']}")
tc = s.get('test_coverage', {})
print('test points:', tc.get('test_point_count'), ' debug connectors:',
      [d['ref'] + '/' + d['interface'] for d in tc.get('debug_connectors', [])])
