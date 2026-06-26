#!/usr/bin/env python3
"""Release rollback runbook generator.

PyPI cannot un-publish a released file: a broken release is rolled back by
**yank + retract** on PyPI, **reverting** the release commit on the main
branch, and **republishing** a patch release that contains the revert. This
script produces that runbook (and, with ``--apply``, executes the safe local
parts -- it never auto-pushes tags or yanks without explicit flags).

Usage::

    python scripts/rollback.py --version 3.2.1            # print runbook
    python scripts/rollback.py --version 3.2.1 --apply   # also do the local git revert
    python scripts/rollback.py --version 3.2.1 --yank    # requires PYPI_API_TOKEN
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def release_commit(version: str) -> str | None:
    """Return the hash of the commit that tagged ``v<version>``."""
    out = subprocess.run(
        ["git", "rev-list", "-n", "1", f"v{version}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    h = out.stdout.strip()
    return h or None


def runbook(version: str, commit: str | None, has_token: bool) -> str:
    lines = [
        f"# Rollback runbook for Flask {version}",
        "",
        "PyPI files cannot be deleted; rollback = yank/retract + git revert + "
        "republish a patch. Execute the steps below in order.",
        "",
        "## 1. Stop the bleeding (PyPI yank / retract)",
        "",
        "Yank makes the release uninstallable for new ``pip install`` resolves "
        "but leaves it available for already-pinned users.",
        "",
        f"- Web UI: https://pypi.org/manage/project/flask/release/{version}/yank/",
    ]
    if has_token:
        lines.append(
            f"- API: ``scripts/rollback.py --version {version} --yank`` "
            "(uses PYPI_API_TOKEN)"
        )
    else:
        lines.append(
            "- API: set PYPI_API_TOKEN and re-run with ``--yank`` "
            "(trusted publishing cannot yank; a long-lived token or the "
            "web UI is required)."
        )
    lines += [
        "",
        "## 2. Revert the release commit",
        "",
    ]
    if commit:
        lines.append(f"The release was tagged at commit ``{commit}``.")
        lines.append("If it was a merge commit:")
        lines.append(f"    git revert -m 1 {commit}")
        lines.append("If it was a plain commit:")
        lines.append(f"    git revert {commit}")
    else:
        lines.append(
            f"Tag ``v{version}`` not found locally; locate the release "
            f"commit with ``git log -- v{version}`` and revert it."
        )

    next_patch = _next_patch(version)
    next_next_dev = _next_patch(next_patch) + ".dev"
    lines += [
        "",
        "## 3. Republish a patch release on the revert branch",
        "",
        "On the branch containing the revert, run the two-phase release pipeline",
        "(so the tag points at a clean-version commit, not the next .dev):",
        "",
        "    python scripts/changes.py bump --level patch --apply",
        f"    #   release-prep: version -> {next_patch} (clean, tagged)",
        f"    git commit -am 'Release {next_patch} (rollback of {version})'",
        f"    git tag v{next_patch}",
        f"    python scripts/changes.py start-dev --next-dev {next_next_dev} --apply",
        f"    git commit -am 'Start {next_next_dev} dev'",
        f"    git push origin <branch> v{next_patch}",
        "",
        "The tag push triggers ``.github/workflows/publish.yaml``; the "
        "``environment: publish`` approval gate is the hard stop before PyPI.",
        "",
        "## 4. Communicate",
        "",
        "- Edit the GitHub release notes for ``v"
        + version
        + "`` to point to ``v"
        + next_patch
        + "``.",
        "- Open a security/ops advisory if the release shipped a correctness "
        "or security bug.",
    ]
    return "\n".join(lines)


def _next_patch(version: str) -> str:
    major, minor, patch = (int(p) for p in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def do_local_revert(commit: str) -> None:
    """Attempt a plain ``git revert`` (works for non-merge commits)."""
    print(f"running: git revert --no-edit {commit}")
    subprocess.run(["git", "revert", "--no-edit", commit], cwd=ROOT, check=True)


def do_yank(version: str, token: str) -> None:
    """Yank all files for ``version`` via the PyPI JSON API + token."""
    import json
    import urllib.request

    url = f"https://pypi.org/pypi/flask/{version}/json"
    with urllib.request.urlopen(url) as resp:  # noqa: S310 (trusted https URL)
        data = json.load(resp)
    for f in data.get("urls", []):
        filename = f["filename"]
        req = urllib.request.Request(
            f"https://pypi.org/simple/flask/{filename}/",
            method="POST",
            headers={"Authorization": f"token {token}"},
            data=b'{"yanked":true,"yanked_reason":"rolled back"}',
        )
        try:
            urllib.request.urlopen(req)
            print(f"yanked {filename}")
        except Exception as exc:  # noqa: BLE001
            print(f"yank failed for {filename}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", required=True, help="released version to roll back, e.g. 3.2.1"
    )
    parser.add_argument("--apply", action="store_true", help="run the local git revert")
    parser.add_argument(
        "--yank", action="store_true", help="yank on PyPI (needs PYPI_API_TOKEN)"
    )
    args = parser.parse_args()

    import os

    token = os.environ.get("PYPI_API_TOKEN", "")
    commit = release_commit(args.version)

    if args.yank:
        if not token:
            print("PYPI_API_TOKEN is required for --yank", file=sys.stderr)
            return 2
        do_yank(args.version, token)

    if args.apply and commit:
        do_local_revert(commit)
    elif args.apply and not commit:
        print(
            f"no tag v{args.version} found; cannot auto-revert. "
            "Run `git fetch --tags` or locate the release commit manually.",
            file=sys.stderr,
        )

    print(runbook(args.version, commit, has_token=bool(token)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
