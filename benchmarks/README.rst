# Performance benchmarks

In-process micro-benchmarks that measure Flask's *framework* request-dispatch
overhead. They are deterministic by construction (no network, no real WSGI
server, GC disabled around the measured loop, median of 200 iterations) so
they can serve as a CI regression gate without the flakiness of a real load
test.

## Run

```bash
# from repo root, after `uv sync` (or inside `tox run -e perf`)
tox run -e perf
# or directly:
uv run --group tests python benchmarks/perf_check.py
```

The gate compares each benchmark's current median against the committed
`baseline.json` and prints a Markdown table (also written to
`$GITHUB_STEP_SUMMARY` in CI).

| benchmark | what it measures |
|---|---|
| `core_request_roundtrip` | full request round-trip on a hello-world app via the test client |
| `routing_match` | URL-rule match only, bypassing full dispatch |
| `template_render` | render a small Jinja template |

## Gate semantics

- **Phase 1 (current): advisory.** Any regression, including a "hard" one, only
  prints a warning and exits 0, so a flaky runner never blocks a PR.
- **Phase 3+: blocking.** Drop `--advisory` in CI. Benchmarks listed in
  `thresholds.hard_regression` (`core_request_roundtrip`) that regress beyond
  `hard_regression_ratio` (default 1.25x) fail the build. Promote only after
  recalibrating `baseline.json` across >= 10 CI runs to establish a variance
  budget.

## Recalibrate

```bash
python benchmarks/perf_check.py --update-baseline   # commit the new baseline
```

## Real-world load testing

These benchmarks isolate framework cost for the regression gate. To profile a
running server under real concurrency use `wrk` or `locust` against a served
app (for example the OpenTelemetry example under `examples/observability/`):

```bash
# serve an app, then:
wrk -t4 -c64 -d20s http://127.0.0.1:5000/
```

That is out of scope for the CI gate but useful for production profiling.
