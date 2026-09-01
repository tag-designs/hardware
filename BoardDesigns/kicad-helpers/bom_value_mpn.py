#!/usr/bin/env python3
"""Flag BOM lines whose Value field names a different part than the MPN field.

Compares the alphanumeric part-number core, so stm32l431kc vs STM32L432KCU6
is reported as a mismatch (L431 and L432 are different devices).
"""
import re
from _common import load
def core(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())
for b in load('schematic')['bom']:
    v, m = str(b.get('value', '')), str(b.get('mpn', ''))
    if not m or not b['references'][0].startswith('U'):
        continue
    cv, cm = core(v), core(m)
    ok = cv.startswith(cm[:len(cv)]) or cm.startswith(cv[:len(cm)])
    print(f"{','.join(b['references']):8s} value={v:20s} mpn={m:34s} {'ok' if ok else 'MISMATCH'}")
