#!/usr/bin/env python3
"""I2C rise-time budget for SDA/SCL with NO external pull-ups.

Pull-up is then only the STM32L432 internal weak pull-up:
RPU = 25 / 40 / 55 kOhm (DS11451 Rev 4, Table 57, p.~110).
I2C-bus spec (UM10204): tr(max) = 1000 ns standard mode (100 kHz),
                        tr(max) =  300 ns fast mode     (400 kHz).
tr for an RC bus = 0.8473 * R * C  (30%->70% of VDD).
"""
import json, glob

pcb = json.load(open(sorted(glob.glob('analysis/*/pcb.json'))[-1]))
lens = {n['net']: n['total_length_mm'] for n in pcb['net_lengths']}

# pin capacitances from datasheets
C_PIN_STM32 = 5.0   # DS11451 CIO pad capacitance, pF
C_PIN_RTC   = 10.0  # RV-3028-C7 App Manual, I2C pin load, pF (conservative)
# 2-layer, 0.4 mm FR4, NO ground pour under the traces -> low line capacitance
C_PER_MM    = 0.4   # pF/mm, conservative for an unreferenced 4 mil trace

RPU = {'min (fastest)': 25e3, 'typ': 40e3, 'max (slowest)': 55e3}
LIMITS = {'standard 100 kHz': 1000.0, 'fast 400 kHz': 300.0}

print(f"{'net':8s} {'len_mm':>7s} {'Cbus_pF':>8s}   " + "  ".join(f"tr@{k:>13s}" for k in RPU))
for net in ('/SDA', '/SCL'):
    L = lens.get(net, 0.0)
    C = C_PIN_STM32 + C_PIN_RTC + C_PER_MM * L
    trs = {k: 0.8473 * R * C * 1e-12 * 1e9 for k, R in RPU.items()}
    print(f"{net:8s} {L:7.2f} {C:8.1f}   " + "  ".join(f"{trs[k]:13.0f}ns" for k in RPU))
    for mode, lim in LIMITS.items():
        worst = trs['max (slowest)']
        verdict = 'PASS' if worst <= lim else 'FAIL'
        print(f"         -> {mode:18s} limit {lim:6.0f} ns : worst-case {worst:6.0f} ns  {verdict}")
