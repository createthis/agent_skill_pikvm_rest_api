#!/usr/bin/env bash
# Run the pikvm-rest-api test suite.
#
#   bash pikvm-rest-api/tests/run_tests.sh            # everything
#   bash pikvm-rest-api/tests/run_tests.sh python     # just the Python unit tests
#   bash pikvm-rest-api/tests/run_tests.sh bash       # just the pikvm.sh tests
#
# Dependencies: bash 4+, curl, python3, and Pillow (pip install pillow) for
# test_zoom.py. jq is optional — pikvm.sh works without it, and the tests
# don't require it either.
#
# The suite runs entirely offline: pikvm.sh is exercised against a local
# mock KVMD server (tests/mock_kvm_server.py) on 127.0.0.1. No real KVM,
# network, or credentials are needed; any PIKVM_* environment variables of
# yours are ignored (the bash tests run in a scrubbed environment).
set -u

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/.." && pwd)"
MODE="${1:-all}"

overall=0

run_python() {
  echo "=== Python unit tests (kvmcoords.py, zoom.py) ==="
  if command -v python3 >/dev/null 2>&1; then
    if (cd "$REPO_ROOT" && python3 -m unittest discover -s pikvm-rest-api/tests -p 'test_*.py' -v); then
      echo "PYTHON: PASS"
    else
      echo "PYTHON: FAIL"
      overall=1
    fi
  else
    echo "SKIP python tests: python3 not found"
    overall=1
  fi
}

run_bash() {
  echo
  echo "=== Bash integration tests (pikvm.sh vs mock KVMD server) ==="
  if bash "$TESTS_DIR/test_pikvm.sh"; then
    echo "BASH: PASS"
  else
    echo "BASH: FAIL"
    overall=1
  fi
}

case "$MODE" in
  all)    run_python; run_bash ;;
  python) run_python ;;
  bash)   run_bash ;;
  *) echo "usage: $0 [all|python|bash]" >&2; exit 2 ;;
esac
exit "$overall"
