#!/bin/bash
# After phases 2 and 3: the clip-free spectrum experiment (unless results/STOP is set).
cd ~/dev/lossy-bench || exit 1
while pgrep -f "scripts/[c]hain.sh" >/dev/null; do sleep 30; done
[ -e results/STOP ] && { echo "after_chain: STOP set, not starting"; exit 0; }
echo "after_chain: clipfree start $(date +%T)"
nice -n 19 python3 scripts/clipfree.py --workers 4 > results/clipfree.log 2>&1 < /dev/null
echo "after_chain: clipfree exited rc=$? $(date +%T)"
