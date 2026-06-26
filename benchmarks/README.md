# Benchmarks

Micro-benchmarks for Flask's hot paths, used as a performance regression gate.

These are **not** part of the normal test run — `testpaths` in `pyproject.toml`
is limited to `tests/`, so `pytest` alone never collects this directory. They run
on demand via `pytest-benchmark` (in the `benchmarks` dependency group).

## What is measured

| File | Path |
|------|------|
| `test_routing_bench.py` | URL map matching, static and dynamic dispatch |
| `test_appctx_bench.py`  | app / request context push-pop |
| `test_json_bench.py`    | JSON encode/decode, `url_for` |

## Running locally

```bash
# run and compare against the committed baseline (10% threshold)
make perf
# or directly:
scripts/perf.sh

# refresh the baseline after an intentional, justified change
make perf-update
```

## How the gate works

1. `scripts/perf.sh` runs `pytest benchmarks/ --benchmark-json=<current>`.
2. `compare.py` matches benchmarks by name and compares median times.
3. If any benchmark is slower than `baseline/baseline.json` by more than
   `PERF_THRESHOLD` (default `0.10`), it exits non-zero.

In CI (`.github/workflows/benchmarks.yaml`) the gate blocks on `main` and is
advisory on branches, because shared runners are noisy. Treat a single failing
run as a prompt to re-run, not proof of a regression — confirm before updating
the baseline.

## Updating the baseline

Only update when a performance change is **intentional and reviewed**. Commit the
regenerated `baseline/baseline.json` in the same PR that justifies it, and note
the reason in `CHANGES.rst`.
