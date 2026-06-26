# Flask Performance Benchmarks

Performance benchmarks for Flask, using `pytest-benchmark`.

## Running Locally

```bash
# Install benchmark dependencies
pip install Flask pytest-benchmark

# Run all benchmarks
pytest benchmarks/ --benchmark-only --benchmark-min-rounds=10 -v

# Run specific benchmark file
pytest benchmarks/test_routing.py --benchmark-only -v

# Generate JSON output
pytest benchmarks/ --benchmark-only --benchmark-json=benchmarks/output.json
```

## Benchmark Categories

| File | What It Measures |
|------|-----------------|
| `test_app_creation.py` | Flask app instantiation and configuration |
| `test_routing.py` | URL matching and route dispatch |
| `test_request_cycle.py` | Full request lifecycle with hooks |
| `test_templating.py` | Jinja2 template rendering |
| `test_json.py` | JSON serialization and jsonify |
| `test_session.py` | Session signing, serialization, deserialization |
| `test_signals.py` | Blinker signal emission overhead |
| `test_overhead.py` | Observability module overhead (requires `Flask[observability]`) |

## Baseline

The `baseline.json` file is automatically updated on every push to `main`.
It serves as the reference point for regression detection in CI.

## Regression Detection

CI compares each PR's benchmark results against the baseline:

- **> 10% slower**: Warning comment on PR (non-blocking)
- The baseline is updated weekly via the `update-baseline` job

## Interpreting Results

Each benchmark reports:

- **ops/sec**: Operations per second (higher = better)
- **mean**: Average time per operation in seconds
- **stddev**: Standard deviation (lower = more consistent)
- **rounds**: Number of measurement rounds

## Tips for Reducing Noise

- Run on a quiet machine with no other heavy processes
- Use `--benchmark-min-rounds=20` for more stable results
- CI runs use dedicated GitHub Actions runners for consistency
