#!/usr/bin/env python3
"""
Release rollback script for Flask.

Rolls back a release by:
1. Deleting the git tag
2. Reverting version bump commit (optional)
3. Providing instructions for PyPI yanking

Usage:
    python scripts/rollback.py <version>

Example:
    python scripts/rollback.py 3.1.0
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if check and result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)

    return result


def delete_git_tag(version: str, push: bool = True) -> None:
    """Delete a git tag locally and remotely."""
    tag_name = f"v{version}" if not version.startswith("v") else version

    # Delete local tag
    result = run_command(["git", "tag", "-d", tag_name], check=False)
    if result.returncode == 0:
        print(f"✓ Deleted local tag: {tag_name}")
    else:
        print(f"⚠ Local tag {tag_name} not found or already deleted")

    # Delete remote tag
    if push:
        result = run_command(
            ["git", "push", "origin", ":refs/tags/" + tag_name],
            check=False,
        )
        if result.returncode == 0:
            print(f"✓ Deleted remote tag: {tag_name}")
        else:
            print(f"⚠ Could not delete remote tag {tag_name} (may not exist)")


def revert_version_commit(version: str) -> None:
    """Find and revert the version bump commit."""
    # Find commit that bumped to this version
    result = run_command(
        ["git", "log", "--all", "--grep=Release version", "--grep=version", "--oneline"],
        check=False,
    )

    if result.returncode != 0 or not result.stdout:
        print("⚠ Could not find version bump commit")
        return

    # Look for the specific version in the log
    commits = result.stdout.strip().split("\n")
    target_commit = None
    for commit_line in commits:
        if version in commit_line:
            target_commit = commit_line.split()[0]
            break

    if not target_commit:
        print(f"⚠ Could not find commit for version {version}")
        return

    print(f"Found version bump commit: {target_commit}")

    # Show the commit
    run_command(["git", "show", target_commit, "--stat"])

    response = input(f"\nRevert commit {target_commit}? This will create a revert commit. [y/N] ")
    if response.lower() != "y":
        print("Skipping revert")
        return

    # Revert the commit
    result = run_command(
        ["git", "revert", target_commit, "--no-edit"],
        check=False,
    )

    if result.returncode == 0:
        print(f"✓ Reverted commit {target_commit}")
        print("\nTo push the revert:")
        print("  git push origin main")
    else:
        print("⚠ Revert failed (may have conflicts)")
        print("Resolve conflicts manually and commit with:")
        print("  git revert --continue")


def provide_pypi_instructions(version: str) -> None:
    """Provide instructions for yanking the PyPI release."""
    print("\n" + "=" * 60)
    print("PyPI Release Rollback Instructions")
    print("=" * 60)
    print()
    print("To yank (hide) the release from PyPI:")
    print()
    print(f"  1. Go to https://pypi.org/manage/project/flask/release/{version}/")
    print(f"  2. Click 'Options' → 'Yank'")
    print(f"  3. Provide a reason: 'Rolled back due to issues'")
    print()
    print("Or use the PyPI API:")
    print()
    print(f"  curl -X POST https://pypi.org/simple/flask/{version}/ \\")
    print(f"    -H 'Authorization: Bearer $PYPI_TOKEN' \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"yank\": true, \"yank_comment\": \"Rolled back\"}}'")
    print()
    print("Note: Yanking hides the release but doesn't delete it.")
    print("      Users with pinned versions can still install it.")
    print()
    print("To completely delete (not recommended):")
    print()
    print(f"  pip install twine")
    print(f"  twine delete flask {version}")
    print()
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: rollback.py <version>")
        print("Example: rollback.py 3.1.0")
        sys.exit(1)

    version = sys.argv[1].lstrip("v")
    print(f"Rolling back version: {version}\n")

    # Confirm
    print("This will:")
    print(f"  1. Delete git tag v{version} (local and remote)")
    print(f"  2. Optionally revert the version bump commit")
    print(f"  3. Provide instructions for yanking PyPI release")
    print()

    response = input("Continue? [y/N] ")
    if response.lower() != "y":
        print("Aborted")
        sys.exit(0)

    print()

    # Step 1: Delete git tag
    print("Step 1: Deleting git tag")
    print("-" * 60)
    delete_git_tag(version, push=True)
    print()

    # Step 2: Optionally revert version commit
    print("Step 2: Revert version bump commit (optional)")
    print("-" * 60)
    revert_version_commit(version)
    print()

    # Step 3: PyPI instructions
    print("Step 3: PyPI rollback")
    print("-" * 60)
    provide_pypi_instructions(version)

    print("\n✅ Rollback process initiated")
    print("\nRemaining manual steps:")
    print("  1. Complete PyPI yanking (instructions above)")
    print("  2. Notify users if this was a public release")
    print("  3. Update CHANGES.rst to remove the release entry")
    print("  4. Create a new patch release if needed")


if __name__ == "__main__":
    main()
