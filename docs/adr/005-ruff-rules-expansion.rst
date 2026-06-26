ADR-005: Ruff Rules Expansion
=============================

Status
------

Accepted.

Context
-------

Flask's original ruff configuration selected only 6 rule categories:
B (bugbear), E (pycodestyle), F (pyflakes), I (isort), UP (pyupgrade),
and W (warnings). This left gaps in security scanning and code quality
enforcement.

Decision
--------

Expand the ruff ruleset to include:

- **S** (flake8-bandit) — security checks
- **PT** (flake8-pytest-style) — pytest best practices
- **RUF** — ruff-specific rules
- **SIM** (flake8-simplify) — code simplification
- **PIE** (flake8-pie) — miscellaneous lints
- **T20** (flake8-print) — disallow print statements
- **C4** (flake8-comprehensions) — comprehension improvements
- **ISC** (flake8-implicit-str-concat) — implicit string concatenation

**Per-file-ignores strategy**:

- ``tests/**``: Suppress assert usage (S101), hardcoded secrets
  (S105/S106), and pytest style rules that conflict with Flask's
  existing test patterns.
- ``benchmarks/**``: Allow print and assert.
- ``scripts/**``: Allow print and all security rules (scripts are
  developer tools, not production code).
- ``src/flask/cli.py``: S307 (eval) — intentional use in
  ``flask shell``.
- ``src/flask/sessions.py``: S324 (sha1) — intentional use for
  session signing.
- ``src/flask/config.py``: S102 (exec) and S110 — intentional
  patterns for config loading.
- ``src/flask/**``: RUF012 (mutable class defaults) and SIM rules —
  Flask's class-level dict/list defaults are a deliberate design
  pattern.

**Not enabled**:

- **TCH** (type-checking imports) — requires moving many imports
  into ``TYPE_CHECKING`` blocks, which risks changing runtime
  behavior. Too invasive for existing code.

Consequences
------------

**Positive:**

- Security issues (eval, exec, insecure hashes) are flagged and
  explicitly suppressed with rationale.
- New code is held to a higher standard automatically.
- Print statements in library code are caught.

**Negative:**

- The per-file-ignores list is long — new contributors may find it
  confusing.
- Some suppressions (RUF012, SIM rules) are blanket rather than
  per-line, which could mask issues in new code.
