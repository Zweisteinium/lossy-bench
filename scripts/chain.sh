#!/bin/bash
# After phase 1: reproduction check; only with 0 mismatches and all jobs complete start phase 2, then phase 3.
cd ~/dev/lossy-bench || exit 1
while pgrep -f "[s]cripts/run.py --phase 1" >/dev/null; do sleep 20; done
[ -e results/STOP ] && { echo "chain: STOP file present, not continuing"; exit 0; }
python3 scripts/analyze.py --partial > results/analysis_after_phase1.txt 2>&1 || { echo "chain: analyze failed"; exit 1; }
mism=$(($(wc -l < results/analysis/reproduction_mismatches.csv) - 1))
compl=$(grep -oP 'phase 1 \(originals\): \K[0-9]+' results/analysis_after_phase1.txt)
echo "chain: phase 1 complete jobs=$compl, reproduction mismatches=$mism"
[ "$mism" = 0 ] || { echo "chain: mismatches, phase 2 NOT started"; exit 0; }
[ "$compl" = 2500 ] || { echo "chain: phase 1 incomplete, phase 2 NOT started"; exit 0; }
echo "chain: starting phase 2 $(date +%T)"
python3 scripts/run.py --phase 2 --workers 5 --lp-threads 2 > results/phase2.log 2>&1 < /dev/null
echo "chain: phase 2 exited rc=$? $(date +%T)"
[ -e results/STOP ] && { echo "chain: STOP file present, phase 3 not started"; exit 0; }
python3 scripts/run.py --phase 3 --workers 5 --lp-threads 2 > results/phase3.log 2>&1 < /dev/null
echo "chain: phase 3 exited rc=$? $(date +%T)"
