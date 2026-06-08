# Ultra-Miniature 1.8V Step-Down Power Supply Design

This document details the optimized component selection and layout design for stepping down a Lithium-Polymer (LiPo) battery voltage down to **1.8V** using the Texas Instruments **TPS62840** high-efficiency buck regulator. 

The configuration is optimized for space-constrained applications with a **30 mA peak load current**.

---

## 1. System Overview & IC Details
The design leverages the Texas Instruments TPS62840 due to its ultra-low 60 nA operating quiescent current (\(I_Q\)) and excellent efficiency at extremely light loads (< 100 µA to 30 mA).

* **Regulator IC:** Texas Instruments `TPS62840YBGR`
* **Package:** 6-DSBGA (WCSP)
* **Silicon Footprint:** 0.97 mm × 1.47 mm × 0.5 mm
* **Control Scheme:** PFM-only mode, ideal for a 30 mA peak load.

---

## 2. Finalized Ultra-Small Bill of Materials (BOM)

Because the peak current is restricted to 30 mA, every single passive component has been successfully shrunk down to micro-footprints (**0402** and **0201** metric packages) without risking inductor saturation or compromising battery runtime.


| Component Reference | Description | Recommended Part Number | Footprint Size (Metric) | Dimensions (mm) | Key Specifications |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **U1** | High-efficiency buck regulator | **TI TPS62840YBGR** | 6-DSBGA / WCSP | 1.47 × 0.97 | 60 nA \(I_Q\), up to 750 mA limit |
| **L1** | Multilayer chip power inductor | **TDK MLZ1005M2R2WTD25** | 0402 | 1.00 × 0.50 | 2.2 µH, 60 mA \(I_{SAT}\), 0.55 Ω DCR |
| **C_IN** | Ceramic Input Capacitor | **Murata GRM155R60J106ME15D** | 0402 | 1.00 × 0.50 | 10 µF, 6.3V, X5R, ±20% |
| **C_OUT** | Ceramic Output Capacitor | **Murata GRM155R60J226ME11D** | 0402 | 1.00 × 0.50 | 22 µF, 6.3V, X5R, ±20% |
| **C_BYP** | Internal Bypass Capacitor | **Murata GRM155R60J106ME15D** | 0402 | 1.00 × 0.50 | 10 µF, 6.3V, X5R, ±20% |
| **R_SET** | Output Voltage Set Resistor | **Panasonic ERJ-1GEF3242C** | 0201 | 0.60 × 0.30 | **32.4 kΩ, ±1% tolerance**, 0.05W |

---

## 3. Circuit Block Diagram

```text
                       [ L1: 0402 Inductor ]
                             (2.2 µH)
                                │
[ LiPo In ] ───► [ U1: TPS62840 IC ] ───► [ 1.8V Out ] ───► To 30mA Load
    │                   │                      │
[ C_IN ]            [ R_SET ]              [ C_OUT ]
  10µF                32.4 kΩ                22µF
    │                   │                      │
[  GND  ] ────────── [  GND  ] ──────────── [  GND  ]
```

---

## 4. Design & Assembly Rules for Micro-Footprints

### VSET Resistor Requirements
The TPS62840 does not use standard dynamic feedback. It checks the analog value of $R_{SET}$ exactly once during its startup sequence to choose one of 16 internal factory-programmed voltage targets.
* **Tolerance:** The 32.4 kΩ resistor **must maintain a ±1% tolerance** (or better). If the resistor drifts out of this window, the IC will boot into an incorrect voltage tier.
* **Cleanliness Warning:** Residual solder flux under an 0201 package can introduce parasitic resistance parallel to $R_{SET}$. Ensure a thorough post-assembly isopropyl alcohol (IPA) wash to avoid unintended voltage scaling.

### Layout Considerations
1. **Star Grounding:** Tie the ground pads of `C_IN`, `C_OUT`, and the `GND` pins of the TPS62840 into a unified copper pour area directly beneath the chip to keep switching loops tight.
2. **Trace Routing:** Since the current is tiny (30 mA), minimal 0.15 mm (6 mil) traces can safely be used for signal and power, matching the thin escape routes needed for the WCSP package bumps.
3. **Assembly Method:** Due to the combination of a 0.5mm pitch WCSP IC, 0402 passives, and an 0201 resistor, this layout **cannot be hand-soldered**. It requires automated pick-and-place placement with a precision stencil (typically 3-mil or 4-mil thickness) and standard reflow profiles.
