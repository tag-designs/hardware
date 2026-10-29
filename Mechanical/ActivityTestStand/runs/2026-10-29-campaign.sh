#!/bin/bash
# 2026-10-29 non-power test campaign; results in runs/, summaries on stdout
cd ~/Research/hardware/Mechanical/ActivityTestStand
T() { python3 run_trial.py "$@" 2>&1 | grep -E "servo supply|records|Error|error|failed"; }
D=2026-10-29
echo "=== nudge (out and back)"; T $D-nudge --act 0.35 --inact 0.15 --samples 9 -- nudge --angles 3,5.7,7.5,10,11.5,17.5 --reset-angle=-40 --move-ms 250 --hold 0 --delay 0.3 --reps 3 --shuffle 4 --rest 4
python3 analyze_trials.py runs/$D-nudge
echo "=== nudge (held 3 s)"; T $D-nudge-hold --act 0.35 --inact 0.15 --samples 9 -- nudge --angles 5.7,11.5,17.5 --reset-angle=-40 --move-ms 250 --hold 3 --delay 0.3 --reps 3 --shuffle 5 --rest 4
python3 analyze_trials.py runs/$D-nudge-hold
echo "=== blip"; T $D-blip --act 0.35 --inact 0.15 --samples 3 -- blip --angles 22,24,26,28,32,40 --move-ms 150 --reps 5 --shuffle 6 --rest 2 --poll 0.01
python3 analyze_trials.py runs/$D-blip --threshold 0.35 | tail -9
echo "=== gaps fine, 6 samples"; T $D-inact6-fine --act 0.25 --inact 0.15 --samples 6 -- gaps --gaps 0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3 --reps 3 --shuffle 7 --bout 2 --move-ms 600 --rest 3
python3 analyze_trials.py runs/$D-inact6-fine
echo "=== gaps fine, 9 samples"; T $D-inact9-fine --act 0.25 --inact 0.15 --samples 9 -- gaps --gaps 0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6 --reps 3 --shuffle 8 --bout 2 --move-ms 600 --rest 3
python3 analyze_trials.py runs/$D-inact9-fine
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
