#!/bin/bash
# 2026-10-29 P4, discrete-Pareto workload (the user's sampler): bouts of +/-30 deg
# swings, lengths 1-30 s drawn once per still second, active 20% of the time.
# Stock fw-v0.6, default bitpersec config, 2.5 V via joulescope_server.py.
cd ~/Research/hardware/Mechanical/ActivityTestStand
R=~/Research/software/host/commandline-rs/target/release
OLD=~/Downloads/host-tools-linux-x64/UltralightTags-3.2-linux-x86_64/tag_tools/bin
SW=~/Research/software
JS=~/.venvs/joulescope/bin/python
P=runs/2026-10-29-p4-pareto
cp $SW/embedded/tools/power-configs/bittag-bitpersec.json $P-config.json
for i in $(seq 1 10); do out=$($R/tag-reset --set-rtc 2>&1); rc=$?; [ $rc -eq 0 ] && break; sleep 2; done
echo "tag-reset rc=$rc attempt $i"; echo "$out" | strings | grep "Final state"
for i in $(seq 1 10); do out=$($R/tag-start --config $P-config.json --set-rtc --start-now 2>&1); rc=$?; [ $rc -eq 0 ] && break; sleep 2; done
echo "tag-start rc=$rc attempt $i"; echo "$out" | strings | grep -i -E "state|error" | tail -2
t0=$(date +%s)
python3 stand_profile.py pareto --duty 0.2 --seed 1 --angle 30 --move-ms 600 --minutes 44 \
  -o $P-stand.csv 2> $P-stand.log &
SP=$!
sleep $(( 75 - ($(date +%s) - t0) ))
for w in 1 2; do
  echo "== window $w from $(date -u +%FT%TZ)"
  $JS $SW/embedded/tools/joulescope_measure.py --use-server --duration 1200 --window 0.5 2>&1 | tail -2
done | tee $P-power.txt
wait $SP; cat $P-stand.log
cd $OLD
for i in $(seq 1 10); do ./tag-dwnld --stop -f text -o ~/Research/hardware/Mechanical/ActivityTestStand/$P-log.txt > /dev/null 2>&1 && break; sleep 2; done
echo "download done (attempt $i)"
