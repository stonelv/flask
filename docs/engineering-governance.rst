Engineering Governance
======================

This page is the operational companion to the Architecture Decision Records in
``docs/adr/``. It captures the engineering system added for observability and
release governance: what runs where, the risks and how they are mitigated, the
acceptance criteria, and the migration plan. The overriding constraint is that
**none of this changes Flask's public API behaviour**.

Components
----------

============================  ===========================================  ==============================
Area                          Where                                        How it runs
============================  ===========================================  ==============================
One-click developer flow      ``Makefile``, ``scripts/``                   ``make bootstrap|dev|test|perf``
Fast CI lane                  ``.github/workflows/ci-fast.yaml``           lint + format + smoke + example
Full compatibility matrix     ``.github/workflows/tests.yaml``             unchanged matrix + failure triage
Performance gate              ``.github/workflows/benchmarks.yaml``        ``benchmarks/`` vs baseline
Observability (opt-in)        ``examples/observability/``                  isolated env, in-memory tested
Release governance            ``.github/workflows/publish.yaml``           verify tag/notes, validate, publish
Rollback                      ``scripts/rollback.sh``                      yank + tag/release teardown
============================  ===========================================  ==============================

Public API guarantee
--------------------

- No change to anything importable from ``flask`` other than restoring
  importability: ``flask.cli.CertParamType`` previously crashed at import time
  because it subscripted ``click.ParamType[... ssl.SSLContext]`` while ``ssl``
  was only imported under ``TYPE_CHECKING``. It now subclasses a base aliased
  under ``TYPE_CHECKING`` — the full generic for type checkers, bare
  ``click.ParamType`` at runtime — so ``import flask`` no longer requires
  ``ssl`` while ``mypy --strict`` and ``pyright`` still see the generic. The
  runtime behaviour of the type is unchanged.
- OpenTelemetry never enters ``src/`` or ``uv.lock`` (enforced by review and the
  ``grep -r opentelemetry src/`` check).
- ``CHANGES.rst`` remains hand-maintained; tooling validates, never rewrites it.

Risk register
-------------

==============================================  ========  ====================================================
Risk                                            Severity  Mitigation
==============================================  ========  ====================================================
Benchmark noise on shared runners               Medium    median comparison, 10% threshold, advisory by
                                                          default; ``PERF_ENFORCE`` opt-in for stable runners
Baseline JSON bloat in git                      Medium    ``trim_baseline.py`` keeps only summary stats (~3 KB)
OTel deps leaking into core                     High→ok   isolated ``examples/observability`` project + grep gate
Auto-changelog breaking Pallets convention      High→ok   validate-only ``release-guard``; no generation
``git blame`` triage on shallow checkout        Low       triage job uses ``fetch-depth: 0``; degrades to plain
                                                          list if blame unavailable; never fails the build
Tag/version drift at release                    Medium    ``publish.yaml`` ``verify`` job blocks mismatch
Bad release on immutable PyPI                   Medium    draft-release safety net + ``rollback.sh`` yank flow
Makefile unavailable on Windows                 Low       scripts callable directly; ``uv``/tox equivalents noted
==============================================  ========  ====================================================

Acceptance criteria
-------------------

- ``uv run --locked`` commands succeed: ``import flask`` works, the smoke tests
  pass, ``ruff check``/``ruff format --check`` are clean, and the typing job
  runs.
- ``pytest`` (default ``testpaths=tests``) does **not** collect ``benchmarks/``;
  ``pytest benchmarks/`` runs the 8 micro-benchmarks.
- ``scripts/perf.sh`` is advisory by default and fails only when
  ``PERF_ENFORCE=true`` and a benchmark regresses beyond ``PERF_THRESHOLD``.
- ``benchmarks/baseline/baseline.json`` is a trimmed (~KB) summary, not the raw
  multi-MB run.
- ``tests/test_triage.py`` exercises the failure-attribution helper.
- ``examples/observability/test_otel.py`` proves spans and metrics are emitted
  using in-memory exporters; the core lock has no OTel deps.
- ``publish.yaml`` blocks when the tag and ``pyproject`` version disagree, builds
  reproducibly, validates artifacts with ``twine check --strict``, and attaches
  changelog-derived notes to a **draft** release before PyPI upload.
- ``release-guard`` fails a PR that bumps the version without a ``CHANGES.rst``
  entry.

Migration plan
--------------

The work is additive and lands in independent, revertible steps:

#. **Import fix + lock**: restore ``flask.cli`` importability, add the
   ``benchmarks`` dependency group, refresh ``uv.lock``.
#. **One-click + fast CI**: ``scripts/``, ``Makefile``, ``ci-fast.yaml``.
#. **Performance gate**: ``benchmarks/`` suite, trimmed baseline, comparator,
   ``benchmarks.yaml`` (advisory; flip ``PERF_ENFORCE`` to enforce later).
#. **Failure triage**: ``scripts/triage_failures.py`` + ``tests/test_triage.py``
   + the ``if: failure()`` step in ``tests.yaml``.
#. **Observability**: ``examples/observability/`` with an in-memory-exporter
   test and a dedicated CI job.
#. **Release governance**: ``publish.yaml`` verify/validate/notes jobs,
   ``release.sh``, ``changelog_extract.py``, ``rollback.sh``,
   ``docs/release-process.rst``.

Each step can be reverted by removing its files (and, for the two edited
workflows and ``cli.py``, reverting the diff) without affecting the others.
