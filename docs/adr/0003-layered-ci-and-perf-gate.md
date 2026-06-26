# 0003 — Layered CI with a performance regression gate

- Status: Accepted
- Date: 2026-06-23

## Context

The existing `tests.yaml` runs a broad compatibility matrix (CPython
3.10–3.14, free-threaded 3.14t, PyPy, Windows, macOS, minimum and development
dependency versions). It is thorough but slow, and every push pays the full
cost before a contributor learns about a trivial lint or smoke failure. Two
capabilities were missing:

1. A **fast feedback lane** that fails in seconds on formatting/lint/smoke
   problems, before the heavy matrix spins up.
2. A **performance regression gate** — Flask has no defence against a change
   that silently makes request dispatch slower.

## Decision

CI is layered:

- **Fast lane** (`ci-fast.yaml`): `ruff check` + `ruff format --check` + a smoke
  subset of the test suite on a single interpreter, with
  `cancel-in-progress`. Sub-two-minute signal. Also hosts the `release-guard`
  job (see ADR 0005).
- **Full matrix** (`tests.yaml`): unchanged — remains the source of truth for
  compatibility, plus the `typing` job.
- **Performance gate** (`benchmarks.yaml`): on PRs it runs the `benchmarks/`
  suite with `pytest-benchmark`. Because absolute timings are
  environment-specific, it does **not** compare against a stored cross-machine
  baseline; instead it benchmarks the base commit in a worktree on the *same
  runner* and compares head-vs-base. `compare.py` reports per-benchmark noise
  (relative std-dev), compares medians, and with `--ignore-within-noise`
  suppresses deltas smaller than the runs' combined noise. Blocking is
  controlled by the `PERF_ENFORCE` repository variable (advisory by default,
  since shared runners are noisy). The gate logic is unit-tested in
  `tests/test_perf_compare.py`.
- **Failure attribution**: `tests.yaml` gains an `if: failure()` step that runs
  `scripts/triage_failures.py`, mapping each failing test to its most recent
  author/module via `git blame` and writing a grouped `$GITHUB_STEP_SUMMARY`.

The matrix is *not* duplicated across these workflows; `paths`/`paths-ignore`
and shared `concurrency` groups keep runs from overlapping.

## Consequences

- Good: contributors get near-instant signal; perf regressions are caught
  mechanically against a same-environment baseline; triage of red builds is
  faster.
- Cost: benchmark numbers are noisy on shared runners — mitigated by
  same-runner comparison, median + noise-aware thresholding, and keeping the
  gate advisory (`PERF_ENFORCE=false`) until a dedicated runner is available.

## Alternatives considered

- **airspeed-velocity (asv)** for long-term perf history: more capable but
  heavier to host and maintain; revisit if trend analysis becomes a need.
- **End-to-end HTTP load testing (locust/wrk)** as the gate: too
  environment-sensitive for a hard CI gate; better suited to the observability
  example for manual baselining.
- **Folding the fast lane into `tests.yaml`**: keeps one file but loses the
  early-exit property and complicates the matrix.
