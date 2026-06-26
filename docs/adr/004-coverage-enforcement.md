# ADR-004: Coverage Enforcement Policy

## Status

Accepted

## Context

Flask's test coverage had gradually declined from 92% to 87% over several releases due to:
- New features added without tests
- Legacy code paths not covered
- No automated enforcement
- Manual review prone to oversight

Low coverage leads to:
- Undetected bugs in untested paths
- Refactoring risk
- Reduced confidence in releases

## Decision

Enforce **90% minimum coverage** on all code in `src/flask/` with these policies:

1. **PR-level enforcement**: CI fails if coverage < 90%
2. **File-level reporting**: Show coverage per file
3. **Diff coverage**: New/changed code must maintain 90%
4. **Graceful degradation**: Allow temporary drops with documented issues

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| `src/flask/` (overall) | 90% | 92% |
| `src/flask/app.py` | 95% | 97% |
| `src/flask/blueprints.py` | 90% | 88% |
| `src/flask/templating.py` | 85% | 90% |
| `src/flask/observability/` | 95% | 98% |

### Exclusions

Exclude from coverage:
- Type stubs (`*.pyi`)
- Debug helpers (`debughelpers.py`)
- Example code (`examples/`)
- Benchmark code (`benchmarks/`)
- Test utilities (`tests/conftest.py`)

Configuration:

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/flask"]
omit = [
    "src/flask/debughelpers.py",
    "src/flask/observability/__init__.py",  # Re-exports only
]

[tool.coverage.report]
fail_under = 90
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

## Implementation

### CI Workflow

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest tests/ --cov=src/flask --cov-report=xml --cov-report=term-missing

- name: Check coverage threshold
  run: |
    coverage report --fail-under=90

- name: Upload coverage report
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Diff Coverage

Use `diff-cover` to enforce coverage on changed lines:

```yaml
- name: Check diff coverage
  run: |
    pip install diff-cover
    diff-cover coverage.xml --fail-under=90 --compare-branch=origin/main
```

### Local Development

```bash
# Run tests with coverage
pytest tests/ --cov=src/flask --cov-report=term-missing

# Check specific file
coverage run -m pytest tests/test_app.py
coverage report src/flask/app.py
```

## Consequences

### Positive
- **Higher quality**: More code paths tested
- **Regression prevention**: Bugs caught before merge
- **Refactoring confidence**: Tests validate behavior
- **Documentation**: Tests serve as usage examples

### Negative
- **Slower PR process**: Authors must write tests
- **Coverage gaming**: Developers may write trivial tests
- **Maintenance burden**: Tests need updating with code
- **False confidence**: Coverage ≠ correctness

### Mitigations
- Review test quality, not just coverage numbers
- Allow `# pragma: no cover` for truly untestable code
- Provide test templates and examples
- Regular coverage report reviews

## Coverage Trends

Track coverage over time:

```
v3.0.0: 92.1%
v3.0.1: 91.8%
v3.1.0: 89.5% ← Dropped below 90%
v3.1.1: 90.2% ← Recovery after enforcement
v3.2.0: 92.5% ← Observability well-tested
```

## Exception Process

For temporary coverage drops:

1. **Create issue**: Document why coverage dropped
2. **Add to PR**: Link issue in PR description
3. **Set deadline**: Commit to fix within 2 releases
4. **Review**: Maintainer approves exception

Example:

```markdown
## Coverage Exception

Issue: #5234 - Refactoring session management
Expected drop: 92% → 88%
Recovery plan: Add tests in #5235
Deadline: v3.2.1
```

## Alternatives Considered

1. **No enforcement**: Coverage continues to decline
2. **Higher threshold (95%)**: Too strict, blocks PRs
3. **Lower threshold (80%)**: Insufficient coverage
4. **File-level enforcement**: Too granular, hard to maintain

## References

- Coverage configuration: `pyproject.toml`
- CI workflow: `.github/workflows/test.yml`
- Coverage badge: README.md
- Historical data: `.coverage-history.json`
