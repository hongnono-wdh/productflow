#!/usr/bin/env bash
# ProductFlow test runner.
# Runs the full stdlib-unittest suite (CLI + HTTP + e2e) from the skill root.
# Isolation is built into the tests (sandboxed HOME); this never touches the
# real ~/.productflow or ~/code. The e2e layer self-skips if playwright/chromium
# are unavailable.
#
# Usage:
#   tests/run.sh            # run everything
#   tests/run.sh -v         # verbose (per-test names)
set -euo pipefail

# Skill root = parent of this script's dir, regardless of where it's invoked.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"
cd "$SKILL_DIR"

PY="${PYTHON:-python3}"

echo "ProductFlow tests"
echo "  skill dir : $SKILL_DIR"
echo "  python    : $("$PY" --version 2>&1)"
echo "  command   : $PY -m unittest discover -s tests -p 'test_*.py' $*"
echo "------------------------------------------------------------"

# -W default surfaces ResourceWarnings so leaks don't hide. Pass through any
# extra args (e.g. -v) to unittest.
if "$PY" -W default -m unittest discover -s tests -p 'test_*.py' "$@"; then
  echo "------------------------------------------------------------"
  echo "RESULT: PASS"
else
  rc=$?
  echo "------------------------------------------------------------"
  echo "RESULT: FAIL (exit $rc)"
  exit "$rc"
fi
