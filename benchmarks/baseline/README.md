# The performance baseline (baseline.json) is generated, never hand-written.
#
# It is environment-specific, so it must be produced where the gate runs:
#   - locally:  make perf-update
#   - in CI:    benchmarks.yaml seeds it from the main branch and caches it
#
# Until a baseline exists, scripts/perf.sh runs the benchmarks and exits 0 with
# a hint instead of failing. Commit a baseline.json here only if your team
# prefers the committed-baseline workflow over the CI-cached one.
