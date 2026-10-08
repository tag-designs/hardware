# Measuring and Debugging

Two questions dominate tag development, and they need different instruments.
*How much current does this cost?* is answered by a
[Joulescope](https://www.joulescope.com/). *What is the driver actually doing on
the bus?* is answered by a [Saleae](https://www.saleae.com/) logic analyzer.

The hardware is arranged so that the first can be asked of anything, and the
second only of a prototype. That asymmetry is the reason prototype boards exist.

## Current: the Joulescope reaches everything

A Joulescope connects at the 4-pin JST-XH, `J1`, on every base board — the net
is `EXT_PWR` on the coin-cell boards and `PWR_IN` on the LiPo ones. Because
every tag is powered through a base board, whether it is a finished tag on a
pogo connector or a prototype on a header pair, the same measurement works in
both cases.

The requirement this imposes is the one described in the
[base board overview](../bases/index.md#handing-the-supply-to-a-joulescope):
**when the instrument is connected, the board's own supply to the tag must be
out of the circuit.** Two sources on one rail would measure the wrong thing. How
that is done follows the battery chemistry — a physical changeover for LiPo, a
low-leakage analog switch for coin cells.

The bases also carry a current mirror, `TAG_MIRROR` on the tag bases and
`PWR_IN_MIRROR` on the breakout bases, for observing the supply without
interrupting it.

## Signals: the Saleae reaches only a prototype

A finished tag has six pogo pads, carrying power and SWD. Everything else is
buried between two packages on a board that has to weigh under a gram. There is
nowhere to attach a probe, and no room to add one.

A prototype board is the opposite: the signals between the processor and the
sensors cross a pair of 1×17 headers on 2.54 mm pitch. The breakout base brings
out essentially the entire processor — `PA0` through `PA15`, `PB0` through
`PB15`, plus `NRST`, `boot0`, `clkout` and the RTC's `rtc_scl` and `rtc_sda` —
and the prototype side names them for what they do:

| Prototype | What a logic analyzer can see |
| --- | --- |
| [UIUCBreakout](uiuc.md) | Three SPI buses — `ACCEL_*`, `AT25_*`, `LPS_*` — plus `LPS_PWR`, `LPS_RDY` and `WKUP1` |
| [IMUTagNandBMP581-breakout](imutag-nand-bmp581.md) | SPI to the flash and pressure sensor, I²C on `SCL`/`SDA`, interrupts `BMM_INT` and `LPS_DRDY`, the trigger `LSM_TRG`, and `FLASH_PWR` |

That is the full working surface of a device driver: the transactions, the
interrupt and data-ready timing, and the chip selects.

!!! tip "It also catches board defects, not just firmware ones"

    `tag-breakout-l432v2` has its RTC's SDA and SCL
    [crossed](../bases/tag-breakout-l432v2.md). On the bus that is unmistakable
    — clock and data doing each other's job — while from inside the firmware it
    looks like a clock that does not answer. A capture distinguishes a driver
    bug from a wiring bug in seconds, which is worth remembering before
    rewriting a driver that was already correct.

## Using them together

The combination is more useful than either alone, because the
**power-gating lines are visible to both instruments at once**. `LPS_PWR` and
`FLASH_PWR` appear on the headers as logic signals and as steps in the current
trace, so a question like *how long does the pressure sensor take to settle after
its rail comes up, and what does the inrush look like* can be answered in one
capture rather than inferred from two.

That is the measurement that settled two decisions already documented elsewhere:
the 10 Ω inrush-limiting resistor on the
[UIUC tag](https://tag-designs.github.io/hardware/tags/uiuctag.html)'s pressure
sensor, and the removal of the NAND load switch from
[IMUTag](https://tag-designs.github.io/hardware/tags/imutag.html) once the saving
turned out to be negligible.

## Why this argues for prototyping drivers first

A driver written against a finished tag can only be debugged by what the
firmware reports about itself. The same driver written against a prototype can
be watched directly, on the real sensor, at the real clock rate, with the real
current cost visible beside it.

By the time a tag-shaped board is fabricated, the drivers should already work —
and the only genuinely new questions should be mechanical.
