#!/bin/bash
# 2026-10-29 P0 stand control: stock fw-v0.6, default bitpersec config, 2.5 V via
# joulescope_server.py.  Stand still at level, servo powered, torque off.
# Settle 75 s after start, then two 1200 s windows (charge/time), then download.
cd ~/Research/hardware/Mechanical/ActivityTestStand
R=~/Research/software/host/commandline-rs/target/release
SW=~/Research/software
JS=~/.venvs/joulescope/bin/python
P=runs/2026-10-29-p0
cp $SW/embedded/tools/power-configs/bittag-bitpersec.json $P-config.json
for i in $(seq 1 10); do out=$($R/tag-start --config $P-config.json --set-rtc --start-now 2>&1); rc=$?; [ $rc -eq 0 ] && break; sleep 2; done
echo "tag-start rc=$rc attempt $i"; echo "$out" | strings | grep -i -E "state|error" | tail -3
t0=$(date +%s)
python3 stand_profile.py still --unload --minutes 44 -o $P-stand.csv 2> $P-stand.log &
SP=$!
sleep $(( 75 - ($(date +%s) - t0) ))
for w in 1 2; do
  echo "== window $w from $(date -u +%FT%TZ)"
  $JS $SW/embedded/tools/joulescope_measure.py --use-server --duration 1200 --window 0.5 2>&1 | tail -2
done | tee $P-power.txt
wait $SP; cat $P-stand.log
cd ~/Downloads/host-tools-linux-x64/UltralightTags-3.2-linux-x86_64/tag_tools/bin
for i in $(seq 1 10); do ./tag-dwnld --stop -f text -o ~/Research/hardware/Mechanical/ActivityTestStand/$P-log.txt > /dev/null 2>&1 && break; sleep 2; done
cd ~/Research/hardware/Mechanical/ActivityTestStand
echo "download: $(grep -c ',SEC:' $P-log.txt) SEC records; nonzero: $(grep ',SEC:' $P-log.txt | grep -v -c 'SEC:0x0*$')"
