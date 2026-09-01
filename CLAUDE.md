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
