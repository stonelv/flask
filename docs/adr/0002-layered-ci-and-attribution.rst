ADR 0002: Layered CI and failed-test auto-attribution
=====================================================

:Date: 2026-06-26
:Status: Accepted

Context
-------

The original ``.github/workflows/tests.yaml`` ran a single flat test matrix
(11 entries: Python 3.10-3.14, free-threaded 3.14t, Windows, macOS, PyPy,
minimum-versions, development-versions) plus a separate ``typing`` job. There
was no fast gate that could fail a broken pull request before spending matrix
minutes, no performance regression check, and no way to attribute a failing
test to the source module or team that owns it.

Two repo-specific constraints shaped the design:

#. ``[tool.pytest.ini_options]`` sets ``filterwarnings = ["error"]``. An
   unregistered ``@pytest.mark.smoke`` raises ``PytestUnknownMarkWarning``,
   which becomes a hard session failure. Markers must be registered before
   use.
#. The ``test_<x>.py`` -> ``flask/<x>.py`` filename mapping has nine
   non-obvious exceptions (e.g. ``test_request`` exercises
   ``src/flask/wrappers.py``, not a ``flask/request.py``; several test files
   target ``flask/app.py``). A naive ``test_<x> -> flask/<x>`` rule
   mis-attributes.

Decision
--------

#. **CI is layered with explicit gates:**

   .. code-block:: text

      smoke ──┬──> tests (matrix, --junit-xml) ──artifact──> triage (if: always)
              ├──> typing
              └──> perf (advisory)

   ``smoke`` is the fast first gate; the heavy matrix, ``typing``, and
   ``perf`` all ``need: smoke`` so a broken PR does not spend matrix minutes.

#. **Smoke selection is data-driven, not decorator-driven.** Markers
   ``smoke`` and ``slow`` are registered in ``pyproject.toml`` (and again in
   ``tests/conftest.py::pytest_configure`` as a belt-and-suspenders measure).
   ``pytest_collection_modifyitems`` only *adds* the ``smoke`` marker to a
   curated ``SMOKE_MODULES`` allowlist. No ``tests/test_*.py`` file is edited;
   a normal run (no ``-m``) selects the whole suite unchanged.

#. **Failed-test attribution** is ``scripts/triage.py`` (stdlib). It parses
   JUnit XML, derives the test stem from ``classname``, maps it to a source
   module via a static ``TEST_TO_MODULE`` dict (encoding the nine
   exceptions, defaulting to ``src/flask/<stem>.py`` and falling back to the
   test file itself when that path does not exist), resolves owners from
   ``.github/CODEOWNERS`` (longest-prefix match), and falls back to
   ``git log`` on the mapped source file. Output is a Markdown table written
   to ``$GITHUB_STEP_SUMMARY``.

#. **The performance gate is in-process and advisory at first.** The
   benchmarks use the Flask test client (no network), disable GC around the
   measured loop, and report the median of 200 iterations. The gate compares
   ratios against ``benchmarks/baseline.json``. In Phase 1 it is fully
   advisory (exit 0); ``core_request_roundtrip`` is promoted to a hard gate
   (exit 1 beyond 1.25x) only after recalibrating the baseline across >= 10
   CI runs.

Consequences
------------

Positive: broken PRs fail in seconds on ``smoke`` rather than minutes on the
matrix; every failure ships with an owner and a deep link to the last
change; perf regressions are visible before they reach a release.

Negative: the ``smoke`` allowlist must be curated as new high-signal tests
land (it is a single ``frozenset`` in ``tests/conftest.py``). The perf gate
is non-deterministic on noisy runners, which is why it starts advisory.

Alternatives considered
-----------------------

* Decorate individual tests with ``@pytest.mark.smoke``: rejected because it
  edits every test file and would itself be a churny diff; the allowlist is
  one place to tune.
* ``pytest-benchmark``: rejected (see ADR 0001) for lock-churn reasons.
