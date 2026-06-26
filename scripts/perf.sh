#!/usr/bin/env bash
# Run the micro-benchmark suite and compare it against the committed baseline.
#
# Usage:
#   scripts/perf.sh                 # compare against benchmarks/baseline/baseline.json
#   scripts/perf.sh --update        # overwrite the baseline with the current run
#
# Environment:
#   PERF_THRESHOLD=0.10   regression threshold as a fraction (default 0.10 = 10%)
#   PERF_ENFORCE=true     exit non-zero on regression (default: advisory, exit 0)
#   PERF_OUT=path.json    where to write the current run (default .perf-current.json)
set -euo pipefail

cd "$(dirname "$0")/.."

BASELINE="benchmarks/baseline/baseline.json"
CURRENT="${PERF_OUT:-.perf-current.json}"
THRESHOLD="${PERF_THRESHOLD:-0.10}"
ENFORCE="${PERF_ENFORCE:-false}"
REPORT="${PERF_REPORT:-.perf-report.md}"

echo "==> running benchmarks"
uv run --locked --no-default-groups --group benchmarks pytest benchmarks/ \
    --benchmark-json="$CURRENT" \
    --benchmark-min-rounds=5 \
    -q

if [[ "${1:-}" == "--update" ]]; then
    mkdir -p "$(dirname "$BASELINE")"
    uv run --locked --no-default-groups --group benchmarks \
        python benchmarks/trim_baseline.py "$CURRENT" "$BASELINE"
    echo "==> baseline updated: $BASELINE"
    exit 0
fi

if [[ ! -f "$BASELINE" ]]; then
    echo "no baseline at $BASELINE; create one with: scripts/perf.sh --update" >&2
    exit 0
fi

echo "==> comparing against baseline (threshold ${THRESHOLD}, enforce=${ENFORCE})"
set +e
uv run --locked --no-default-groups --group benchmarks python benchmarks/compare.py \
    "$BASELINE" "$CURRENT" --threshold "$THRESHOLD" --markdown "$REPORT"
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
    if [[ "$ENFORCE" == "true" ]]; then
        echo "==> regression detected and PERF_ENFORCE=true -> failing" >&2
        exit "$status"
    fi
    echo "==> regression detected but advisory (PERF_ENFORCE!=true) -> not failing" >&2
fi
exit 0
