#!/bin/bash
# 2026-10-29 inactivity-threshold sweep: after a snap wakes the tag, rock it
# +/-A about level for 6 s; peak-to-peak change 2 sin A at 0.5-2x the
# threshold.  Commanded angles are padded 0.8 deg for the servo's shortfall;
# analyze_trials.py scores on the measured peak-to-peak.
cd ~/Research/hardware/Mechanical/ActivityTestStand
D=2026-10-29
for T in 0.10 0.20 0.30 0.50; do
  angles=$(python3 -c "import math; print(','.join(f'{math.degrees(math.asin(k*$T/2))+0.8:.2f}' for k in (0.5,0.75,0.9,1.0,1.1,1.25,1.5,2.0)))")
  name=$D-inthr$(echo $T | tr -d .)
  echo "=== inactivity threshold $T g: angles $angles"
  python3 run_trial.py $name --act 0.6 --inact $T --samples 6 -- rock --angles=$angles \
    --reps 3 --shuffle 29 --bout 6 --reset-angle 60 --move-ms 600 --poll 0.03 --rest 4 \
    2>&1 | grep -E "servo supply|records|Error|error|failed"
  python3 analyze_trials.py runs/$name
done
echo "=== sweep done"
