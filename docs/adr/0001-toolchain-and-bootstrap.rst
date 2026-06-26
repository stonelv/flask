ADR 0001: Unified toolchain, dependency layering, and bootstrap
===============================================================

:Date: 2026-06-26
:Status: Accepted

Context
-------

Flask already had a strong, modern toolchain before this work (``ruff`` for
lint/format, ``mypy`` + ``pyright`` for typing, ``tox`` for matrix runs,
``uv`` for dependency resolution with a committed ``uv.lock``, and
``pre-commit``). What was missing was a documented layering model and a
guarantee that adding the new engineering platform (benchmarks, release
scripts, telemetry example) would not churn the locked dependency graph.

The version source of truth is a single static line in ``pyproject.toml``
(``version = "3.2.0.dev"``). There is no ``__version__`` attribute in
``src/flask`` (it was removed in 3.2.0); the CLI reads it at runtime via
``importlib.metadata``. This makes release automation a one-line bump.

Decision
--------

#. **Dependency layering is expressed via ``[dependency-groups]``** in
   ``pyproject.toml`` (``dev``, ``tests``, ``typing``, ``docs``,
   ``pre-commit``, ``gha-update``). ``[tool.uv] default-groups`` enables
   ``dev`` + ``pre-commit`` + ``tests`` + ``typing`` for local development.

#. **No new runtime dependency touches the main ``uv.lock``.** Every new
   dependency lives somewhere that does not participate in the main lock:

   * OpenTelemetry libraries live in ``examples/observability/pyproject.toml``
     (a standalone flit project, mirroring the existing ``tutorial`` /
     ``celery`` / ``javascript`` examples).
   * The performance harness and all release/triage scripts are **standard
     library only** (``re``, ``argparse``, ``xml.etree``, ``subprocess``,
     ``statistics``, ``gc``). ``pytest-benchmark`` and ``commitizen`` were
     deliberately not adopted.

#. **``pyproject.toml`` edits are configuration-only** -- markers, tox env
   definitions, ``ruff.src``, ``flit.sdist.include`` -- none of which
   participate in dependency resolution. Therefore ``uv lock`` is never
   invoked by this platform and the work completes fully offline.

#. **The clone-to-release flow is one script**, ``scripts/bootstrap.sh``,
   with named modes (``check`` / ``full`` / ``perf`` / ``release``) that wrap
   the existing ``uv``/``tox`` invocations. A thin ``Makefile`` exposes the
   same steps as targets.

Consequences
------------

Positive: the engineering platform can be added without a ``uv lock``
regeneration, without network access, and without risk to the published
dependency set. The layering model is discoverable in one file.

Negative: contributors who later want ``commitizen`` or
``pytest-benchmark`` must add a ``[dependency-groups]`` entry and run an
online ``uv lock`` -- that is an explicit, separate step, not implicit. This
is intentional friction: it keeps the locked graph stable.

Alternatives considered
-----------------------

* Adopt ``commitizen``: rejected because it requires a ``release``
  dependency group and an online ``uv lock`` to regenerate ``uv.lock``; a
  stdlib ``scripts/changes.py`` achieves the same bump + changelog with zero
  dependencies.
* Add ``pytest-benchmark``: rejected for the same lock-churn reason; the
  in-process ``time.perf_counter`` harness is deterministic enough for a CI
  gate.
