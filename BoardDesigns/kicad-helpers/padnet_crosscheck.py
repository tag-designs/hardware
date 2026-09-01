#!/usr/bin/env python3
"""Cross-check every schematic pin->net against the PCB pad->net. Prints mismatch count."""
from _common import load
s, p = load('schematic'), load('pcb')
sch = {}
for net, n in s['nets'].items():
    for pin in n.get('pins', []):
        sch.setdefault(pin['component'], {})[str(pin['pin_number'])] = net
bad = 0
for fp in p['footprints']:
    ref = fp['reference']
    if ref not in sch:
        continue
    for pad, info in (fp.get('pad_nets') or {}).items():
        a = (info.get('net') or '').lstrip('/')
        b = (sch[ref].get(str(pad)) or '').lstrip('/')
        if not b or a == b or a.startswith(('unconnected', 'Net-')) and b.startswith('__unnamed'):
            continue
        print(f'MISMATCH {ref} pad {pad}: sch={b} pcb={a}'); bad += 1
print(f'footprints checked: {len(p["footprints"])}, mismatches: {bad}')
print('U302 pad 9 ->', [f for f in p['footprints'] if f['reference']=='U302'][0]['pad_nets']['9'])
