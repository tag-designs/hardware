#!/bin/bash
# 2026-10-29 activity-log checks, one run per format (re-run: the campaign passed bad format names)
cd ~/Research/hardware/Mechanical/ActivityTestStand
T() { python3 run_trial.py "$@" 2>&1 | grep -E "servo supply|records|Error|error|failed"; }
D=2026-10-29
for spec in SEC:BITTAG_BITPERSEC:60:0:0 MIN:BITTAG_BITSPERMIN:600:70:60 FOURMIN:BITTAG_BITSPERFOURMIN:1920:250:240 FIVEMIN:BITTAG_BITSPERFIVEMIN:2100:310:300; do
  IFS=: read name fmt rec long align <<< "$spec"
  now=$(date +%s); left=$(( rec - now % rec )); [ $left -lt $(( long + align + 90 )) ] && left=$(( left + rec ))
  mins=$(( (left + 150) / 60 )); [ $mins -lt 12 ] && mins=12
  bouts="2,5,10,20,40"; extra=""
  [ $long -gt 0 ] && bouts="$long,$bouts" && extra="--align $align"
  echo "=== bins $name: $mins min, bouts $bouts $extra"
  T $D-bins-$(echo $name | tr A-Z a-z) --act 0.25 --inact 0.15 --samples 6 --log-format $fmt -- bouts --bouts $bouts --period 50 --offset 0.5 --minutes $mins --move-ms 600 $extra
  python3 analyze_bins.py runs/$D-bins-$(echo $name | tr A-Z a-z)
done
echo "=== campaign done"
