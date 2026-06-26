Contributing
============

See the Pallets `detailed contributing documentation <contrib_>`_ for many ways
to contribute, including reporting issues, requesting features, asking or
answering questions, and making PRs.

.. _contrib: https://palletsprojects.com/contributing/

Development Setup
-----------------

From a fresh clone, run the bootstrap script:

.. code-block:: text

    git clone https://github.com/pallets/flask.git
    cd flask
    bash scripts/bootstrap.sh

This installs all dependencies via ``uv``, sets up pre-commit hooks,
and runs a smoke test to verify everything works.

Alternatively, set up manually:

.. code-block:: text

    uv sync
    uv run pre-commit install --install-hooks

Running Tests
-------------

Run the test suite with:

.. code-block:: text

    make test          # default Python version
    make test-all      # full tox matrix (all Python versions)

Run a specific test file:

.. code-block:: text

    uv run pytest tests/test_basic.py -v

Linting and Type Checking
-------------------------

.. code-block:: text

    make lint          # ruff check + format via pre-commit
    make type          # mypy + pyright

Benchmarks
----------

Run the benchmark suite to check for performance regressions:

.. code-block:: text

    make bench

Results are output in JSON format for CI comparison.

Changelog Fragments
-------------------

Every PR that changes behavior should include a changelog fragment.
Create a file in ``changelog.d/`` named ``<issue-or-pr-number>.<type>.rst``
where ``<type>`` is one of:

- ``breaking`` — breaking changes
- ``feature`` — new features
- ``fix`` — bug fixes
- ``docs`` — documentation improvements
- ``internal`` — internal / CI / tooling changes

Example (``changelog.d/1234.feature.rst``):

.. code-block:: rst

    Added support for new widget. :pr:`1234`

Preview the assembled changelog:

.. code-block:: text

    make changelog-preview

Architecture Decision Records
------------------------------

Significant design decisions are documented as ADRs in ``docs/adr/``.
Use the template at ``docs/adr/000-template.rst`` as a starting point.

Release Process
---------------

Releases are managed by maintainers using the release script:

.. code-block:: text

    scripts/release.sh --dry-run 3.2.0   # preview
    scripts/release.sh 3.2.0             # execute

The script bumps the version, assembles the changelog, commits, and
tags. Pushing the tag triggers the publish workflow which builds and
publishes to PyPI via trusted OIDC.

See :doc:`adr/004-release-process` for the full process and rollback
strategy.

All Commands
------------

Run ``make help`` to see all available development commands:

.. code-block:: text

    make help

