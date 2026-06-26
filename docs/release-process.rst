.. _release-process:

Release Process
===============

This document describes Flask's release process, including versioning, changelog generation, and publishing.

Versioning
----------

Flask follows `Semantic Versioning <https://semver.org/>`_:

- **Major** (3.0.0 → 4.0.0): Breaking changes
- **Minor** (3.0.0 → 3.1.0): New features, backward compatible
- **Patch** (3.0.0 → 3.0.1): Bug fixes, backward compatible

Development versions use ``.dev`` suffix: ``3.2.0.dev``

Release Preparation
-------------------

1. Update Changelog
~~~~~~~~~~~~~~~~~~~

Generate changelog from commits:

.. code-block:: bash

    python scripts/generate_changelog.py

This creates ``CHANGES.md`` from git history and PR labels.

Review and edit the changelog:

- Group changes by category (Features, Fixes, etc.)
- Add migration notes for breaking changes
- Credit contributors

2. Bump Version
~~~~~~~~~~~~~~~

Update version in ``pyproject.toml``:

.. code-block:: bash

    # Patch release
    python scripts/bump_version.py patch

    # Minor release
    python scripts/bump_version.py minor

    # Major release
    python scripts/bump_version.py major

    # Specific version
    python scripts/bump_version.py 3.2.0

This updates:

- ``pyproject.toml`` version
- ``src/flask/__version__.py``
- ``docs/conf.py`` version

3. Run Validation
~~~~~~~~~~~~~~~~~

Ensure all checks pass:

.. code-block:: bash

    # Run tests
    pytest tests/

    # Run benchmarks
    pytest benchmarks/ --benchmark-only

    # Check type hints
    mypy src/

    # Check formatting
    ruff check .
    ruff format --check .

4. Create Release Branch
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git checkout -b release/3.2.0
    git add -A
    git commit -m "Release 3.2.0"

5. Create Pull Request
~~~~~~~~~~~~~~~~~~~~~~

Open a PR for the release branch:

- Title: ``Release 3.2.0``
- Description: Link to changelog
- Wait for CI to pass
- Get approval from maintainers

Publishing
----------

After PR merge:

1. Tag the Release
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git checkout main
    git pull
    git tag v3.2.0
    git push origin v3.2.0

The tag triggers the publish workflow:

- Validates tag matches version
- Builds distribution
- Publishes to TestPyPI
- Publishes to PyPI
- Creates GitHub Release

2. Verify Release
~~~~~~~~~~~~~~~~~

Check the release:

- PyPI: https://pypi.org/project/Flask/3.2.0/
- GitHub: https://github.com/pallets/flask/releases/tag/v3.2.0
- Test installation: ``pip install Flask==3.2.0``

3. Announce Release
~~~~~~~~~~~~~~~~~~~

- Post on Flask Discord
- Tweet from @PalletsTeam
- Update flask.palletsprojects.com

4. Prepare Next Development Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bump to next dev version:

.. code-block:: bash

    python scripts/bump_version.py 3.3.0.dev
    git add -A
    git commit -m "Bump to 3.3.0.dev"
    git push origin main

Hotfix Releases
---------------

For critical bugs in released versions:

1. Checkout Release Tag
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git checkout v3.2.0
    git checkout -b hotfix/3.2.1

2. Apply Fix
~~~~~~~~~~~~

Cherry-pick or apply the fix:

.. code-block:: bash

    git cherry-pick <commit-hash>

3. Bump Patch Version
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    python scripts/bump_version.py patch

4. Update Changelog
~~~~~~~~~~~~~~~~~~~

Add entry for the hotfix:

.. code-block:: markdown

    ## 3.2.1 - 2024-01-15

    ### Fixed
    - Critical security issue in session handling (#1234)

5. Create PR and Release
~~~~~~~~~~~~~~~~~~~~~~~~

Follow normal release process (steps 4-5 above).

Rollback Procedure
------------------

If a release has critical issues:

1. Yank from PyPI
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    python scripts/rollback.py 3.2.0

This marks the version as "yanked" on PyPI (prevents new installs but allows existing).

2. Create Fix Release
~~~~~~~~~~~~~~~~~~~~~

Immediately create a hotfix release (see above).

3. Communicate
~~~~~~~~~~~~~~

- Post advisory on GitHub
- Notify Flask Discord
- Update documentation if needed

Automated Release Scripts
-------------------------

bump_version.py
~~~~~~~~~~~~~~~

Bumps version across all files:

.. code-block:: bash

    # Increment patch
    python scripts/bump_version.py patch

    # Increment minor
    python scripts/bump_version.py minor

    # Set specific version
    python scripts/bump_version.py 3.2.0

    # Set dev version
    python scripts/bump_version.py 3.3.0.dev

generate_changelog.py
~~~~~~~~~~~~~~~~~~~~~

Generates changelog from git history:

.. code-block:: bash

    # Generate from all commits
    python scripts/generate_changelog.py

    # Generate from specific tag
    python scripts/generate_changelog.py --from v3.1.0

    # Output to file
    python scripts/generate_changelog.py --output CHANGES.md

rollback.py
~~~~~~~~~~~

Yanks a release from PyPI:

.. code-block:: bash

    # Yank version
    python scripts/rollback.py 3.2.0

    # Dry run (preview)
    python scripts/rollback.py 3.2.0 --dry-run

bootstrap.py
~~~~~~~~~~~~

Sets up development environment:

.. code-block:: bash

    # Run bootstrap
    python scripts/bootstrap.py

This:

- Creates virtual environment
- Installs dependencies
- Installs pre-commit hooks
- Runs initial tests

Release Checklist
-----------------

Use this checklist for each release:

**Pre-release**:

- [ ] All PRs for this release are merged
- [ ] Changelog is updated and reviewed
- [ ] Version is bumped in all files
- [ ] Tests pass locally
- [ ] Benchmarks show no regressions
- [ ] Type hints are correct
- [ ] Documentation is updated

**Release**:

- [ ] Release branch PR is approved
- [ ] Release branch is merged
- [ ] Tag is created and pushed
- [ ] CI publish workflow succeeds
- [ ] PyPI release is verified
- [ ] GitHub release is created

**Post-release**:

- [ ] Next dev version is bumped
- [ ] Release is announced
- [ ] Documentation site is updated
- [ ] Monitor for issues (first 24 hours)

Security Releases
-----------------

For security vulnerabilities:

1. **Do not** create a public PR
2. Fix in private fork
3. Coordinate with security team
4. Release without advance notice
5. Publish security advisory
6. Notify affected users via security mailing list

See `Security Policy <https://github.com/pallets/flask/security/policy>`_ for details.

See Also
--------

- :doc:`/contributing` - Contribution guidelines
- :doc:`/changelog` - Version history
