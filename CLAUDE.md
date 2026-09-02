# tag-designs / hardware — working notes

KiCad projects for low-power animal-borne sensor tags. Each board lives in
`BoardDesigns/<name>/`. Reviews use the `kicad-happy` skill suite (`kicad`,
`emc`, `spice`, `datasheets`, `bom`, distributor and fab skills).

## Before reviewing any board — read its `.kicad-happy.json` first

Several boards carry a `.kicad-happy.json` that encodes design intent, the
power profile, the mating-baseboard contract, and rule suppressions with
reasons. It is the difference between a useful review and one that
re-litigates settled decisions.

Only 5 of the ~55 boards have one. If the board under review has no config,
expect to re-derive conventions that are already written down elsewhere — read
`BoardDesigns/CompassTag/.kicad-happy.json` and
`BoardDesigns/BitTagNG/.kicad-happy.json` as the reference examples, and offer
to write one for the board as part of the review.

**Suppressions are only half-automatic — verified 2026-08-31.** `analyze_emc.py`
and `analyze_thermal.py` call `apply_suppressions()` and honour the config;
`analyze_schematic.py` and `analyze_pcb.py` load the config for project
settings and design intent but **deliberately do not apply suppressions**
(see the comment at `analyze_schematic.py:9881` — it claims schematic warnings
"lack rule_ids", which is now stale, since they carry PR-002, PU-001, RS-001
and friends).

Measured on BitTagNG: adding a config suppressed 19 of 35 EMC findings
(CK-003 ×11, IO-001 ×6, IO-002, SU-001) and **zero** schematic or PCB findings.

So for schematic/PCB rules the config is documentation *for the reviewer to
read*, not a filter that runs. Read the `suppressions` and `reviewer_notes`
blocks yourself and honour them by hand; do not assume a finding that survived
the analyzer is therefore unaccepted.

## House conventions that look like defects but are not

These recur across the tag family. Do not raise them as blockers without first
checking whether the board's config already accepts them.

- **No external I²C pull-ups.** Firmware drives the RV-3028 RTC with a *slow
  bit-banged software I²C driver* on the STM32 internal pull-ups (R<sub>PU</sub>
  25/40/55 kΩ). This is deliberate and works in the field. On a tag-sized board
  the measured worst-case rise time is ~730 ns against the 1000 ns
  standard-mode limit. It does **not** survive a move to the hardware I²C
  peripheral or 400 kHz — that part is worth flagging.
- **No external chip-select pull-ups.** Flash and sensor deselect is a
  firmware/reset-state contract using STM32 internal pull-ups. Firmware drives
  CS high as its first GPIO action.
- **Missing transistor base resistors.** On tags that plug into a baseboard,
  the reset transistor's base series resistor lives on the *baseboard*, not the
  tag. Check `mating_design` in the config before calling it a defect.
- **`Value` vs `MPN` mismatches.** Fab and assembly consume the `MPN` field and
  treat `Value` as a label, so a mismatch does not break a build. It does
  mislead *human* review — including automated review — so it is a real cleanup
  item, just not a blocker.
- **0.1016 mm (4 mil) traces and 0.102 mm annular rings.** Deliberate on these
  dense tags. A fabrication process-selection concern, never a current-capacity
  one at ~10 µA typical.
- **`J3xx` one-pin "connectors"** are usually 1.1 mm mounting holes, not I/O.
  Any EMC-filtering or clock-near-connector finding that cites them is noise.
- **Custom footprints are UltraLibrarian or vendor-supplied and have shipped.**
  `BGA9_BMM350_BOS`, `QFN10_BMP581_BOS`, `LGA14-L_2P59X3P1X0P5_STM`,
  `IC_TPS22916BYFPR`, `RV-3028-C8` and friends. Treat their land, mask and paste
  geometry as validated; do not re-derive it against IPC or a datasheet land
  pattern. U302/U6 use KiCad stock footprints, also correct as shipped.
- **Zero solder mask expansion.** `pad_to_mask_clearance 0` is in 29 of the 30
  boards here — it is KiCad's default, not a decision, and fabs apply their own
  expansion (~0.05 mm/side) regardless, so the delivered lands are NSMD. Not a
  finding, even under a fine-pitch BGA.

## Analyzer false positives seen repeatedly

- **GND "split into N islands" / "crosses a plane gap."** The analyzer's
  union-find over copper does not merge islands the way KiCad's connectivity
  engine does. **Always confirm with KiCad's own DRC before believing it.**
- **"Vias not tented."** Check for `(viasonmask false)` in the `.kicad_pcb` —
  that means vias *are* tented.
- **"via in pad, `same_net: false`"** under a QFN. Verify by computing the via
  coordinates against the exposed-pad rectangle; these have been GND-on-GND
  every time so far.
- **Heuristic power budgets** (e.g. "20 mA MCU + 10 mA per peripheral") are
  placeholders and meaningless for a coin-cell tag. Ignore them.
- **Stray `.kicad_pro` files poison the analyzer.** It can pick up any project
  file in the board directory, not the board's own. Verified twice:
  `imutag-smps` was analyzed against `BitTagNG-LIS2DU12...kicad_pro`, and
  `BitTagNG` against `panel-copy.kicad_pro` — so every rule-derived number in
  those runs was measured against the wrong rule set. The selection rule is
  neither alphabetical nor newest-first; do not try to predict it. **Check
  `project_settings.source` and `design_rule_compliance.rules_source` in
  `pcb.json` before trusting any rule-derived finding.** Both offenders were
  swept on 2026-09-01: the BitTagNG copies, and `panel-copy.kicad_pro` — an
  artifact of copying a previous design as the starting point for a new one,
  left in 13 directories with no matching board or schematic. Re-run any
  analysis whose `rules_source` names something other than the board's own
  `.kicad_pro`.

## Running DRC

Use KiCad's own DRC to settle connectivity questions the analyzer raises:

```bash
kicad-cli pcb drc --format json -o drc.json <board>.kicad_pcb
```

**Copy the `.kicad_pro` alongside the `.kicad_pcb`** when running on a copy.
Without it, DRC falls back to KiCad defaults and reports hundreds of bogus
clearance violations against these intentionally tight rules — on BitTagNG,
382 violations with defaults versus 25 with the project's own rules.

`kicad-cli` is not on `PATH`; it is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.

Three traps that cost real time on 2026-09-01:

- **Run DRC from the board's own directory.** Even with the `.kicad_pro` copied,
  a scratch copy without `fp-lib-table` reports 11 phantom `lib_footprint_issues`
  plus 2 nonmirrored-text warnings. In place: clean.
- **Pass `--refill-zones` whenever you DRC-test a via or track resize.** Stale
  zone fill produced up to 71 phantom clearance violations and made the option
  that actually worked look impossible. Add `--save-board` to keep the refill.
- **Never edit `.kicad_pro` or `.kicad_pcb` while KiCad has the project open.**
  KiCad holds project settings in memory and rewrites the file on save, silently
  reverting external edits. This wiped a set of net-class and constraint changes,
  after which new vias were placed at the reverted defaults. Check for
  `~*.lck` files first, or make design-rule changes in Board Setup instead.

## Datasheets

`BoardDesigns/libraries/datasheets/` is the shared store; individual boards
symlink to it as `datasheets/`. No distributor API credentials are configured,
and LCSC has no listing for most of these specialty parts, so **automated
datasheet sync mostly fails** — if a datasheet is missing, ask rather than
burning time on fetch attempts.

Verify pinouts against the manufacturer PDF, never against the KiCad symbol —
checking a symbol against itself is circular, and a symbol whose pinout
disagrees with the real part passes DRC and ERC silently.

## Review helpers

`BoardDesigns/kicad-helpers/` holds board-agnostic probes over analyzer JSON.
Run them from a board directory that has an `analysis/` folder:

```bash
cd BoardDesigns/<board>
PYTHONPATH=../kicad-helpers python3 ../kicad-helpers/padnet_crosscheck.py
```

`padnet_crosscheck.py` is worth running on **every** review — it compares every
schematic pin-net against every PCB pad-net, and a mismatch there is both
invisible to DRC/ERC and fatal. See `kicad-helpers/README.md` for the rest.

Several helpers carry board-specific constants in their docstrings (pin
capacitance, driver impedance). Read the docstring before quoting a number.

## Review output conventions

- Name the report `<board>-design-review.md` in the board directory.
- Record the designer's responses to findings in the report *and* fold the
  durable ones into the board's `.kicad-happy.json`, so the next review starts
  from the settled position instead of re-raising them.
- `analysis/` is gitignored by default (`track_in_git: false`), which keeps only
  the manifest. Prefer setting `"track_in_git": true` and deleting
  `analysis/.gitignore`: the analyzer JSON is slow to regenerate and
  `deep_review.json` — the hand-authored, evidence-gated findings the next
  review diffs against — is not regenerable at all. Git stores a full run in
  about 57 kB compressed. `analysis_cache.py` only recreates that `.gitignore`
  when `track_in_git` is false *and* the file is absent, so the deletion sticks.
- Helpers live once, in `BoardDesigns/kicad-helpers/`. Cite them from
  `deep_review.json` as `../kicad-helpers/<name>.py`; the gate checks the path
  resolves, so a stale citation quarantines the finding.
- **Every review of a board with an STM32-family part gets a pin-map table.**
  Generate it with `stm32_pinmap.py` and put the full table in the report — pin,
  port, net, what it connects to, function. It is the artefact firmware actually
  needs, and three things fall out of it every time:
  shared SPI buses (deselect becomes a firmware contract when two devices share
  SCK/MISO/MOSI with separate selects), BOOT0 straps carrying a pulled-up signal
  (needs an explicit option-byte write *and* read-back), and unused GPIOs (set
  analog/no-pull for lowest leakage; PA15 has a default pull-up and is worth
  setting explicitly). Mirror it into the board's `.kicad-happy.json` as
  `mating_design.host_pin_map` so firmware can consume it without re-deriving
  from the schematic — see `imutag-smps` and `CompassTag` for the shape.

  ```bash
  cd BoardDesigns/<board>
  PYTHONPATH=../kicad-helpers python3 ../kicad-helpers/stm32_pinmap.py
  ```

  **Include the alternate-function number for every peripheral signal**, and flag
  anything that cannot work. `stm32_pinmap.py` does this from
  `kicad-helpers/af_tables/<family>.json`, which is **generated from the
  `STM32_open_pin_data` submodule** — ST's own machine-readable pin data, the same
  source STM32CubeMX uses:

  ```bash
  git submodule update --init STM32_open_pin_data
  python3 BoardDesigns/kicad-helpers/af_tables/generate.py STM32U375KGUx
  ```

  `stm32u375.json` and `stm32l432.json` exist. Generate others as boards need them;
  the helper says so rather than guessing when a table is missing. The generator
  resolves ST's bracket filenames (`STM32L432K(B-C)Ux.xml`) and reads the GPIO IP
  modes file the part actually references.

  **Do not read AF tables out of the datasheet PDF.** A layout-text parse of the
  U375's Tables 22–23 scores 9/11 on spot checks — cells that wrap to a second line
  shift every column after them, so PB3 silently reads `SPI3_SCK` where the
  datasheet says `SPI1_SCK`. The XML has no such failure mode. (For the record, a
  careful by-hand read of the PDF did agree with ST's data on 48/54 entries, the six
  differences being label style only — `DEBUG_JTMS-SWDIO` vs `JTMS/SWDIO`. It is
  doable, just not worth doing.)

  Three checks come out of it, all silent failures that DRC and ERC pass:

  - **Peripheral-signal collisions** — two nets needing the same signal, which an
    STM32 routes to one pin at a time. On `imutag-smps` this found that the `/LPS_*`
    group is not a second SPI bus: PA11/PA12/PB3 need the same
    `SPI1_MISO`/`MOSI`/`SCK` as PA6/PA7/PA5, so firmware must remap at runtime or
    bit-bang one.
  - **Pin-number errors** — the symbol's pin numbering against the real package.
    This is the automated form of the "verify pinouts against the manufacturer,
    never the symbol" rule above; a wrong-pinout symbol passes DRC and ERC silently.
  - **What each pin gives up** — a pin whose AF0 is a `DEBUG_*` function forfeits it
    (PB3 loses TRACESWO, PB4 loses NJTRST).

  **Read additional functions, not just alternate functions.** The datasheet
  separates them: alternate functions are selected through `GPIOx_AFR`, additional
  functions through peripheral registers. `generate.py` captures both. Ignoring the
  second kind produced two wrong findings on `imutag-smps`: PC14 was called a plain
  GPIO that "costs you the LSE" when ST lists `RCC_OSC32_IN` on it — the RV-3028's
  32.768 kHz CLKOUT drives the **LSE in bypass mode**, giving a 1 PPM timebase with
  no crystal on the board, which LPTIM1 then divides onto PB4 (`LPTIM1_CH2`) to
  trigger the IMU in hardware while the CPU is stopped. A pin showing "no AF" is not
  a pin with no use.

  **The net name does not reveal intent.** Suffixes like `_SCK` or `_MISO` identify
  bus signals, but a net called `/LSM_TRG` driven by `LPTIM1_CH2` looks like a GPIO.
  The helper lists candidate peripheral functions for such pins under "confirm
  intent" — ask the designer rather than assuming. Better still, have the symbol
  declare KiCad **pin alternates** (the stock `MCU_ST_STM32*` libraries carry tens of
  thousands; the local `stm32u375` symbol has none) so the chosen function is
  recorded in the schematic and needs no guessing.

## Reviewing well — what went wrong last time

On 2026-09-01, three of ten findings were withdrawn as raised in error: mask
expansion, exposed-pad vias and paste, and a missing `.gbrjob`. All three came
from trusting a derivation from the files over the fact that **these boards have
been built and shipped**. Before raising anything about land geometry, paste,
mask, or a house-standard via:

- Ask whether this footprint or pattern has been fabricated before, and check
  sibling boards for the same pattern — it is usually a house convention.
- Check the fab outputs of boards that *were* built (`pcbway_production/`,
  `jlcpcb/`) rather than reasoning only from the current board file. Only
  BitTagNG, PresTag, CompassTag and BitTag have been fabbed.
- **Gerber `RoundRect` aperture macro corner coordinates are the centres of the
  corner circles, not the outer extents** — add 2r to width and height. Reading
  them as extents produced a bogus 25% exposed-pad paste figure where the true
  value is 63%, and nearly cost a working design a redesign.
