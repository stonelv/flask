"""End-to-end dry-run tests for the release and rollback scripts.

These build a throwaway git repository, copy the scripts in, and exercise their
real control flow via ``bash`` — clean/dirty tree, ``.dev`` rejection, the
dry-run vs ``--execute`` boundary, and rollback's dry-run safety. They never
touch the real repository. Skipped where ``bash``/``git`` are unavailable
(e.g. Windows CI runners).
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(__file__))

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("git") is None,
    reason="needs bash and git",
)

PYPROJECT = '[project]\nname = "Flask"\nversion = "{ver}"\n'
CHANGES = "Version {ver}\n{ul}\n\nReleased 2026-01-01\n\n-   Something. :pr:`1`\n"


def _run(script, *args, cwd):
    return subprocess.run(
        ["bash", script, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _make_repo(tmp_path, version):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in ("release.sh", "rollback.sh"):
        shutil.copy(f"{_ROOT}/scripts/{name}", repo / "scripts" / name)
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(ver=version), encoding="utf-8"
    )
    (repo / "CHANGES.rst").write_text(
        CHANGES.format(ver=version, ul="-" * (len("Version ") + len(version))),
        encoding="utf-8",
    )
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
        env={**os.environ, **env},
    )
    return repo


def _tags(repo):
    out = subprocess.run(
        ["git", "tag"], cwd=repo, capture_output=True, text=True
    ).stdout
    return out.split()


def test_release_dry_run_passes_and_creates_no_tag(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    r = _run("scripts/release.sh", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "dry-run only" in r.stdout
    assert "suggest" in r.stdout
    assert _tags(repo) == []  # dry-run must not tag


def test_release_execute_creates_tag(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    r = _run("scripts/release.sh", "--execute", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "1.2.3" in _tags(repo)


def test_release_rejects_dev_version(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3.dev")
    r = _run("scripts/release.sh", cwd=repo)
    assert r.returncode != 0
    assert "dev version" in r.stderr


def test_release_rejects_dirty_tree(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(ver="1.2.3") + "# dirty\n", encoding="utf-8"
    )
    r = _run("scripts/release.sh", cwd=repo)
    assert r.returncode != 0
    assert "not clean" in r.stderr


def test_release_requires_changelog_section(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    (repo / "CHANGES.rst").write_text(
        "Version 0.0.1\n-------------\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        cwd=repo,
        check=True,
    )
    r = _run("scripts/release.sh", cwd=repo)
    assert r.returncode != 0
    assert "CHANGES.rst" in r.stderr


def test_rollback_dry_run_is_safe(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    # create a tag so rollback has something to (pretend to) remove
    subprocess.run(["git", "tag", "1.2.3"], cwd=repo, check=True)
    r = _run("scripts/rollback.sh", "1.2.3", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "dry-run" in r.stdout
    assert "1.2.3" in _tags(repo)  # dry-run must NOT delete the tag


def test_rollback_requires_version_arg(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")
    r = _run("scripts/rollback.sh", cwd=repo)
    assert r.returncode == 2
