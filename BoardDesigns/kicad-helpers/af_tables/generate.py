#!/usr/bin/env python3
"""Generate an AF table for stm32_pinmap.py from the STM32_open_pin_data submodule.

ST's own machine-readable pin data, the same source STM32CubeMX uses — so this
replaces reading alternate-function tables out of the datasheet PDF, which is
error-prone: a layout-text parse of the U375's Tables 22-23 silently shifts every
column after any cell that wraps to a second line.

    python3 generate.py STM32U375KGUx          # writes stm32u375.json
    python3 generate.py STM32L432KCUx --stdout

Two files are read per part:
  mcu/<part>.xml          pin positions and the signals each pin can carry
  mcu/IP/GPIO-<ver>...    the AF number for each (pin, signal) pair
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(REPO, 'STM32_open_pin_data', 'mcu')

TAG = re.compile(r'\{.*\}')


def local(el):
    return TAG.sub('', el.tag)


def portname(raw):
    """'PB3 (JTDO/TRACESWO)' -> 'PB3';  'PC14-OSC32_IN (PC14)' -> 'PC14'."""
    tok = re.split(r'[\s(\-/]', (raw or '').strip(), maxsplit=1)[0]
    return tok if re.fullmatch(r'P[A-Z]\d{1,2}', tok) else None


def find_mcu(part):
    """Resolve a part to its XML, allowing ST's bracket form (STM32L432K(B-C)Ux)."""
    exact = os.path.join(DATA, part + '.xml')
    if os.path.exists(exact):
        return exact, part
    for f in sorted(os.listdir(DATA)):
        if not f.endswith('.xml'):
            continue
        # expand (B-C) / (4-6) style ranges into a regex character class
        pat = re.sub(r'\(([A-Z0-9])-([A-Z0-9])\)', r'[\1-\2]', f[:-4])
        pat = pat.replace('(', '[').replace(')', ']').replace('|', '')
        try:
            if re.fullmatch(pat, part, re.I):
                return os.path.join(DATA, f), f[:-4]
        except re.error:
            continue
    return None, None


def build(part):
    mcu_path, matched = find_mcu(part)
    if not mcu_path:
        cands = [f[:-4] for f in os.listdir(DATA)
                 if f.lower().startswith(part.lower()[:9]) and f.endswith('.xml')]
        sys.exit(f"no XML matching {part} in {DATA}\ncandidates: {', '.join(sorted(cands)[:12])}")

    root = ET.parse(mcu_path).getroot()

    # pin position -> port name, the GPIO IP version, and every signal ST lists
    positions, gpio_ver, signals = {}, None, {}
    for el in root.iter():
        if local(el) == 'IP' and el.get('Name') == 'GPIO':
            gpio_ver = el.get('Version')
        if local(el) == 'Pin' and el.get('Type') == 'I/O':
            name = portname(el.get('Name'))
            if name:
                positions[name] = el.get('Position')
                signals[name] = [c.get('Name') for c in el
                                 if local(c) == 'Signal' and c.get('Name') != 'GPIO']
    if not gpio_ver:
        sys.exit(f'{part}: no GPIO IP version in the MCU XML')

    modes = os.path.join(DATA, 'IP', f'GPIO-{gpio_ver}_Modes.xml')
    if not os.path.exists(modes):
        sys.exit(f'{part}: expected GPIO modes file not found: {modes}')

    af = {}
    for pin in ET.parse(modes).getroot().iter():
        if local(pin) != 'GPIO_Pin':
            continue
        port = portname(pin.get('Name'))
        if port not in positions:
            continue                      # not bonded out on this package
        for sig in pin:
            if local(sig) != 'PinSignal':
                continue
            for sp in sig:
                if sp.get('Name') != 'GPIO_AF':
                    continue
                for pv in sp:
                    m = re.match(r'GPIO_AF(\d+)_', (pv.text or '').strip())
                    if m:
                        af.setdefault(port, {})[m.group(1)] = sig.get('Name')
    return {
        '_source': f'STM32_open_pin_data (STM32CubeMX-DB), mcu/{part}.xml + '
                   f'mcu/IP/GPIO-{gpio_ver}_Modes.xml',
        '_matched_xml': matched,
        '_generated_by': 'af_tables/generate.py — do not hand-edit; regenerate instead',
        '_part': part,
        'positions': positions,
        'af': af,
        # Signals with NO GPIO_AF entry. The datasheet calls these "additional
        # functions" - selected through peripheral registers, not GPIOx_AFR - and
        # they are easy to miss. RCC_OSC32_IN on PC14 is one: reading only the AF
        # map makes that pin look like it has no peripheral use at all, when in
        # fact it is the LSE input and can take an external clock in bypass mode.
        'additional': {p: sorted(set(sigs) - set(af.get(p, {}).values()))
                       for p, sigs in signals.items()
                       if set(sigs) - set(af.get(p, {}).values())},
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('part', help='e.g. STM32U375KGUx')
    ap.add_argument('--stdout', action='store_true')
    a = ap.parse_args()

    table = build(a.part)
    if a.stdout:
        json.dump(table, sys.stdout, indent=1, sort_keys=True)
        print()
    else:
        fam = re.match(r'(stm32[a-z]\d{3})', a.part.lower()).group(1)
        out = os.path.join(HERE, fam + '.json')
        with open(out, 'w') as fh:
            json.dump(table, fh, indent=1, sort_keys=True)
            fh.write('\n')
        print(f"{os.path.basename(out)}: {len(table['af'])} ports, "
              f"{sum(len(v) for v in table['af'].values())} AF entries, "
              f"{len(table['positions'])} bonded pins")
