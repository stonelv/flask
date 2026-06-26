"""Validate release readiness before publishing.

Usage: python scripts/ci/validate_release.py <tag-name>

Runs as the first job in the publish workflow to catch problems
before building or uploading anything.

Checks:
  1. Tag matches the version in pyproject.toml
  2. Version has no .dev suffix
  3. CHANGES.rst contains an entry for this version
  4. No leftover changelog fragments in changelog.d/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
CHANGES = Path("CHANGES.rst")
CHANGELOG_DIR = Path("changelog.d")


def get_pyproject_version() -> str:
    content = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        sys.exit("Error: could not find version in pyproject.toml")
    return match.group(1)


def check_changelog(version: str) -> bool:
    if not CHANGES.exists():
        return False
    return f"Version {version}" in CHANGES.read_text()


def check_no_leftover_fragments() -> list[str]:
    """Return any .rst fragments still in changelog.d/ (should have been
    consumed by towncrier)."""
    if not CHANGELOG_DIR.is_dir():
        return []
    return [
        str(p)
        for p in CHANGELOG_DIR.glob("*.rst")
        if p.name != "_template.rst"
    ]


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tag-name>")
        sys.exit(1)

    tag = sys.argv[1]
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Version matches tag
    pyproject_version = get_pyproject_version()
    if pyproject_version != tag:
        errors.append(
            f"Version mismatch: pyproject.toml has '{pyproject_version}' "
            f"but tag is '{tag}'"
        )

    # 2. No .dev suffix
    if ".dev" in pyproject_version:
        errors.append(
            f"Development version '{pyproject_version}' cannot be released"
        )

    # 3. Changelog entry
    if not check_changelog(tag):
        errors.append(
            f"No changelog entry for 'Version {tag}' in CHANGES.rst"
        )

    # 4. No leftover fragments
    leftovers = check_no_leftover_fragments()
    if leftovers:
        warnings.append(
            f"{len(leftovers)} changelog fragment(s) not consumed: "
            + ", ".join(leftovers)
        )

    # Report
    if errors:
        print("Release validation FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        for w in warnings:
            print(f"  ⚠ {w}")
        sys.exit(1)

    print(f"Release validation passed for {tag}")
    print(f"  ✓ pyproject.toml version = {pyproject_version}")
    print("  ✓ No .dev suffix")
    print("  ✓ Changelog entry exists")
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
