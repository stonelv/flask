"""Validate release readiness before publishing.

Usage: python scripts/ci/validate_release.py <tag-name>

Checks:
  - Tag matches version in pyproject.toml
  - No .dev suffix in release version
  - Changelog entry exists for this version
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
CHANGES = Path("CHANGES.rst")


def get_pyproject_version() -> str:
    """Extract version from pyproject.toml."""
    content = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("Error: could not find version in pyproject.toml")
        sys.exit(1)
    return match.group(1)


def check_changelog(version: str) -> bool:
    """Check that CHANGES.rst contains an entry for this version."""
    if not CHANGES.exists():
        return False
    content = CHANGES.read_text()
    # Look for "Version X.Y.Z" header
    return f"Version {version}" in content


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tag-name>")
        sys.exit(1)

    tag = sys.argv[1]
    errors = []

    # Check version matches tag
    pyproject_version = get_pyproject_version()
    if pyproject_version != tag:
        errors.append(
            f"Version mismatch: pyproject.toml has '{pyproject_version}' "
            f"but tag is '{tag}'"
        )

    # Check no .dev suffix
    if ".dev" in pyproject_version:
        errors.append(
            f"Development version '{pyproject_version}' cannot be released. "
            f"Remove .dev suffix first."
        )

    # Check changelog
    if not check_changelog(tag):
        errors.append(f"No changelog entry found for 'Version {tag}' in CHANGES.rst")

    if errors:
        print("Release validation FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"Release validation passed for {tag}")
        print("  ✓ pyproject.toml version matches tag")
        print("  ✓ No .dev suffix")
        print("  ✓ Changelog entry exists")


if __name__ == "__main__":
    main()
