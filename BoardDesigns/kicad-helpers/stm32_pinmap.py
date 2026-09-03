#!/usr/bin/env python3
"""Full pin map for any STM32 on the board: pin -> port -> net -> what it drives.

Standard output for every review that has an STM32-family part. Prints one row
per MCU pin, then the three things the map reliably surfaces on these tags:

  * shared SPI buses     - devices sharing SCK/MISO/MOSI with separate selects,
                           which makes chip-select deselect a firmware contract
  * BOOT0 straps         - a BOOT0-capable pin carrying a pulled-up signal needs
                           an explicit option-byte write and read-back
  * unused GPIOs         - should be analog/no-pull for lowest leakage
  * AF collisions        - two nets needing the SAME peripheral signal (e.g. two
                           pins both wanting SPI1_MISO), which an STM32 cannot
                           route simultaneously
  * pin-number errors    - the symbol's pin numbering checked against the real
                           package, catching a wrong-pinout symbol that DRC and
                           ERC both pass silently
  * declared intent      - the KiCad pin alternate chosen on the schematic, if
                           any. That is the designer SAYING what a pin does, so
                           it beats inference: /LSM_TRG announces itself as
                           LPTIM1_CH2 instead of looking like a GPIO. Generate
                           the alternates with af_tables/add_pin_alternates.py.
  * peripheral options   - for pins with no chosen alternate and no bus role in
                           the net name, the peripheral functions the pin CAN do,
                           so intent gets confirmed rather than assumed.

The last two need af_tables/<family>.json, generated from ST's own pin data:

    python3 af_tables/generate.py STM32U375KGUx

Detects the MCU from the BOM, so it needs no per-board configuration. Pass a
reference (e.g. U302) to force a particular part.
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

from _common import load

HERE = os.path.dirname(os.path.abspath(__file__))


def af_table(part):
    """AF + package map for the family, or None. See af_tables/generate.py."""
    m = re.match(r'(stm32[a-z]\d{3})', part.lower())
    if not m:
        return None
    path = os.path.join(HERE, 'af_tables', m.group(1) + '.json')
    return json.load(open(path)) if os.path.exists(path) else None

sch = load('schematic')


def chosen_alternates(ref):
    """Pin -> alternate function the designer selected on the schematic.

    The analyzer's schematic.json carries only component/pin_number/pin_name/
    pin_type, so the selection is read from the .kicad_sch itself.
    """
    files = [f for f in glob.glob('*.kicad_sch')
             if 'panel' not in f and '-back' not in f]
    if not files:
        return {}
    src = open(files[0]).read()
    out = {}
    for m in re.finditer(r'\(property "Reference" "%s"' % re.escape(ref), src):
        i = src.rfind('(symbol', 0, m.start())
        d = 0
        j = i
        while True:
            if src[j] == '(':
                d += 1
            elif src[j] == ')':
                d -= 1
                if d == 0:
                    break
            j += 1
        for pm in re.finditer(r'\(pin "([^"]+)"(?:(?!\(pin ").)*?\(alternate "([^"]+)"',
                              src[i:j + 1], re.S):
            out[pm.group(1)] = pm.group(2)
    return out

# --- find the STM32 -----------------------------------------------------------
want = sys.argv[1] if len(sys.argv) > 1 else None
mcus = []
for b in sch['bom']:
    text = f"{b.get('value','')} {b.get('mpn','')}".lower()
    if 'stm32' in text:
        for ref in b['references']:
            mcus.append((ref, b.get('mpn') or b.get('value')))
if want:
    mcus = [m for m in mcus if m[0] == want]
if not mcus:
    sys.exit('no STM32 found in the BOM (pass a reference to override)')

# --- pin -> (name, type, net, other nodes) ------------------------------------
for ref, part in mcus:
    pins = {}
    for net_name, net in sch['nets'].items():
        for p in net.get('pins', []):
            if p['component'] != ref:
                continue
            others = [f"{q['component']}.{q['pin_number']}" for q in net['pins']
                      if q['component'] != ref and not q['component'].startswith('#')]
            pins[p['pin_number']] = (p.get('pin_name', ''), p.get('pin_type', ''),
                                     net.get('display_name') or net_name, others)

    picked = chosen_alternates(ref)
    if picked:
        print(f"   {len(picked)} pin alternate(s) chosen on the schematic - "
              f"declared intent, not inferred")
    print(f"=== {ref}  {part}   {len(pins)} pins ===\n")
    print(f"{'Pin':>4}  {'Port':<14} {'Net':<22} Connected to")
    print('-' * 96)

    unused, boot0, bus = [], [], defaultdict(list)
    for num in sorted(pins, key=lambda x: int(x) if x.isdigit() else 999):
        name, ptype, net, others = pins[num]
        # KiCad names an unconnected pin's net after the pin itself
        if net.startswith('unconnected-') or not others and ptype == 'bidirectional':
            unused.append((num, name))
            print(f"{num:>4}  {name:<14} {'—':<22} — (unused)")
            continue
        # a rail fans out to everything; a count is more use than the list
        shown = f"rail — {len(others)} nodes" if len(others) > 8 else (', '.join(others) or '—')
        alt = f"   [{picked[num]}]" if num in picked else ''
        print(f"{num:>4}  {name:<14} {net:<22} {shown}{alt}")
        if 'BOOT0' in name.upper():
            boot0.append((num, name, net, others))
        m = re.match(r'^/?(.+?)_(SCK|CK|CLK|MISO|MOSI|CS|nCS)$', net)
        if m:
            bus[m.group(1)].append((m.group(2), num, name, others))

    # --- the three things worth saying out loud --------------------------------
    print()
    shared = {k: v for k, v in bus.items()
              if len({o for _, _, _, others in v for o in others}) > 1}
    if bus:
        print('SPI/serial buses:')
        for name, members in sorted(bus.items()):
            devs = sorted({o.split('.')[0] for _, _, _, others in members for o in others})
            tag = '  <-- SHARED, deselect is a firmware contract' if len(devs) > 1 else ''
            print(f"   {name:<10} {' '.join(sig for sig, _, _, _ in sorted(members)):<28} "
                  f"devices: {', '.join(devs)}{tag}")

    if boot0:
        print('\nBOOT0 strap:')
        for num, name, net, others in boot0:
            pulled = any(o.startswith('R') for o in others)
            print(f"   pin {num} {name} carries {net} -> {', '.join(others)}")
            print(f"   {'PULLED via ' + [o for o in others if o.startswith('R')][0] if pulled else 'no resistor on the net'}"
                  f" - production programming must write AND read back the option bytes")

    # --- AF cross-check --------------------------------------------------------
    tbl = af_table(part or '')
    if tbl is None:
        print('\nAF check skipped - no af_tables/ entry for this family.')
        print('   Add one (hand-verified from the datasheet) to enable it.')
    else:
        af, notes = tbl['af'], tbl.get('notes', {})
        pos = tbl.get('positions', {})
        wants = {}          # peripheral signal -> [pins asking for it]
        print(f"\nAF cross-check against {tbl['_source']}")
        for num, (name, _t, net, _o) in sorted(
                pins.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999):
            port = re.match(r'(P[A-H]\d{1,2})', name)
            if not port or port.group(1) not in af:
                continue
            port = port.group(1)
            role = re.search(r'(SCK|CK|CLK|MISO|MOSI|SCL|SDA)$', net, re.I)
            if not role:
                continue
            role = role.group(1).upper()
            role = 'SCK' if role in ('CK', 'CLK') else role
            hits = [(n, sig) for n, sig in af[port].items() if sig.endswith('_' + role)]
            for n, sig in hits:
                wants.setdefault(sig, []).append((num, port, n, net))
        # symbol pin numbers vs the real package - a wrong-pinout symbol passes
        # DRC and ERC silently, so this is worth checking every time
        wrong = []
        for num, (name, _t, _net, _o) in pins.items():
            m = re.match(r'(P[A-H]\d{1,2})', name or '')
            if m and m.group(1) in pos and pos[m.group(1)] != num:
                wrong.append((m.group(1), num, pos[m.group(1)]))
        if wrong:
            for port, sym, real in sorted(wrong):
                print(f"   PINOUT ERROR  symbol puts {port} on pin {sym}, "
                      f"{tbl.get('_part', 'the package')} has it on pin {real}")
        else:
            checked = sum(1 for _n, (nm, _t, _x, _y) in pins.items()
                          if re.match(r'(P[A-H]\d{1,2})', nm or '')
                          and re.match(r'(P[A-H]\d{1,2})', nm).group(1) in pos)
            print(f"   pin numbering matches the package ({checked} GPIO pins checked)")

        clash = {sig: v for sig, v in wants.items() if len({p for _, p, _, _ in v}) > 1}
        if clash:
            for sig, v in sorted(clash.items()):
                print(f"   COLLISION  {sig} is wanted by "
                      + ' and '.join(f"{port}(pin {num}, AF{n}, {net})" for num, port, n, net in v))
            print('   An STM32 routes each peripheral signal to ONE pin at a time.')
            print('   These groups cannot be live simultaneously - remap at runtime or bit-bang one.')
        else:
            print('   no peripheral-signal collisions')
        # For pins whose net name reveals no bus role, show what peripherals the
        # pin can drive. The netlist cannot say whether /LSM_TRG is a GPIO or a
        # timer output - only the designer knows, so surface the options.
        INTERESTING = re.compile(r'^(LPTIM|TIM|USART|UART|LPUART|SPI|I2C|I3C|SAI|ADC|DAC)\d')
        opts = []
        for num, (name, _t, net, _o) in sorted(
                pins.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999):
            m = re.match(r'(P[A-H]\d{1,2})', name or '')
            if not m or m.group(1) not in af or (num, name) in unused:
                continue
            if num in picked:
                continue                       # designer declared it; nothing to ask
            if re.search(r'(SCK|CK|CLK|MISO|MOSI|SCL|SDA)$', net, re.I):
                continue                       # already resolved as a bus signal
            dbg0 = af[m.group(1)].get('0', '')
            if dbg0.startswith('DEBUG_'):
                netu = re.sub(r'[^A-Z0-9]', '', net.upper())
                # skip only if the pin IS its debug function (SWDIO/SWCLK)
                if any(re.sub(r'[^A-Z0-9]', '', q) in netu
                       for q in dbg0.split('_', 1)[1].split('-')):
                    continue
            cands = sorted({sig for n, sig in af[m.group(1)].items()
                            if INTERESTING.match(sig)},
                           key=lambda x: (not x.startswith('LPTIM'), x))[:4]
            if cands:
                opts.append((num, m.group(1), net, cands, af[m.group(1)]))
        if opts:
            print('\nPins with no bus role in the net name - confirm intent:')
            for num, port, net, cands, sigs in opts:
                shown = ', '.join(f"AF{[k for k, v in sigs.items() if v == c][0]} {c}"
                                  for c in cands)
                print(f"   pin {num:>2} {port:<5} {net:<14} could be: {shown}")

        # what each used pin gives up, derived rather than hand-listed
        for num, (name, _t, net, _o) in sorted(
                pins.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999):
            m = re.match(r'(P[A-H]\d{1,2})', name or '')
            if not m or m.group(1) not in af or (num, name) in unused:
                continue
            port, sigs = m.group(1), af[m.group(1)]
            dbg = sigs.get('0', '')
            if dbg.startswith('DEBUG_'):
                fn = dbg.split('_', 1)[1]                       # e.g. JTMS-SWDIO
                netu = re.sub(r'[^A-Z0-9]', '', net.upper())
                # only a forfeit if the net is NOT that debug function itself
                if not any(re.sub(r'[^A-Z0-9]', '', part) in netu for part in fn.split('-')):
                    print(f"   {port} ({net}) forfeits {fn} on AF0")
            extra = tbl.get('additional', {}).get(port, [])
            if set(sigs) <= {'15'} and extra:
                print(f"   {port} ({net}) has no ALTERNATE functions, but ST lists "
                      f"additional function(s): {', '.join(extra)}")
                print(f"      (additional functions are enabled through peripheral "
                      f"registers, not GPIOx_AFR - do not read 'no AF' as 'no use')")
            elif set(sigs) <= {'15'}:
                print(f"   {port} ({net}) has no peripheral functions at all")
        for port, note in notes.items():
            print(f"   note {port}: {note}")

    if unused:
        print(f"\nUnused GPIOs ({len(unused)}) - set analog/no-pull for lowest leakage:")
        print('   ' + ', '.join(f"{n}:{p}" for n, p in unused))
        if any(p == 'PA15' for _, p in unused):
            print('   PA15 has a default pull-up on STM32 - set it explicitly.')
    print()
