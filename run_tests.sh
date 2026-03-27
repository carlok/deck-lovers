#!/usr/bin/env bash
# run_tests.sh — build and run all test suites inside containers
#
# Usage:
#   ./run_tests.sh              # all four suites
#   ./run_tests.sh converter    # Python tests for md2html
#   ./run_tests.sh converter-js # Jest tests for slides.pure.js
#   ./run_tests.sh server       # Python tests for server.py
#   ./run_tests.sh server-js    # Jest tests for audience.pure.js
#   ./run_tests.sh py           # both Python suites
#   ./run_tests.sh js           # both Jest suites
set -euo pipefail

COMPOSE="podman compose"
if ! command -v podman >/dev/null 2>&1 || ! podman info >/dev/null 2>&1; then
  echo "ERROR: Podman is required. Install Podman and retry." >&2
  exit 1
fi
if ! podman compose version >/dev/null 2>&1; then
  echo "ERROR: 'podman compose' is required. Install podman-compose plugin and retry." >&2
  exit 1
fi
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

SUITE="${1:-all}"

mkdir -p test-results
chmod -R 777 test-results || true

run_suite() {
  local svc="$1"
  echo
  echo "══════════════════════════════════════════"
  echo "  Building & running: $svc"
  echo "══════════════════════════════════════════"
  $COMPOSE build "$svc"
  $COMPOSE run --rm --remove-orphans "$svc"
}

case "$SUITE" in
  converter)    run_suite test-converter    ;;
  converter-js) run_suite test-converter-js ;;
  server)       run_suite test-server       ;;
  server-js)    run_suite test-server-js    ;;
  py)
    run_suite test-converter
    run_suite test-server
    ;;
  js)
    run_suite test-converter-js
    run_suite test-server-js
    ;;
  all)
    run_suite test-converter
    run_suite test-converter-js
    run_suite test-server
    run_suite test-server-js
    ;;
  *)
    echo "Usage: $0 [all|py|js|converter|converter-js|server|server-js]"
    exit 1
    ;;
esac

echo
echo "✓ Coverage reports → test-results/"
echo "  converter/      server/         (Python — HTML)"
echo "  converter-js/   server-js/      (Jest   — HTML)"
