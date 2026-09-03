import glob
import json
import os
import sys


def load(kind):
    """Newest analyzer run of `kind`, with a loud warning if it predates the design.

    The analyzer JSON is a snapshot. Running a helper against a stale run reports
    the PREVIOUS revision of the board and looks entirely plausible - on
    imutag-smps a run 8 days old still contained a load switch that had been
    removed. Regenerate with:

        python3 <kicad-skill>/scripts/analyze_schematic.py <board>.kicad_sch --analysis-dir analysis/
    """
    runs = sorted(glob.glob(f'analysis/*/{kind}.json'))
    if not runs:
        sys.exit(f"no analysis/*/{kind}.json here - run the analyzer first, "
                 f"from the board's own directory")
    newest = runs[-1]
    src = {'schematic': '*.kicad_sch', 'pcb': '*.kicad_pcb'}.get(kind)
    if src:
        design = [f for f in glob.glob(src) if 'panel' not in f and '-back' not in f]
        if design:
            age = os.path.getmtime(design[0]) - os.path.getmtime(newest)
            if age > 60:
                print(f"!! STALE ANALYSIS: {newest} predates {design[0]} by "
                      f"{age / 3600:.1f} h.\n"
                      f"!! Anything below describes the OLDER design. Re-run the "
                      f"analyzer before trusting it.\n", file=sys.stderr)
    return json.load(open(newest))
