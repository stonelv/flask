# ADR-001: Layered CI Architecture

## Status

Accepted

## Context

Flask's previous CI setup ran all checks in a single workflow, causing:
- Slow feedback loops (15-20 minutes for simple lint failures)
- Difficulty identifying which layer failed
- No performance regression detection
- Resource waste on full test runs for trivial changes

## Decision

Implement a 4-layer CI architecture:

### Layer 1: Quick Validation (< 2 minutes)
- Ruff linting and formatting
- Codespell
- Pre-commit hooks
- Basic syntax checks

**Purpose**: Fast feedback for obvious issues

### Layer 2: Core Tests (5-10 minutes)
- Unit tests across Python versions
- Type checking (mypy, pyright)
- Coverage enforcement (90% minimum)

**Purpose**: Validate correctness of changes

### Layer 3: Extended Tests (15-20 minutes)
- Integration tests
- Cross-platform tests (Windows, macOS)
- Minimum dependency versions
- Documentation builds

**Purpose**: Comprehensive compatibility testing

### Layer 4: Performance (5-10 minutes)
- Benchmark suite
- Regression detection (>10% threshold)
- Historical performance tracking

**Purpose**: Prevent performance regressions

## Implementation

```yaml
# .github/workflows/ci.yml
jobs:
  layer1-quick:
    runs-on: ubuntu-latest
    steps:
      - ruff check
      - ruff format --check
      - codespell

  layer2-tests:
    needs: layer1-quick
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - pytest tests/ --cov=src
      - mypy src/

  layer3-extended:
    needs: layer2-tests
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - pytest tests/ -m "integration or slow"

  layer4-performance:
    needs: layer2-tests
    steps:
      - pytest benchmarks/ --benchmark-compare
```

## Consequences

### Positive
- **Faster feedback**: Developers get lint errors in <2 minutes
- **Better resource usage**: Quick checks don't block expensive tests
- **Clear failure attribution**: Each layer has specific purpose
- **Performance visibility**: Regressions caught before merge

### Negative
- **Increased complexity**: More workflows to maintain
- **Potential delays**: Later layers wait for earlier ones
- **More GitHub Actions minutes**: Running multiple jobs

### Mitigations
- Use `needs:` dependencies to parallelize where possible
- Cache dependencies aggressively
- Make Layer 3/4 optional for draft PRs
- Monitor CI costs and adjust as needed

## Alternatives Considered

1. **Single workflow with conditional steps**: Simpler but slower feedback
2. **Separate PR and merge workflows**: Less granular control
3. **Third-party CI (CircleCI, Travis)**: More features but external dependency

## References

- PR #5123: Implement layered CI
- Discussion #5100: CI performance issues
- Benchmark baseline: benchmarks/baseline.json
