#!/usr/bin/env bash
# Run the micro-benchmark suite and compare it against the committed baseline.
#
# Usage:
#   scripts/perf.sh                 # compare against benchmarks/baseline/baseline.json
#   scripts/perf.sh --update        # overwrite the baseline with the current run
#   PERF_THRESHOLD=0.10 scripts/perf.sh   # fail if any path regresses > 10%
set -euo pipefail

cd "$(dirname "$0")/.."

BASELINE="benchmarks/baseline/baseline.json"
CURRENT="${PERF_OUT:-.perf-current.json}"
THRESHOLD="${PERF_THRESHOLD:-0.10}"

echo "==> running benchmarks"
uv run --group benchmarks pytest benchmarks/ \
    --benchmark-json="$CURRENT" \
    --benchmark-min-rounds=5 \
    -q

if [[ "${1:-}" == "--update" ]]; then
    mkdir -p "$(dirname "$BASELINE")"
    cp "$CURRENT" "$BASELINE"
    echo "==> baseline updated: $BASELINE"
    exit 0
fi

if [[ ! -f "$BASELINE" ]]; then
    echo "no baseline at $BASELINE; create one with: scripts/perf.sh --update" >&2
    exit 0
fi

echo "==> comparing against baseline (threshold ${THRESHOLD})"
uv run --group benchmarks python benchmarks/compare.py \
    "$BASELINE" "$CURRENT" --threshold "$THRESHOLD"
