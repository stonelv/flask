# ADR-005: Performance Baseline Management

## Status

Accepted

## Context

Flask had no systematic performance tracking, leading to:
- Undetected performance regressions
- Difficulty identifying when performance degraded
- No historical performance data
- User complaints about slowdowns

## Decision

Implement continuous performance monitoring with:

1. **Benchmark suite**: Comprehensive tests for all critical paths
2. **Baseline tracking**: Historical performance data in git
3. **Regression detection**: Automatic alerts for >10% slowdowns
4. **CI integration**: Prevent merging performance regressions

### Regression Threshold

**10% regression threshold** chosen because:
- Detects meaningful slowdowns (not noise)
- Allows for normal variance (±5%)
- Prevents "death by a thousand cuts"
- Actionable (worth investigating)

### Baseline Update Strategy

Baselines update on:
- **Main branch merges**: Automatic update
- **Release tags**: Tagged snapshot
- **Manual update**: Developer-initiated when acceptable

## Implementation

### Benchmark Structure

```
benchmarks/
├── conftest.py              # Shared fixtures
├── test_app_creation.py     # Flask() instantiation
├── test_routing.py          # URL matching
├── test_request_cycle.py    # Full request lifecycle
├── test_templating.py       # Jinja2 rendering
├── test_json.py             # JSON serialization
├── test_session.py          # Session operations
├── test_signals.py          # Signal dispatch
├── test_overhead.py         # Observability overhead
└── baseline.json            # Performance baseline
```

### Running Benchmarks

```bash
# Install dependencies
pip install Flask[benchmarks]

# Run all benchmarks
pytest benchmarks/ --benchmark-only

# Compare against baseline
pytest benchmarks/ --benchmark-only --benchmark-compare

# Update baseline
pytest benchmarks/ --benchmark-only --benchmark-save=baseline
```

### CI Integration

```yaml
# .github/workflows/benchmarks.yml
name: Performance Benchmarks

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for comparison

      - name: Install dependencies
        run: |
          pip install -e .[benchmarks]

      - name: Run benchmarks
        run: |
          pytest benchmarks/ --benchmark-only \
            --benchmark-json=results.json \
            --benchmark-compare=baseline

      - name: Check for regressions
        run: |
          pytest-benchmark compare \
            --fail-on-regression \
            --threshold=10

      - name: Update baseline (main branch only)
        if: github.ref == 'refs/heads/main'
        run: |
          cp results.json benchmarks/baseline.json
          git add benchmarks/baseline.json
          git commit -m "Update performance baseline [skip ci]"
          git push

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: results.json
```

### Regression Detection

Example CI output when regression detected:

```
------------------------------------------------------
test_routing.py::test_complex_route
------------------------------------------------------
Baseline:  68.7 μs (ops: 14,556)
Current:   78.9 μs (ops: 12,674)
Change:    +14.8% ⚠️  REGRESSION

Possible causes:
- Added new middleware in request cycle
- Changed URL matching algorithm
- Introduced expensive operation in hot path

Review commit: abc123f
```

## Baseline Management

### Automatic Updates

Baselines auto-update on main branch:

```yaml
# Only on main, after tests pass
if: github.ref == 'refs/heads/main' && success()
run: |
  pytest benchmarks/ --benchmark-save=baseline
  git add benchmarks/baseline.json
  git commit -m "Update baseline [skip ci]" || true
```

### Manual Updates

For acceptable performance changes:

```bash
# Investigate regression
pytest benchmarks/test_routing.py -v

# If acceptable, update baseline
pytest benchmarks/ --benchmark-save=baseline

# Commit with explanation
git add benchmarks/baseline.json
git commit -m "Update baseline: Accept 5% slower routing due to #5234"
```

### Historical Tracking

Store baseline history:

```bash
# Tag releases with baseline
git tag -a v3.2.0-baseline -m "Baseline for v3.2.0"

# Compare against historical baseline
pytest benchmarks/ --benchmark-compare=v3.1.0-baseline
```

## Consequences

### Positive
- **Early detection**: Catch regressions before release
- **Historical data**: Track performance trends
- **Confidence**: Safe to refactor with performance guardrails
- **Accountability**: Clear visibility into performance impact

### Negative
- **CI time**: Adds 5-10 minutes to pipeline
- **Baseline maintenance**: Requires periodic updates
- **False positives**: Noise may trigger false alerts
- **Storage**: Baseline history grows over time

### Mitigations
- Run benchmarks in parallel with other CI jobs
- Use statistical methods to reduce noise (min-rounds=10)
- Allow manual baseline updates for acceptable changes
- Prune old baseline history (keep last 10 releases)

## Performance Trends

Example tracking over releases:

```
v3.0.0: Simple route: 45.2μs, Complex route: 68.7μs
v3.0.1: Simple route: 45.5μs, Complex route: 69.1μs
v3.1.0: Simple route: 47.8μs, Complex route: 72.3μs  (+5% slower)
v3.1.1: Simple route: 46.2μs, Complex route: 70.1μs  (optimized)
v3.2.0: Simple route: 46.5μs, Complex route: 71.2μs  (+observability)
```

## Benchmark Guidelines

### Writing Good Benchmarks

1. **Isolate the operation**: Test one thing at a time
2. **Use realistic data**: Production-like payloads
3. **Multiple rounds**: Reduce noise with repetitions
4. **Assert correctness**: Verify results are correct
5. **Document expectations**: Comment on expected performance

Example:

```python
def test_simple_route(benchmark):
    """Simple route should complete in < 50μs"""
    app = Flask(__name__)

    @app.route('/hello')
    def hello():
        return "Hello"

    client = app.test_client()

    # Run 10+ rounds for stable measurement
    result = benchmark(client.get, '/hello')

    # Verify correctness
    assert result.status_code == 200
    assert result.data == b"Hello"

    # Document expectation
    # Expected: ~45μs on modern hardware
```

### Avoiding Benchmark Pitfalls

❌ **Don't**:
```python
# Too few rounds (noisy)
benchmark(client.get, '/', min_rounds=1)

# Including setup in measurement
benchmark(setup_and_request)

# Ignoring results
assert True  # Always passes
```

✅ **Do**:
```python
# Sufficient rounds for stability
benchmark(client.get, '/', min_rounds=10)

# Separate setup from measurement
client = app.test_client()  # Setup
benchmark(client.get, '/')  # Measurement

# Verify correctness
result = benchmark(client.get, '/')
assert result.status_code == 200
```

## Alternatives Considered

1. **No performance tracking**: Regressions go undetected
2. **Manual benchmarking**: Inconsistent, not automated
3. **External tools (Gatling, Locust)**: More complex setup
4. **Higher threshold (20%)**: Misses gradual degradation

## References

- Benchmark suite: `benchmarks/`
- Baseline file: `benchmarks/baseline.json`
- CI workflow: `.github/workflows/benchmarks.yml`
- pytest-benchmark: https://pytest-benchmark.readthedocs.io/
