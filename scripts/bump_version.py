#!/usr/bin/env python3
"""
Version bumping script for Flask releases.

Updates version in:
- pyproject.toml
- src/flask/__init__.py (__version__)
- docs/conf.py (version/release)

Usage:
    python scripts/bump_version.py [major|minor|patch]
    python scripts/bump_version.py 3.1.0  # specific version
"""

import re
import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).parent.parent


def parse_version(version: str) -> tuple[int, int, int, str]:
    """Parse version string into (major, minor, patch, suffix) tuple."""
    # Match X.Y.Z or X.Y.Z.suffix or X.Y.Z-suffix
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[.-](.+))?$", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        match.group(4) or "",
    )


def bump_version(
    current: tuple[int, int, int, str],
    bump_type: Literal["major", "minor", "patch"],
    dev: bool = False,
) -> tuple[int, int, int, str]:
    """Bump version according to semver rules."""
    major, minor, patch, suffix = current

    # If current is a dev version, strip suffix for bump calculation
    if suffix and bump_type in ("major", "minor", "patch"):
        suffix = ""

    if bump_type == "major":
        return (major + 1, 0, 0, "dev" if dev else "")
    elif bump_type == "minor":
        return (major, minor + 1, 0, "dev" if dev else "")
    elif bump_type == "patch":
        return (major, minor, patch + 1, "dev" if dev else "")
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    pyproject_path = ROOT / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find version in pyproject.toml")
    return match.group(1)


def update_pyproject_toml(new_version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = ROOT / "pyproject.toml"
    content = pyproject_path.read_text()
    content = re.sub(
        r'^version = "[^"]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(content)
    print(f"✓ Updated pyproject.toml to {new_version}")


def update_init_py(new_version: str) -> None:
    """Update __version__ in src/flask/__init__.py."""
    init_path = ROOT / "src" / "flask" / "__init__.py"
    content = init_path.read_text()
    content = re.sub(
        r'^__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    init_path.write_text(content)
    print(f"✓ Updated src/flask/__init__.py to {new_version}")


def update_docs_conf(new_version: str) -> None:
    """Update version in docs/conf.py."""
    conf_path = ROOT / "docs" / "conf.py"
    if not conf_path.exists():
        print(f"⚠ Skipping docs/conf.py (not found)")
        return

    content = conf_path.read_text()

    # Update version (short version: X.Y)
    parts = new_version.split(".")
    short_version = f"{parts[0]}.{parts[1]}"

    content = re.sub(
        r'^version = "[^"]*"',
        f'version = "{short_version}"',
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r'^release = "[^"]*"',
        f'release = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    conf_path.write_text(content)
    print(f"✓ Updated docs/conf.py to {new_version}")


def main():
    if len(sys.argv) < 2:
        print("Usage: bump_version.py [major|minor|patch] [--dev]")
        print("       bump_version.py X.Y.Z")
        print("\nExamples:")
        print("  bump_version.py patch          # 3.2.0 -> 3.2.1")
        print("  bump_version.py minor --dev    # 3.2.0 -> 3.3.0.dev")
        print("  bump_version.py 3.1.0          # Set to specific version")
        sys.exit(1)

    arg = sys.argv[1]
    dev = "--dev" in sys.argv
    current = get_current_version()
    print(f"Current version: {current}")

    # Check if arg is a specific version or a bump type
    if arg in ("major", "minor", "patch"):
        current_tuple = parse_version(current)
        new_tuple = bump_version(current_tuple, arg, dev=dev)
        major, minor, patch, suffix = new_tuple
        new_version = f"{major}.{minor}.{patch}"
        if suffix:
            new_version += f".{suffix}"
    else:
        # Validate the provided version
        try:
            parse_version(arg)
            new_version = arg
        except ValueError:
            print(f"Error: '{arg}' is not a valid version or bump type")
            sys.exit(1)

    print(f"Bumping to: {new_version}\n")

    # Update all version locations
    update_pyproject_toml(new_version)
    update_init_py(new_version)
    update_docs_conf(new_version)

    print(f"\n✅ Version bumped to {new_version}")
    print("\nNext steps:")
    print(f"  1. Update CHANGES.rst with release notes")
    print(f"  2. Commit: git commit -am 'Release version {new_version}'")
    if not dev:
        print(f"  3. Tag: git tag -a v{new_version} -m 'Version {new_version}'")
        print(f"  4. Push: git push origin main --tags")
    else:
        print(f"  3. Push: git push origin main")


if __name__ == "__main__":
    main()
