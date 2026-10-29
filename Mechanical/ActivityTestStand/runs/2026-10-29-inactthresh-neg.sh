#!/bin/bash
# 2026-10-29 inactivity-threshold sweep, third pass.  The first two snapped to
# +60 deg and then rocked to +A first, the same side as the reference the
# snap's return left, so about half the trials ran out the countdown before
# the rocking started.  Snap to -60 deg instead.  Amplitude sin A from level
# 0.6-1.5x T, angles padded 0.8 deg for the servo's shortfall.
cd ~/Research/hardware/Mechanical/ActivityTestStand
D=2026-10-29
for T in 0.10 0.20 0.30 0.50; do
  angles=$(python3 -c "import math; print(','.join(f'{math.degrees(math.asin(r*$T))+0.8:.2f}' for r in (0.6,0.8,0.9,1.0,1.1,1.25,1.5)))")
  name=$D-inthr$(echo $T | tr -d .)-neg
  echo "=== inactivity threshold $T g: angles $angles"
  python3 run_trial.py $name --act 0.6 --inact $T --samples 6 -- rock --angles=$angles \
    --reps 3 --shuffle 29 --bout 6 --reset-angle=-60 --move-ms 600 --poll 0.03 --rest 4 \
    2>&1 | grep -E "servo supply|records|Error|error|failed"
  python3 analyze_trials.py runs/$name
done
echo "=== sweep done"
