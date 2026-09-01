#!/usr/bin/env python3
"""Show the two SPI pin groups sharing SPI1 on the STM32."""
from _common import load
nets = load('schematic')['nets']
for n in ('ACCEL_SCK','ACCEL_MISO','ACCEL_MOSI','ACCEL_CS','AT25_SCK','AT25_MISO','AT25_MOSI','AT25_nCS'):
    pins = nets[n]['pins']
    print(f"{n:12s} " + ', '.join(f"{p['component']}.{p['pin_number']}({p['pin_name']})" for p in pins))
