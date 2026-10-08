# Tag Designs

Six fabricated tag boards, each documented with its major components, a block
diagram, what it records, and a link to its design files.

| | Senses | Processor | Memory | Switched rail | Cell |
| --- | --- | --- | --- | --- | --- |
| [BitTagv7](bittag.md) | Movement | STM32L432KC | Internal only | — | Coin |
| [BitTagNG](bittagng.md) | Movement | STM32L432KC | 4 MB serial | — | Coin |
| [PresTag-v6](prestag.md) | Pressure | STM32L431KC | 4 MB serial | Pressure sensor | Coin |
| [CompassTag](compasstag.md) | Movement, magnetic field | STM32L432KC | 4 MB serial | Magnetometer (+1V8) | Coin |
| [UIUC Tag](uiuctag.md) | Movement, pressure | STM32L432KC | 4 MB serial | Pressure sensor | Coin |
| [IMUTag](imutag.md) | Movement, rotation, magnetic field, pressure | STM32U375KG | NAND | — | 12 mAh LiPo |

The [project home](https://tag-designs.github.io/) describes the tag families
from a user's point of view — what each one is for and which questions it
answers. These pages are about the boards.

## How to read the block diagrams

Every diagram on these pages follows the generic structure set out in the
project's [Hardware Architecture](https://tag-designs.github.io/architecture/hardware/)
page. A tag is divided into three regions:

**Always on** holds the processor, the RTC, and any sensor or memory whose
quiescent current is low enough to leave powered for the life of the deployment.
The ADXL362 and ADXL367 accelerometers sit here at around 10 nA idle, as does the
AT25 serial flash — chosen specifically because it is a low quiescent current
part, which most serial flash is not.

**Switched** holds anything fed from its own supply line rather than from the
main rail. In practice this means sensors a tag cannot afford to leave idling:
the LPS27 pressure sensor draws about 0.9 µA doing nothing, which on a budget
measured in microamps is not negligible. A switched part is powered either
directly from a processor pin or through a regulator whose enable pin a processor
pin controls.

**Power** holds the cell and any regulator. Most of these boards have no
regulator at all — parts run at battery voltage less one Schottky diode drop.
IMUTag is the exception.

A tag with no switched region is not an oversight. It means every part on the
board was chosen to be cheap enough at idle that gating it would not pay for
itself — and in IMUTag's case, that conclusion came from measuring a load switch
that was already there and then removing it.

## Shared conventions

All six boards are programmed and read through an ARM serial wire debug (SWD)
interface, reached by spring-loaded pogo pins contacting test pads on the board.
They connect to a [base board](https://tag-designs.github.io/architecture/hardware/),
which emulates the ST-LINK protocol so that standard open-source tools work
against them unmodified.

All six carry a Micro Crystal RV-3028 real-time clock, in the C7 or C8 variant.
At roughly 40 nA and 1 ppm it is what lets a tag sleep for months and still
timestamp what it recorded.

## Cells

The five boards without a core regulator take one of two Seiko rechargeable coin
cells, and the choice between them is mass against endurance:

| Cell | Capacity | Mass |
| --- | --- | --- |
| MS621FE-FL11E | 5.5 mAh | 230 mg |
| MS920SE-FL27E | 11 mAh | 450 mg |

IMUTag is the exception. Its switching converter regulates whatever the cell
gives down to 1.8 V, which frees it from the coin-cell voltage window; it runs
from a 12 mAh LiPo, with the specific cell not yet settled.

!!! warning "Battery chemistry is not interchangeable"

    On the boards without regulators the rail follows the cell, less one Schottky
    diode drop. A 3 V coin cell lands near 2.8 V, comfortably within range. A
    3.7 V LiPo at full charge would reach roughly 4.0 V — the absolute maximum
    rating of several of the parts involved, not merely outside their operating
    range. That substitution is safe only on IMUTag, and only because the
    converter stands between the cell and everything else.
