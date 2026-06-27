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
        tests.yaml                       # EDITED: smoke/perf/observability/triage layering
        release.yaml                     # NEW: semver release (workflow_dispatch, two-phase)
        benchmarks.yaml                  # NEW: weekly perf calibration (multi-sample, uploads result)
        (publish/pre-commit/lock/zizmor.yaml unchanged)
    benchmarks/                          # NEW: stdlib in-process perf gate (8 benchmarks)
      __init__.py, conftest.py, bench_core.py
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
    tests/test_platform.py               # NEW: dry-run tests for scripts (no Flask)
    Makefile                             # NEW: thin task runner
    pyproject.toml                       # EDITED: markers, tox envs, ruff.src, sdist.include

Unchanged (no public API behavior change): ``tests/test_*.py``,
``CHANGES.rst`` (format), ``uv.lock`` (proven in sync by the ``uv-lock``
pre-commit hook), the existing examples, ``publish.yaml``, ``docs/Makefile``.

No ``src/flask/**`` changes (byte-identical to upstream). One **upstream
finding**, not part of this platform: this snapshot's ``src/flask/cli.py``
imports ``ssl`` only under ``if t.TYPE_CHECKING:``, but the base-class
subscript ``click.ParamType[... ssl.SSLContext]`` (line 780) evaluates
``ssl`` at runtime (base-class subscripts are not deferred by
``from __future__ import annotations``). With the locked ``click==8.4.0``
this makes ``import flask`` raise ``NameError``. The fix (hoist
``import ssl`` to runtime) belongs **upstream**, not in this platform; the
platform's smoke gate correctly surfaces it. Flask-dependent gates
(smoke/perf actual benchmarks/OTel/typing) therefore require that upstream
fix to run; the platform's own logic (release/rollback/triage/perf-gate
comparison) is covered by ``tests/test_platform.py``, which does not import
Flask and runs under ``pytest --noconftest tests/test_platform.py``.


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
   timing, ``gc.disable()``, median of 200 iterations, and a **real
   multi-sample baseline** (``perf_check.py --samples 10 --update-baseline``,
   median of per-run medians). The gate is **configurable** via the repo
   variable ``PERF_GATE_MODE`` (``advisory`` default = warn only, exit 0;
   ``hard`` = ``--no-advisory``, hard regressions exit 1). Promote to ``hard``
   only after recalibrating across >= 10 CI runs.

#. **Auto-tag triggers PyPI publication** -- pushing ``vX.Y.Z`` runs
   ``publish.yaml``. Mitigated: ``release.yaml`` defaults to ``dry_run: true``;
   the release is **two commits** (release-prep sets the *clean* version and
   is tagged; ``start-dev`` reopens dev on a separate post-tag commit), so the
   tag points at a clean-version commit and ``uv build`` ships the right
   version (verified: ``version="3.2.0"`` -> ``flask-3.2.0`` artifacts); the
   existing ``environment: publish`` approval is the PyPI hard gate;
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

#. **No committed ``CHANGELOG.md`` mirror** -- by design: regenerating the
   full historical ``CHANGES.rst`` into a second file on every release would
   be a large-scale, uncurated rewrite (risk without benefit). Only
   per-version release notes are generated, on demand, by
   ``release_notes.py``; ``CHANGES.rst`` stays the single canonical
   changelog (hand-maintained, included in the docs as before).


Acceptance criteria
===================

* ``tox run -e style`` passes (new files are ruff/codespell/uv-lock clean).
* ``tox run -e docs`` passes under ``-W`` (ADRs, the observability page, and
  this page render with no dangling references).
* ``tox run -e smoke`` runs the curated subset and exits 0 on a clean tree.
* ``tox run -e perf`` runs all eight benchmarks, compares against
  ``baseline.json``, exits 0 in advisory mode, and posts a table.
* ``pytest --noconftest tests/test_platform.py`` passes (32 dry-run tests for
  the release two-phase, rollback runbook, perf-gate logic with stub
  benchmarks, and triage mapping -- no Flask import required).
* ``.github/workflows/benchmarks.yaml`` (weekly + manual) runs
  ``perf_check --samples 20 --out result.json`` and uploads ``perf-result``
  as calibration evidence; the committed ``baseline.json`` is a real 10-sample
  median (8 benchmarks).
* ``python scripts/triage.py --junit <dir>`` against a synthetic failed JUnit
  produces the attribution table with the correct source-module mapping for
  all nine exception stems and the default rule.
* ``python scripts/changes.py bump --level patch --dry-run`` prints the
  proposed version and the ``CHANGES.rst`` head diff without writing (and
  writes no ``CHANGELOG.md``).
* ``examples/observability/``'s own ``pytest`` passes (spans/metrics asserted
  via the in-memory exporter); the console-exporter path runs without a
  collector. ``setup_telemetry(app)`` instruments any Flask app (reusable
  module, not example-only).
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
``.github/workflows/release.yaml`` (default ``dry_run: true``); run a
dry-run release on ``main`` and verify the ``CHANGES.rst`` rename,
``pyproject.toml`` clean-version bump (tag points at the clean commit), and
per-version release notes (no ``CHANGELOG.md`` mirror). Gate: no tag pushed,
no PyPI interaction.

**Phase 5 -- Release pipeline (live, gated).** Run ``release.yaml`` with
``dry_run: false`` for a real patch release: tag push -> ``publish.yaml``
build -> ``publish`` environment approval -> trusted PyPI publish ->
``attach-notes`` sets the release body. Dry-run ``rollback.py`` against a
staged version; finalize the runbook in ADR 0004.
