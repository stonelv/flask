ADR-003: Layered CI Pipeline
============================

Status
------

Accepted.

Context
-------

The original CI setup ran all tests and linting in one workflow. This
had two problems:

1. Developers waited for the full matrix (10+ jobs, ~5 minutes) to
   learn about a typo or type error.
2. Performance regressions were invisible — no benchmark comparison.

Decision
--------

Split CI into three layers, each with a clear purpose and time budget:

**Layer 1 — Fast Gate** (``lint.yaml``, target < 2 min):

- ``lint`` job: pre-commit / ruff
- ``typing`` job: mypy + pyright (with cache)
- ``smoke`` job: pytest on ``tests/test_basic.py`` with timeout

**Layer 2 — Full Test Suite** (``tests.yaml``):

- Python 3.10–3.14, PyPy, free-threaded, Windows, Mac
- Minimum and development dependency versions
- JUnit XML output + automatic failure attribution

**Layer 3 — Performance Gate** (``benchmarks.yaml``):

- Runs ``pytest-benchmark`` suite
- Compares against cached baseline from ``main``
- Advisory by default (warns, does not block merge)
- Blocks only on regressions > 15%

Failure attribution (``scripts/ci/parse_failures.py``) reads JUnit
XML and categorizes failures into: assertion, import, timeout,
fixture, or infrastructure errors, then annotates the PR.

Consequences
------------

**Positive:**

- Developers get lint/type feedback in < 2 minutes.
- Performance regressions are visible before merge.
- Failure categorization reduces triage time.

**Negative:**

- Three workflows to maintain instead of two.
- Benchmark results are noisy on shared CI runners; the 15%
  threshold accepts some false negatives.
- JUnit XML parsing adds a maintenance surface.
