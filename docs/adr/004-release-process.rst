ADR-004: Semantic Versioning Release Process
============================================

Status
------

Accepted.

Context
-------

Flask's changelog (``CHANGES.rst``) was maintained by hand — a
contributor added a bullet to the "unreleased" section in their PR.
This led to merge conflicts and occasionally missed entries.

The release process was also manual: update version, update changelog,
commit, tag, push.

Decision
--------

Adopt `towncrier <https://towncrier.readthedocs.io/>`_ for fragment-
based changelog generation and a release script for the end-to-end
flow.

**Changelog fragments**: Each PR creates a file in ``changelog.d/``
named ``<number>.<type>.rst`` where type is one of:

- ``breaking`` — breaking changes
- ``feature`` — new features
- ``fix`` — bug fixes
- ``docs`` — documentation improvements
- ``internal`` — internal / CI / tooling changes

**Release script** (``scripts/release.sh``):

1. Validates clean git state and correct branch.
2. Runs ``towncrier build --version X.Y.Z`` to assemble fragments
   into ``CHANGES.rst``.
3. Updates ``version`` in ``pyproject.toml``.
4. Updates the lock file.
5. Commits and tags.
6. Prints rollback instructions.

Supports ``--dry-run`` for previewing.

**Publish workflow** (``publish.yaml``):

- Added a ``validate`` job that checks tag matches version, no
  ``.dev`` suffix, and changelog entry exists.
- Release notes are extracted from ``CHANGES.rst`` and attached
  to the GitHub release.

**Rollback strategy**:

.. code-block:: bash

    git tag -d X.Y.Z
    git reset --hard HEAD~1
    git push origin :refs/tags/X.Y.Z  # if already pushed

If already published to PyPI, yank the release:

.. code-block:: bash

    pip install twine
    twine upload --skip-existing dist/*  # re-upload is idempotent
    # Or use PyPI web UI to yank

Consequences
------------

**Positive:**

- No more merge conflicts on ``CHANGES.rst``.
- The PR template reminds contributors to add fragments.
- Release process is scripted and repeatable.
- Rollback instructions are provided automatically.

**Negative:**

- Contributors must learn the fragment workflow (mitigated by the
  PR template checklist).
- Towncrier is another dev dependency.
- The custom RST template needs maintenance if the changelog
  format changes.
