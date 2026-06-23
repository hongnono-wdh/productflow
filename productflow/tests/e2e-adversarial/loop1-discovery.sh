#!/bin/sh
# Loop 1 — continuous adversarial DISCOVERY.
# Each iteration = one rotated user persona running the harness against its OWN
# isolated sandbox server + browser (multi-instance; never touches :7717).
# Accumulates findings (status=open) in findings/findings.jsonl. NEVER fixes code.
# Stop with:  touch tests/e2e-adversarial/findings/.stop
cd "$(dirname "$0")" || exit 1
mkdir -p findings
rm -f findings/.stop
echo "[loop1] discovery started $(date)" >> findings/discovery.log
i=0
while [ ! -f findings/.stop ]; do
  python3 harness.py --persona auto >> findings/discovery.log 2>&1
  i=$((i + 1))
  [ -f findings/.stop ] && break
  sleep 180   # ~one persona every few minutes; keeps load light
done
echo "[loop1] stopped after $i runs $(date)" >> findings/discovery.log
