Release Process and Rollback
============================

This page documents how a Flask release is cut, how change type maps to the
version number, and how to recover from a bad release. It complements the
automated pipeline in ``.github/workflows/publish.yaml`` and the decision record
in ``docs/adr/0005-semver-release-and-rollback.md``.

Versioning
----------

Flask follows `Semantic Versioning <https://semver.org/>`_. Change type maps to
the increment, and we use PR labels to make the intended tier explicit:

============  =====================  ============================================
PR label      Version increment      Examples
============  =====================  ============================================
``breaking``  major (``X``.0.0)      removing/renaming public API, behaviour change
``feature``   minor (x.``Y``.0)      new public API, additive capability
``fix``       patch (x.y.``Z``)      bug fix, docs, internal-only change
============  =====================  ============================================

``scripts/release.sh`` inspects commit messages since the last tag and
*suggests* the next version. The suggestion is advisory — the maintainer decides
and sets ``version`` in ``pyproject.toml``.

Changelog
---------

``CHANGES.rst`` is maintained **by hand** using Sphinx roles (``:pr:``,
``:issue:``). Every user-visible change gets an entry under the unreleased
version heading. CI enforces a simple invariant (the ``release-guard`` job in
``ci-fast.yaml``): if ``pyproject.toml``'s ``version`` changes in a PR but
``CHANGES.rst`` does not, the check fails. The changelog is validated, never
auto-generated, so the curated narrative is preserved.

Cutting a release
-----------------

#. Land all changes for the release on ``main``.
#. Set the final ``version`` in ``pyproject.toml`` (drop the ``.dev`` suffix).
#. Ensure ``CHANGES.rst`` has a dated section for that version.
#. Dry-run the wizard and review its checks (this is the default — it only
   validates and suggests, it does not tag)::

       ./scripts/release.sh

#. Create and push the annotated tag::

       ./scripts/release.sh --execute
       git push origin <version>

#. The tag push triggers ``publish.yaml``: a reproducible build, a **draft**
   GitHub release, and PyPI publication via OIDC trusted publishing.
#. Review the draft release notes, then publish them.

Rollback
--------

PyPI releases are **immutable** — a version number can never be reused. Recovery
is therefore roll-*forward* with a yank, not delete-and-replace:

#. **Yank the bad version** so new installs skip it while existing pins keep
   working::

       # via the PyPI web UI, or:
       # (pinned installs of the yanked version still resolve; new ranges skip it)

#. **Publish a fixed patch** release (e.g. ``x.y.Z+1``) following the steps
   above.
#. **Revert the offending commits** on ``main`` and add a ``CHANGES.rst`` entry
   describing the regression and fix.
#. If a tag was pushed but the build/publish has **not** completed, delete the
   tag and the draft release before they go public — the draft step exists
   precisely as this pre-publish safety net.

Because publication uses OIDC trusted publishing, no long-lived PyPI token can
leak; rotating credentials is not part of routine rollback.
