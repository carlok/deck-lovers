#!/usr/bin/env bash
# run_tests.sh — build test images and run both test suites inside containers
set -euo pipefail

COMPOSE=$(command -v podman-compose 2>/dev/null || command -v docker-compose 2>/dev/null || echo "docker compose")
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

SUITE="${1:-all}"   # all | converter | server

mkdir -p test-results

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
  converter) run_suite test-converter ;;
  server)    run_suite test-server    ;;
  all)
    run_suite test-converter
    run_suite test-server
    ;;
  *)
    echo "Usage: $0 [all|converter|server]"
    exit 1
    ;;
esac

echo
echo "✓ HTML coverage reports → test-results/converter/  test-results/server/"
