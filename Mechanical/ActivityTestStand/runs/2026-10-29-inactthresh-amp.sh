#!/bin/bash
# 2026-10-29 inactivity-threshold sweep, second pass: the first (peak-to-peak
# 0.5-2x T) never held the tag active, consistent with the reference moving to
# mid-swing.  Here the amplitude sin A from level is 0.9-2x T.
cd ~/Research/hardware/Mechanical/ActivityTestStand
D=2026-10-29
for T in 0.10 0.20 0.30 0.50; do
  angles=$(python3 -c "import math; print(','.join(f'{math.degrees(math.asin(r*$T))+0.8:.2f}' for r in (0.9,1.0,1.1,1.25,1.5,2.0) if r*$T<=0.8))")
  name=$D-inthr$(echo $T | tr -d .)-amp
  echo "=== inactivity threshold $T g: angles $angles"
  python3 run_trial.py $name --act 0.6 --inact $T --samples 6 -- rock --angles=$angles \
    --reps 3 --shuffle 29 --bout 6 --reset-angle 60 --move-ms 600 --poll 0.03 --rest 4 \
    2>&1 | grep -E "servo supply|records|Error|error|failed"
  python3 analyze_trials.py runs/$name
done
echo "=== sweep done"
