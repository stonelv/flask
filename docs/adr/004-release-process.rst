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

If already published to PyPI, yank the version (do NOT delete it —
yanking hides it from ``pip install`` but keeps existing pins working):

.. code-block:: text

    1. Go to https://pypi.org/manage/project/Flask/
    2. Click the affected version → "Options" → "Yank"
    3. Enter a reason (e.g. "critical regression in routing")

Post-yank, publish a patch release with the fix rather than
re-uploading to the same version number (PyPI version numbers are
immutable).

Post-release, bump to the next development version:

.. code-block:: bash

    sed -i 's/^version = ".*"/version = "X.Y.(Z+1).dev"/' pyproject.toml
    uv lock
    git add -A && git commit -m "Start X.Y.(Z+1) development"
    git push

**CI publish pipeline guards (``publish.yaml``):**

1. ``validate`` job — runs ``validate_release.py`` to verify tag
   matches ``pyproject.toml`` version, no ``.dev`` suffix, changelog
   entry exists, and no leftover changelog fragments.
2. ``build`` job — builds wheel + sdist with reproducible
   ``SOURCE_DATE_EPOCH``.
3. ``create-release`` job — creates a draft GitHub Release with
   changelog notes extracted from ``CHANGES.rst``.
4. ``publish-pypi`` job — publishes via trusted OIDC (no API token
   needed).

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
