#!/usr/bin/env bash
# Run every offline test suite (pure stdlib — no network, no third-party deps).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== agent (engine + onboarding) =="
( cd "$ROOT/agent" && python3 -m unittest discover -s tests )

echo "== server (linking) =="
( cd "$ROOT/server" && python3 -m unittest discover -s tests )

echo "== scripts (reminders) =="
( cd "$ROOT" && python3 -m unittest scripts.test_reminders )

echo "All suites passed."
