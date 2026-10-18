#!/bin/bash
# Graceful stop of the benchmark if the host runs low on memory (protects the other services): touches results/STOP.
cd ~/dev/lossy-bench || exit 1
while pgrep -f "[c]hain.sh|[s]cripts/run.py --phase" >/dev/null; do
  avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  if [ "$avail" -lt 2500 ]; then touch results/STOP; echo "$(date +%T) memguard: MemAvailable ${avail} MB < 2500, STOP set"; exit 0; fi
  sleep 10
done
