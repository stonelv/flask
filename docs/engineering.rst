Engineering Platform: Observability & Release Governance
========================================================

This page documents the production-observability and release-governance
engineering platform added to this repository. It is the single place to find
the directory plan, risk list, acceptance criteria, and phased migration
plan. The per-decision rationale lives in the :doc:`adr/index`.

The platform was built under two hard constraints: **no change to any public
API in ``src/flask/``**, and **no churn to the committed ``uv.lock``**. Every
addition is purely additive; the design rule that makes the second constraint
hold is captured in ADR 0001 (new runtime dependencies live in a standalone
example project or are standard-library-only).


Directory plan
--------------

All additions are additive -- nothing is removed or renamed::

    .github/
      CODEOWNERS                         # reviewer auto-assign + triage input
      workflows/
        tests.yaml                       # EDITED: smoke/perf/triage layering
        release.yaml                     # NEW: semver release (workflow_dispatch)
        (publish/pre-commit/lock/zizmor.yaml unchanged)
    benchmarks/                          # NEW: stdlib in-process perf gate
      __init__.py, conftest.py
      bench_core.py, bench_routing.py, bench_templating.py
      baseline.json, perf_check.py, README.rst
    docs/
      engineering.rst                    # NEW: this page
      adr/{index,0001..0005}.rst         # NEW: architecture decision records
      patterns/observability.rst         # NEW: OTel patterns page
      index.rst                          # EDITED: Additional Notes toctree
      patterns/index.rst                 # EDITED: patterns toctree
    examples/observability/              # NEW: standalone OTel flit project
    scripts/                             # NEW: stdlib tooling
      changes.py, release_notes.py, triage.py, rollback.py, bootstrap.sh
    tests/conftest.py                    # EDITED: marker registration + smoke allowlist
    Makefile                             # NEW: thin task runner
    CHANGELOG.md                         # NEW: derived mirror, generated on release
    pyproject.toml                       # EDITED: markers, tox envs, ruff.src, sdist.include

Unchanged: ``src/flask/**``, ``tests/test_*.py``, ``CHANGES.rst`` (format),
``uv.lock``, the existing examples, ``publish.yaml``, ``docs/Makefile``.


Risk list
=========

#. **Main ``uv.lock`` churn** -- mitigated by design: OTel deps live in
   ``examples/observability/`` (separate project); the perf harness and all
   scripts are standard-library-only. ``pyproject.toml`` edits are
   configuration-only and do not participate in dependency resolution, so
   ``uv lock`` is never invoked.

#. **Unregistered pytest marker under ``filterwarnings = ["error"]``** -- an
   unregistered ``@pytest.mark.smoke`` becomes a session error. Mitigated:
   markers are registered in ``pyproject.toml`` and in
   ``tests/conftest.py::pytest_configure``; ``pytest_collection_modifyitems``
   only *adds* markers, so normal runs are unchanged.

#. **Sphinx ``-W`` toctree breakage** -- a dangling toctree entry fails the
   docs build. Mitigated by ordering: every referenced file is created before
   the toctree entry is added, in the same change. ADRs are self-contained
   prose with no ``:ref:`` labels. ``tox run -e docs`` is a gate.

#. **Performance-gate flakiness** -- CI runner jitter. Mitigated: in-process
   timing, ``gc.disable()``, median of 200 iterations, **advisory in Phase 1**;
   promoted to a hard gate only after recalibrating the baseline across
   >= 10 CI runs.

#. **Auto-tag triggers PyPI publication** -- pushing ``vX.Y.Z`` runs
   ``publish.yaml``. Mitigated: ``release.yaml`` defaults to ``dry_run: true``;
   the existing ``environment: publish`` approval is the hard gate;
   ``publish.yaml`` is not modified; ``scripts/rollback.py`` documents
   yank/revert/republish.

#. **Shallow-checkout git blame** -- ``actions/checkout`` defaults to
   ``fetch-depth: 1``, which breaks ``git log`` across history. Mitigated:
   only the ``triage`` job uses ``fetch-depth: 0``; the test/typing/perf jobs
   keep the default.

#. **``tox run`` local behavior change** -- adding envs to ``env_list`` would
   make a bare ``tox run`` execute them locally. Mitigated: ``smoke`` and
   ``perf`` are defined but **not** added to ``env_list``; CI invokes them
   with ``-e``.

#. **``CHANGELOG.md`` drift from ``CHANGES.rst``** -- mitigated:
   ``CHANGELOG.md`` is regenerated from ``CHANGES.rst`` on every release
   (idempotent ``mirror`` command) and is never hand-edited.


Acceptance criteria
===================

* ``tox run -e style`` passes (new files are ruff/codespell/uv-lock clean).
* ``tox run -e docs`` passes under ``-W`` (ADRs, the observability page, and
  this page render with no dangling references).
* ``tox run -e smoke`` runs the curated subset and exits 0 on a clean tree.
* ``tox run -e perf`` runs all three benchmarks, compares against
  ``baseline.json``, exits 0 in advisory mode, and posts a table.
* ``python scripts/triage.py --junit <dir>`` against a synthetic failed JUnit
  produces the attribution table with the correct source-module mapping for
  all nine exception stems and the default rule.
* ``python scripts/changes.py bump --level patch --dry-run`` prints the
  proposed version, the ``CHANGES.rst`` head diff, and a ``CHANGELOG.md``
  preview without writing.
* ``examples/observability/``'s own ``pytest`` passes (spans/metrics asserted
  via the in-memory exporter); the console-exporter path runs without a
  collector.
* ``uv.lock`` is byte-identical to the pre-platform lock (proof of zero
  churn); ``src/flask/**`` is byte-identical to the pre-platform tree.
* ``./scripts/bootstrap.sh check`` completes green on a fresh clone.


Phased migration plan
=====================

**Phase 1 -- Foundations (no CI behavior change).** Add ``docs/adr/`` and
``docs/engineering.rst`` and wire the toctree; add ``scripts/`` (changes,
release_notes, triage, rollback, bootstrap.sh) and the top-level ``Makefile``;
add the ``pyproject.toml`` configuration (markers, ``smoke``/``perf`` tox
envs, ``ruff.src``, sdist include); add the ``tests/conftest.py`` hooks; add
``benchmarks/`` + ``baseline.json`` + ``perf_check.py``; add
``.github/CODEOWNERS``. Gate: ``style``/``docs``/``smoke``/``perf`` green,
``uv.lock`` unchanged, CI still runs only the existing jobs.

**Phase 2 -- CI layering (gating).** Edit ``tests.yaml``: add the ``smoke``
gate, make ``tests``/``typing``/``perf`` depend on it, add the junit posarg
and ``upload-artifact``, add the ``triage`` job (``needs: tests``,
``if: always()``, ``fetch-depth: 0``). Perf runs advisory. Gate: a
deliberately-failing PR produces a populated step-summary attribution table;
a broken PR is skip-cancelled at smoke.

**Phase 3 -- Observability + perf hardening.** Add
``examples/observability/`` (full project + docker-compose) and
``docs/patterns/observability.rst`` + its toctree entry; recalibrate
``baseline.json`` from >= 10 CI runs and promote
``core_request_roundtrip`` to a hard failure. Gate: example tests green; the
perf gate hard-fails a synthetic regression.

**Phase 4 -- Release pipeline (manual, dry-run).** Add
``.github/workflows/release.yaml`` (default ``dry_run: true``); add
``CHANGELOG.md`` via ``changes.py mirror``; run a dry-run release on ``main``
and verify the ``CHANGES.rst`` rename, ``pyproject.toml`` bump,
``CHANGELOG.md`` mirror, and release notes. Gate: no tag pushed, no PyPI
interaction.

**Phase 5 -- Release pipeline (live, gated).** Run ``release.yaml`` with
``dry_run: false`` for a real patch release: tag push -> ``publish.yaml``
build -> ``publish`` environment approval -> trusted PyPI publish ->
``attach-notes`` sets the release body. Dry-run ``rollback.py`` against a
staged version; finalize the runbook in ADR 0004.
