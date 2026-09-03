#!/usr/bin/env python3
"""Add KiCad pin alternates to an STM32 symbol, from ST's own pin data.

KiCad lets a symbol declare each pin's alternate functions; you then pick one per
instance (right-click a pin -> Alternate Pin Function) and the choice is recorded
in the .kicad_sch. That is the native way to say "PB4 is LPTIM1_CH2, not a GPIO",
and it removes the guesswork the pin-map helper would otherwise have to do.

The stock MCU_ST_STM32* libraries carry tens of thousands of these, but only for
families ST and KiCad ship symbols for. There is no STM32U3 symbol upstream at all
(stock has U0 and U5), so a hand-drawn symbol has to grow its own - which is what
this does, using af_tables/<family>.json as the source.

    python3 add_pin_alternates.py ../../libraries/tag_library.kicad_sym stm32u375 \\
            --table stm32u375.json                 # writes in place, .bak kept
    python3 add_pin_alternates.py ... --dry-run    # report only

Pins are matched to ports by PACKAGE PIN NUMBER, taken from the table's
"positions" map, not by pin name - so a pin named "BOOT0-PB7" still resolves.
Existing alternates are replaced, so re-running is safe and idempotent.
"""
import argparse
import json
import os
import re
import shutil
import sys

TYPE_FOR = {                       # electrical type per signal family
    'DEBUG': 'bidirectional',
    'RCC': 'input',
}


def sexp_block(src, start):
    d = 0
    i = start
    while True:
        if src[i] == '(':
            d += 1
        elif src[i] == ')':
            d -= 1
            if d == 0:
                return src[start:i + 1]
        i += 1


def find_symbol(src, name):
    m = re.search(r'\n\t\(symbol "%s"' % re.escape(name), src)
    if not m:
        sys.exit(f'symbol "{name}" not found')
    start = src.index('(', m.start())
    return start, sexp_block(src, start)


def elec_type(signal, default):
    return TYPE_FOR.get(signal.split('_')[0], default)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbol_lib')
    ap.add_argument('symbol_name')
    ap.add_argument('--table', required=True, help='af_tables/<family>.json')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    tbl = json.load(open(a.table if os.path.isabs(a.table)
                         else os.path.join(os.path.dirname(os.path.abspath(__file__)), a.table)))
    af, positions = tbl['af'], tbl['positions']
    additional = tbl.get('additional', {})
    by_pin = {num: port for port, num in positions.items()}

    src = open(a.symbol_lib).read()
    sym_start, sym = find_symbol(src, a.symbol_name)

    out, last, touched, added = [], 0, 0, 0
    for m in re.finditer(r'\(pin[ \n]', sym):
        blk = sexp_block(sym, m.start())
        num = re.search(r'\(number "([^"]*)"', blk)
        etype = re.match(r'\(pin (\w+) (\w+)', blk)
        if not num or num.group(1) not in by_pin:
            continue
        port = by_pin[num.group(1)]

        # every AF, plus additional functions (RCC_OSC32_IN and friends), which are
        # real pin uses even though they carry no AF number
        sigs = sorted(set(af.get(port, {}).values()) | set(additional.get(port, [])))
        sigs = [s for s in sigs if s != 'EVENTOUT']
        if not sigs:
            continue

        stripped = re.sub(r'\s*\(alternate [^)]*\)', '', blk)   # idempotent re-run
        body = stripped[:stripped.rindex(')')].rstrip()
        alts = ''.join(f'\n\t\t\t\t(alternate "{s}" {elec_type(s, etype.group(1))} '
                       f'{etype.group(2)})' for s in sigs)
        newblk = body + alts + '\n\t\t\t)'
        out.append(sym[last:m.start()]); out.append(newblk)
        last = m.start() + len(blk)
        touched += 1
        added += len(sigs)
    out.append(sym[last:])
    newsym = ''.join(out)

    print(f'{a.symbol_name}: {touched} pins matched by package position, '
          f'{added} alternates')
    if a.dry_run:
        return
    shutil.copy(a.symbol_lib, a.symbol_lib + '.bak')
    open(a.symbol_lib, 'w').write(src[:sym_start] + newsym + src[sym_start + len(sym):])
    print(f'written; previous kept as {os.path.basename(a.symbol_lib)}.bak')


if __name__ == '__main__':
    main()
