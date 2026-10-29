#!/usr/bin/env python3
"""Run one configured BitTag edge-log trial on the stand, end to end.

  1. tag-reset --set-rtc     stop if needed, erase, sync the clock
  2. tag-start --config      the ADXL362 settings given here, starting now
  3. stand_profile.py        the motion, with every argument after "--"
  4. edge_log.py             dump and decode SRAM2 (under reset)
  5. tag-dwnld --stop        the tag's own binned log, as text

Files go to runs/<name>-{config.json,stand.csv,sram2.txt,edges.csv,log.txt}.
Every tag tool is retried: attaches fail intermittently with status=0x81
(SERVO-AND-TEST-PLAN.md section 9).  The tag must be running the edge-log
build.

  python3 run_trial.py 2026-10-29-act035 --act 0.35 --inact 0.15 --samples 3 \\
      -- steps --angles 16.3,18.4 --reps 3 --move-ms 1500
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
# Rust tools carry the DBG_SLEEP attach fix; tag-dwnld needs the C++ writer.
RUST = Path(os.environ.get("TAG_RUST_BIN", Path.home() /
            "Research/software/host/commandline-rs/target/release"))
OLD = Path(os.environ.get("TAG_TOOLS_BIN", Path.home() /
           "Downloads/host-tools-linux-x64/UltralightTags-3.2-linux-x86_64/tag_tools/bin"))


def tag_tool(cmd, attempts=10):
    for n in range(1, attempts + 1):
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout
        time.sleep(2)
    sys.exit(f"{Path(cmd[0]).name} failed {attempts} times:\n{p.stdout}{p.stderr}")


def config(act, inact, samples, log_format):
    return {
        "tag_type": "BITTAG_LE",
        "active_interval": {"start_epoch": 0, "end_epoch": 2147483647},
        "hibernate": [{"start_epoch": 0, "end_epoch": 0}] * 2,
        "bittag_log": log_format,
        "adxl362": {"act_thresh_g": act, "inact_thresh_g": inact,
                    "inactive_sec": samples},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("name", help="file prefix in runs/, e.g. 2026-10-29-act035")
    ap.add_argument("--act", type=float, required=True, help="activity threshold, g")
    ap.add_argument("--inact", type=float, required=True, help="inactivity threshold, g")
    ap.add_argument("--samples", type=int, required=True,
                    help="inactivity time in samples (BitTag's inactive_sec)")
    ap.add_argument("--log-format", default="BITTAG_BITPERSEC")
    ap.epilog = "Then --, then the stand_profile.py arguments, without -o."
    argv = sys.argv[1:]
    if "--" not in argv:
        ap.error("give the stand profile after --")
    cut = argv.index("--")
    a, prof = ap.parse_args(argv[:cut]), argv[cut + 1:]
    if not prof:
        ap.error("give the stand profile after --")

    RUNS.mkdir(exist_ok=True)
    out = {k: RUNS / f"{a.name}-{k}" for k in
           ("config.json", "stand.csv", "sram2.txt", "edges.csv", "log.txt")}
    out["config.json"].write_text(json.dumps(
        config(a.act, a.inact, a.samples, a.log_format), indent=1) + "\n")

    tag_tool([RUST / "tag-reset", "--set-rtc"])
    started = tag_tool([RUST / "tag-start", "--config", out["config.json"],
                        "--set-rtc", "--start-now"])
    print(next((l for l in started.splitlines() if l.startswith("State")),
               "started"), file=sys.stderr)

    subprocess.run([sys.executable, HERE / "stand_profile.py", *prof,
                    "-o", out["stand.csv"]], check=True)
    subprocess.run([sys.executable, HERE / "edge_log.py",
                    "--save-dump", out["sram2.txt"], "-o", out["edges.csv"]],
                   check=True)
    tag_tool([OLD / "tag-dwnld", "--stop", "-f", "text", "-o", out["log.txt"]])
    print(f"{a.name}: files in {RUNS}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
