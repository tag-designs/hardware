# PresTag

PresTag trades the accelerometer for a barometric pressure sensor. Where a
BitTag tells you *when* a bird was active, a PresTag tells you *how high* it
was, and when it climbed or descended. The board documented here is
**PresTag-v6**.

## The board

<div class="grid" markdown>

<figure markdown>
  ![PresTag-v6, top side](../images/boards/PresTag-v6-top.png)
  <figcaption>Top</figcaption>
</figure>

<figure markdown>
  ![PresTag-v6, bottom side](../images/boards/PresTag-v6-bottom.png)
  <figcaption>Bottom</figcaption>
</figure>

</div>

The LPS27's circular pressure port is visible at the centre of the top side. These are rendered from the KiCad layout by `kicad-cli`; see
[Board Designs](../boards/index.md) for how they are regenerated.

## Block diagram

```mermaid
flowchart LR
  subgraph TAG[PresTag-v6]
    direction LR
    subgraph SW[Switched]
      PRS["LPS27HHTW<br/>pressure + temperature"]
    end
    subgraph ON[Always on]
      direction TB
      RTC["RV-3028-C7<br/>RTC"]
      MCU["STM32L431KCU6<br/>processor"]
      FLASH["AT25FF321A<br/>4 MB serial flash"]
      RTC --- MCU
      MCU --- FLASH
    end
    subgraph PWR[Power]
      BAT["MS621FE-FL11E or<br/>MS920SE-FL27E<br/>D401 Schottky"]
    end
    IF["Interface<br/>SWD + pogo pads"]
  end
  SW --- ON
  ON --- PWR
  ON --- IF
```

The pressure sensor sits in the switched section because it is fed from its own
supply line, `LPS_PWR`, driven by a processor pin rather than by the main rail.

## Major components

| Role | Part | Domain | Notes |
| --- | --- | --- | --- |
| Processor | STM32L431KCU6 | Always on | |
| RTC | RV-3028-C7 | Always on | 32.768 kHz, 1 ppm |
| Sensor | LPS27HHTW | **Switched** | Barometric pressure and temperature |
| Memory | AT25FF321A-UUN | Always on | 4 MB; unusually low quiescent current for serial flash |
| Power | D401 CDBQC0130L-HF | — | Schottky reverse-polarity protection; no regulator |
| Battery | MS621FE-FL11E or MS920SE-FL27E | — | 5.5 mAh / 230 mg, or 11 mAh / 450 mg |

**Why the pressure sensor is gated.** The LPS27 draws about 0.9 µA just sitting
idle. On a tag whose whole budget is measured in microamps that is not a
rounding error, so its supply is switched off between samples rather than left
standing. The flash is the opposite case: the AT25FF321A was chosen precisely
because its quiescent current is low enough to leave powered, which is why it
sits in the always-on section next to the processor.

!!! note "Driving a sensor rail from a GPIO has a firmware contract"

    While the sensor rail is off, its bus lines are still driven from the main
    domain. Firmware must not leave them high, or the sensor can be
    back-powered through its protection diodes.

## What it records

Pressure and temperature, sampled at a configurable period. Barometric pressure
converts to altitude, so a PresTag record is a flight-altitude profile: how high
the bird flew, and the shape and timing of its climbs and descents.

The sample period sets the deployment length, which is why PresTag has no single
headline endurance figure the way BitTag does — it is whatever the chosen period
and the cell size imply.

## Power

Measured on firmware [`fw-v0.6`](https://github.com/tag-designs/software/releases/tag/fw-v0.6) at 2.4961 V from an unregulated 2.5 V
cell, at the 60 s sample period.

| State | Current |
| --- | ---: |
| `IDLE` | 0.11 µA |
| `RUNNING`, 60 s period | **0.39 µA** |
| `FINISHED` | 0.11 µA |

### Sample period

The sample period is the main lever on a PresTag deployment, and it has been
measured rather than modelled — six points on one board, 1200 s per window:

| Period | `RUNNING` | Period | `RUNNING` |
| ---: | ---: | ---: | ---: |
| 15 s | 1.13 µA | 45 s | 0.45 µA |
| 20 s | 0.88 µA | 60 s | 0.37 µA |
| 30 s | 0.62 µA | 90 s | 0.28 µA |

Fitting `I(T) = I_rest + Q/T` gives a resting term near 0.11 µA and
**15.2 µC per sample**, R² 0.99994. The per-sample energy is the durable
number — an independent campaign a month earlier got 15.3 µC — while the
resting floor it sits on varies from board to board, by more than any firmware
change has.

### What a deployment gets

Battery is not always what runs out first. The 4 MB flash holds 1,048,560
samples:

| Period | 5.5 mAh cell | 11 mAh cell | Memory | Usable, 5.5 mAh | Usable, 11 mAh |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 15 s | 204 d | 407 d | 182 d | **182 d** *(memory)* | **182 d** *(memory)* |
| 20 s | 262 d | 523 d | 243 d | **243 d** *(memory)* | **243 d** *(memory)* |
| 30 s | 371 d | 742 d | 364 d | **364 d** *(memory)* | **364 d** *(memory)* |
| 45 s | 505 d | 1009 d | 546 d | **505 d** *(battery)* | **546 d** *(memory)* |
| 60 s | 625 d | 1251 d | 728 d | **625 d** *(battery)* | **728 d** *(memory)* |
| 90 s | 822 d | 1644 d | 1092 d | **822 d** *(battery)* | **1092 d** *(memory)* |

On a 5.5 mAh cell the constraint switches from memory to battery around 33 s;
on 11 mAh, not until about 200 s. **Below those, sampling faster spends current
on data the flash cannot hold.** At the 60 s default: about 625 days on
5.5 mAh, 728 on 11 mAh — the latter capped by flash rather than by the cell.

Full log: [PresTag power results](https://github.com/tag-designs/software/blob/main/embedded/tags/families/PresTag/design/power-results.md).

## Design files

[Design directory on GitHub](https://github.com/tag-designs/hardware/tree/main/BoardDesigns/Tags/PresTag-v6){ .md-button }
[Schematic (PDF)](../schematics/PresTag-v6.pdf){ .md-button }

No design review has been written for this board. An earlier revision, a v3
design, is in the repository under `BoardDesigns/Tags/PresTag`.
