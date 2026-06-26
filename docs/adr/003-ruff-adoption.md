# ADR-003: Ruff as Primary Linter and Formatter

## Status

Accepted

## Context

Flask historically used multiple tools for code quality:
- **Linting**: flake8, pylint, isort
- **Formatting**: black
- **Type checking**: mypy

Problems:
- Slow execution (multiple tools, multiple passes)
- Configuration spread across multiple files
- Conflicting rules between tools
- Maintenance overhead

## Decision

Adopt **Ruff** as the primary linter and formatter, replacing flake8, black, and isort.

### Why Ruff?

1. **Speed**: 10-100x faster than flake8/black (Rust-based)
2. **Unified tool**: Linting + formatting in single tool
3. **Compatible**: Drop-in replacement for flake8/black/isort
4. **Active development**: Frequent updates, large rule set
5. **Single config**: All settings in `pyproject.toml`

## Implementation

### Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["flask"]
```

### Migration Steps

1. **Install Ruff**: Add to dev dependencies
2. **Run auto-fix**: `ruff check --fix .`
3. **Format code**: `ruff format .`
4. **Update CI**: Replace flake8/black with ruff
5. **Update pre-commit**: Use ruff hooks
6. **Remove old tools**: Uninstall flake8, black, isort

### Handling Violations

For remaining violations after auto-fix:

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # Allow assert in tests
"src/flask/legacy.py" = ["UP"]  # Don't upgrade legacy code
```

### CI Integration

```yaml
# .github/workflows/lint.yml
- name: Lint with Ruff
  run: |
    pip install ruff
    ruff check .
    ruff format --check .
```

## Consequences

### Positive
- **10-100x faster**: Instant feedback on code changes
- **Simpler setup**: One tool, one config file
- **Better DX**: Fewer tools to learn and maintain
- **Consistent rules**: No conflicts between tools
- **Modern**: Actively maintained, frequent updates

### Negative
- **Migration effort**: One-time cost to switch tools
- **Team learning**: Developers need to learn Ruff
- **Fewer options**: Less flexibility than multiple tools
- **Dependency risk**: Single tool failure impacts all linting

### Mitigations
- Ruff is highly compatible with flake8/black (minimal changes)
- Provide migration guide for contributors
- Monitor Ruff development for breaking changes
- Keep mypy for type checking (Ruff doesn't replace this)

## Alternatives Considered

1. **Keep flake8 + black**: Slower but proven tools
2. **Use pylint**: More comprehensive but much slower
3. **Custom tooling**: More control but high maintenance
4. **No linting**: Faster but lower code quality

## Migration Checklist

- [x] Install Ruff in dev dependencies
- [x] Configure `pyproject.toml`
- [x] Run `ruff check --fix .`
- [x] Run `ruff format .`
- [x] Update pre-commit hooks
- [x] Update CI workflows
- [x] Remove flake8, black, isort from dependencies
- [x] Update contributing documentation
- [x] Verify no regressions in test suite

## Performance Comparison

| Tool | Time (full codebase) |
|------|---------------------|
| flake8 + black + isort | 12.5s |
| Ruff | 0.3s |
| **Speedup** | **42x** |

## References

- Ruff documentation: https://docs.astral.sh/ruff/
- PR #5130: Migrate to Ruff
- Pre-commit config: `.pre-commit-config.yaml`
