# Benchmarks

Micro-benchmarks for Flask's hot paths, used as a performance regression gate.

These are **not** part of the normal test run — `testpaths` in `pyproject.toml`
is limited to `tests/`, so `pytest` alone never collects this directory. They run
on demand via `pytest-benchmark` (in the `benchmarks` dependency group). The
*gate logic* itself is unit-tested in `tests/test_perf_compare.py`.

## What is measured

| File | Path |
|------|------|
| `test_routing_bench.py` | URL map matching, static and dynamic dispatch |
| `test_appctx_bench.py`  | app / request context push-pop |
| `test_json_bench.py`    | JSON encode/decode, `url_for` |

## Running locally

```bash
# run and compare against the committed baseline (advisory by default)
make perf
# or directly:
scripts/perf.sh

# enforce the gate locally (exit non-zero on regression)
PERF_ENFORCE=true scripts/perf.sh

# refresh the local baseline after an intentional, justified change
make perf-update
```

## Environment consistency and noise

Absolute timings depend on the machine. **A baseline produced on one host is not
comparable to a run on another** — comparing CI numbers against a laptop-built
baseline is meaningless. Two consequences:

1. **CI compares same-environment.** `benchmarks.yaml` checks out the base commit
   into a worktree and benchmarks it on the *same runner* as the PR head, then
   compares the two. The committed `baseline/baseline.json` is only a local
   convenience and a last-resort advisory fallback.
2. **Micro-benchmarks are noisy.** `compare.py` reports each benchmark's relative
   standard deviation (the `noise` column). On shared runners this can exceed
   100% for sub-microsecond operations. To avoid false alarms:
   - comparison uses the **median**, not the mean;
   - `--ignore-within-noise` suppresses any "regression" smaller than the two
     runs' combined noise;
   - the gate is **advisory by default** and only blocks when `PERF_ENFORCE` is
     set (a dedicated, low-noise runner is recommended before enforcing).

## How the gate works

1. Benchmark the head and the base commit (same runner) → two JSON files.
2. `compare.py` matches by name, compares medians, and reports the delta and the
   noise per benchmark, writing a Markdown table to the job summary.
3. If any benchmark regresses beyond `PERF_THRESHOLD` (default `0.10`) *and*
   beyond the combined noise, it exits non-zero. Whether that fails the job is
   controlled by `PERF_ENFORCE` (repository variable or `workflow_dispatch`
   input).

## Updating the committed baseline

`baseline/baseline.json` is a trimmed (~KB) summary produced by
`benchmarks/trim_baseline.py`. Only refresh it when a performance change is
**intentional and reviewed**; commit it in the same PR and note the reason in
`CHANGES.rst`.
