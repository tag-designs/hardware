#!/usr/bin/env python3
"""Read a BitTag edge-log build's AWAKE record from SRAM2 and decode it.

The stand build of BitTag (software repo, `make BITTAG_EDGE_LOG=1`) records
the RTC time and ADXL362 AWAKE level on every RUNNING wake into a ring at
0x10000000 (embedded/tags/BitTag/inc/edge_log.h).  Every AWAKE edge wakes the
tag, so a change of level between consecutive records is an edge; the
minute-alarm wakes repeat the level.

Read it after the run.  The dump uses STM32CubeProgrammer, connecting under
reset, so it ends the run like any attach -- never read a run you still want.
Reset leaves SRAM2 intact.  The first connect to a sleeping tag often fails,
so it retries.

  python3 edge_log.py -o edges.csv              # dump over SWD and decode
  python3 edge_log.py --dump sram2.txt -o edges.csv   # decode a saved dump
"""

import argparse
import csv
import datetime
import re
import os
import shutil
import struct
import subprocess
import sys
import time

BASE = 0x10000000
WORDS = 4096                      # all 16 KB of SRAM2
MAGIC = 0x4C474445                # "EDGL"
PROGRAMMER = (shutil.which("STM32_Programmer_CLI") or
              os.path.expanduser("~/Software/STM32CubeProgrammer/bin/STM32_Programmer_CLI"))
KINDS = {0: "wake", 1: "start"}


def dump_swd(programmer, attempts=5):
    for _ in range(attempts):
        out = subprocess.run(
            [programmer, "-c", "port=SWD", "mode=UR", "-r32", hex(BASE),
             hex(4 * WORDS)], capture_output=True, text=True).stdout
        if f"{BASE:#x} :" in out:
            return out[out.index(f"{BASE:#x} :"):]
        time.sleep(2)
    sys.exit(f"could not read SRAM2 in {attempts} attempts:\n{out}")


def parse_words(text):
    # 8-digit hex words, with or without 0x; skip "address :" prefixes and
    # anything before the first one (the programmer's banner)
    m = re.search(rf"{BASE:#x}\s*:", text)
    text = text[m.start():] if m else text
    words = [int(w, 16) for w in
             re.findall(r"(?<![0-9a-fA-Fx])(?:0x)?([0-9a-fA-F]{8})\b(?!\s*:)", text)]
    if len(words) < 4:
        sys.exit(f"dump has {len(words)} words; expected {WORDS}")
    return words


def decode(words):
    magic, count, slots = words[0], words[1], words[2]
    if magic != MAGIC:
        sys.exit(f"no edge log at {BASE:#x} (magic {magic:#010x}): "
                 "not the edge-log build, never started, or SRAM2 lost power")
    n = min(count, slots)
    first = count - n
    recs = []
    for k in range(first, count):
        i = 4 + 2 * (k % slots)
        sec = struct.unpack("<i", struct.pack("<I", words[i]))[0]
        info = words[i + 1]
        recs.append({"seq": k, "t": sec + (info & 0x3FF) / 1000.0,
                     "level": (info >> 16) & 1,
                     "kind": KINDS.get(info >> 24, str(info >> 24))})
    return count, slots, recs


def utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(
        timespec="milliseconds")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dump", help="decode this saved dump instead of reading SWD")
    ap.add_argument("--save-dump", help="also write the raw dump here")
    ap.add_argument("--programmer", default=PROGRAMMER, help="STM32_Programmer_CLI path")
    ap.add_argument("-o", "--output", help="CSV of records (default stdout)")
    a = ap.parse_args()

    text = open(a.dump).read() if a.dump else dump_swd(a.programmer)
    if a.save_dump:
        open(a.save_dump, "w").write(text)
    count, slots, recs = decode(parse_words(text))

    out = open(a.output, "w", newline="") if a.output else sys.stdout
    w = csv.writer(out)
    w.writerow(["seq", "utc", "unix", "kind", "level", "edge", "since_edge_s"])
    prev, last_edge = None, None
    edges = []
    for r in recs:
        edge = ""
        if prev is not None and r["level"] != prev:
            edge = "rise" if r["level"] else "fall"
            edges.append((r["t"], edge))
        since = f"{r['t'] - last_edge:.3f}" if edge and last_edge is not None else ""
        if edge:
            last_edge = r["t"]
        w.writerow([r["seq"], utc(r["t"]), f"{r['t']:.3f}", r["kind"],
                    r["level"], edge, since])
        prev = r["level"]
    if a.output:
        out.close()

    lost = f", oldest {count - slots} overwritten" if count > slots else ""
    print(f"{count} records{lost}; {sum(e == 'rise' for _, e in edges)} rises, "
          f"{sum(e == 'fall' for _, e in edges)} falls", file=sys.stderr)
    for (t0, e0), (t1, e1) in zip(edges, edges[1:]):
        if e0 == "rise" and e1 == "fall":
            print(f"  active {utc(t0)} for {t1 - t0:.3f} s", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
