ADR 0004: Semantic-versioning release pipeline and rollback
===========================================================

:Date: 2026-06-26
:Status: Accepted

Context
-------

Releases were a manual, tag-driven flow: a maintainer hand-edits
``CHANGES.rst``, bumps ``pyproject.toml``'s ``version``, pushes a tag, and
``.github/workflows/publish.yaml`` builds and publishes to PyPI via trusted
publishing. There was no change classification, no auto-generated changelog,
and no rollback runbook. ``CHANGES.rst`` is hand-maintained reStructuredText
with ``:pr:`` / ``:issue:`` / ``:ghsa:`` roles, included into the docs via
``docs/changes.rst``.

Decision
--------

#. **The release core is a dependency-free script, ``scripts/changes.py``**,
   not ``commitizen``. It edits the single ``version =`` line in
   ``pyproject.toml`` and performs string operations on ``CHANGES.rst`` --
   no parser dependency, no ``uv.lock`` regeneration, works offline.

#. **``CHANGES.rst`` remains canonical and hand-maintained.** A derived
   ``CHANGELOG.md`` (Keep-a-Changelog markdown) is regenerated from it on
   every release via ``changes.py mirror`` and carries a do-not-edit header;
   it cannot drift because it is never hand-edited.

#. **Change classification reads Conventional Commit subjects** since the last
   ``vX.Y.Z`` tag (``BREAKING``/``!`` -> major, ``feat`` -> minor,
   ``fix``/``perf`` -> patch, default patch). Classification only selects the
   *bump level*; it does not write prose -- humans still curate
   ``CHANGES.rst``. The repo's existing free-form history is not retro-fitted;
   the advisory lint applies to future commits.

#. **A new ``.github/workflows/release.yaml``** (``workflow_dispatch``,
   ``dry_run: true`` by default) makes the release as **two commits** so the
   tag points at a *clean-version* commit:

   - ``changes.py bump --apply`` (release-prep): sets ``pyproject.toml``
     ``version = "X.Y.Z"`` (clean, no ``.dev``) and renames the head
     ``Unreleased`` -> ``Released <date>``. The commit "Release X.Y.Z" is
     **tagged** ``vX.Y.Z``. ``uv build`` on this commit produces
     ``Flask-X.Y.Z`` (verified: building with ``version = "3.2.0"`` yields
     ``flask-3.2.0`` artifacts), *not* the next dev.
   - ``changes.py start-dev --next-dev X.Y.(Z+1).dev --apply``: reopens
     development on a **separate post-tag commit** (``pyproject`` ->
     ``X.Y.(Z+1).dev``, new ``Unreleased`` block). Pushed to ``main`` after
     the tag, so the tag still points at the clean-version commit.

   The tag push triggers the *existing* ``publish.yaml`` -- which is not
   modified. A separate ``attach-notes`` job sets the GitHub release body
   from ``release_notes.py``.

#. **The PyPI hard gate is the existing ``environment: publish`` approval**
   on ``publish.yaml``. The release workflow never publishes directly; the
   ``dry_run: true`` default and the environment reviewers together prevent
   accidental publication.

#. **Rollback is a runbook**, ``scripts/rollback.py``. PyPI files cannot be
   deleted, so rollback = yank/retract + ``git revert`` the release commit +
   republish a patch (``X.Y.(Z+1)``) containing the revert. The script
   prints the runbook and, with ``--apply`` / ``--yank`` (the latter needs
   ``PYPI_API_TOKEN``, since trusted publishing cannot yank), executes the
   safe local parts. It never auto-pushes tags without an explicit flag.

Consequences
------------

Positive: a reproducible, auditable release path that reuses the trusted
publishing gate; a single command produces a correct version bump, changelog
mirror, and release notes; a documented rollback procedure exists before it
is needed.

Negative: two changelog files exist (``CHANGES.rst`` canonical,
``CHANGELOG.md`` derived). This is intentional and bounded: the derived file
is regenerated every release, so it cannot diverge for long. A future phase
may unify them by teaching the docs to render ``CHANGELOG.md``.

Alternatives considered
-----------------------

* ``commitizen`` / ``release-please``: rejected -- each requires a new main
  dependency group and an online ``uv lock`` (ADR 0001), and their Markdown
  changelog would not match the existing reST format without custom config.
* Auto-release on push to ``main``: rejected as unsafe; the workflow is
  manual dispatch with a dry-run default.
