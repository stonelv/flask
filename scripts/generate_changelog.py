#!/usr/bin/env python3
"""
Changelog generator for Flask releases.

Generates changelog entries from git commits between the last tag and HEAD.
Groups commits by type (feat, fix, docs, etc.) following conventional commits.

Usage:
    python scripts/generate_changelog.py [from_tag] [to_ref]

Examples:
    python scripts/generate_changelog.py  # from last tag to HEAD
    python scripts/generate_changelog.py v3.0.0 v3.1.0
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
CHANGES_FILE = ROOT / "CHANGES.rst"

# Conventional commit types and their display names
COMMIT_TYPES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "style": "Code Style",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build System",
    "ci": "CI/CD",
    "chore": "Chores",
    "revert": "Reverts",
}


def run_git(args: list[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_last_tag() -> Optional[str]:
    """Get the most recent git tag."""
    try:
        return run_git(["describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def get_commits(from_ref: str, to_ref: str = "HEAD") -> list[dict]:
    """Get commits between two refs."""
    # Format: hash|subject|body
    log_format = "%H|%s|%b"
    output = run_git(["log", f"{from_ref}..{to_ref}", f"--pretty=format:{log_format}"])

    if not output:
        return []

    commits = []
    for line in output.split("\n"):
        if not line.strip():
            continue

        parts = line.split("|", 2)
        if len(parts) < 2:
            continue

        commit_hash, subject = parts[0], parts[1]
        body = parts[2] if len(parts) > 2 else ""

        # Parse conventional commit format: type(scope): description
        match = re.match(r"^(\w+)(?:\([^)]+\))?:\s*(.+)$", subject)
        if match:
            commit_type, description = match.groups()
            commit_type = commit_type.lower()
        else:
            # Default to "chore" if not conventional
            commit_type = "chore"
            description = subject

        commits.append(
            {
                "hash": commit_hash[:7],  # Short hash
                "full_hash": commit_hash,
                "type": commit_type,
                "description": description,
                "subject": subject,
                "body": body,
            }
        )

    return commits


def group_commits(commits: list[dict]) -> dict[str, list[dict]]:
    """Group commits by type."""
    groups = defaultdict(list)
    for commit in commits:
        groups[commit["type"]].append(commit)
    return dict(groups)


def format_changelog_entry(version: str, groups: dict[str, list[dict]]) -> str:
    """Format changelog entry in reStructuredText format."""
    lines = []
    lines.append(f"Version {version}")
    lines.append("-" * len(lines[0]))
    lines.append("")
    lines.append("Released on YYYY-MM-DD")
    lines.append("")

    # Order: feat, fix, docs, then others alphabetically
    type_order = ["feat", "fix", "docs", "refactor", "perf", "test", "style", "build", "ci", "chore", "revert"]

    for commit_type in type_order:
        if commit_type not in groups:
            continue

        display_name = COMMIT_TYPES.get(commit_type, commit_type.title())
        commits = groups[commit_type]

        lines.append(f"**{display_name}**")
        lines.append("")

        for commit in commits:
            # Format: - Description (#hash)
            lines.append(f"- {commit['description']} (`#{commit['hash']} <https://github.com/pallets/flask/commit/{commit['full_hash']}>`_)")

        lines.append("")

    return "\n".join(lines)


def prepend_to_changes_file(new_entry: str, dry_run: bool = False) -> None:
    """Prepend new changelog entry to CHANGES.rst."""
    if not CHANGES_FILE.exists():
        if dry_run:
            print(f"[dry-run] Would create CHANGES.rst")
        else:
            print(f"⚠ CHANGES.rst not found, creating new file")
            CHANGES_FILE.write_text(new_entry)
        return

    content = CHANGES_FILE.read_text()

    # Find the first version entry (starts with "Version X.Y.Z")
    match = re.search(r"^Version \d+\.\d+\.\d+", content, re.MULTILINE)
    if match:
        # Insert before the first version entry
        insert_pos = match.start()
        content = content[:insert_pos] + new_entry + "\n\n" + content[insert_pos:]
    else:
        # No existing version entries, just prepend
        content = new_entry + "\n\n" + content

    if not dry_run:
        CHANGES_FILE.write_text(content)
        print(f"✓ Updated CHANGES.rst")
    else:
        print(f"[dry-run] Would update CHANGES.rst")


def main():
    parser = argparse.ArgumentParser(
        description="Generate changelog from git commits.",
        epilog="""Examples:
  generate_changelog.py                  # from last tag to HEAD
  generate_changelog.py v3.0.0 v3.1.0    # specific range
  generate_changelog.py --dry-run        # preview without writing""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "from_ref",
        nargs="?",
        help="Starting git ref (tag or commit). Defaults to last tag.",
    )
    parser.add_argument(
        "to_ref",
        nargs="?",
        default="HEAD",
        help="Ending git ref (tag or commit). Defaults to HEAD.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    args = parser.parse_args()

    from_ref = args.from_ref or get_last_tag()
    to_ref = args.to_ref

    if not from_ref:
        print("Error: No previous tag found and no from_ref specified", file=sys.stderr)
        sys.exit(1)

    print(f"Generating changelog from {from_ref} to {to_ref}\n")

    commits = get_commits(from_ref, to_ref)
    if not commits:
        print("No commits found in range")
        sys.exit(0)

    print(f"Found {len(commits)} commits\n")

    groups = group_commits(commits)

    # Use the to_ref as version (strip 'v' prefix if present)
    version = to_ref.lstrip("v") if to_ref != "HEAD" else "Unreleased"

    entry = format_changelog_entry(version, groups)

    # Print to stdout
    print("Generated changelog entry:")
    print("=" * 60)
    print(entry)
    print("=" * 60)
    print()

    if args.dry_run:
        print("[dry-run] No files were modified")
        return

    # Ask if user wants to update CHANGES.rst
    if to_ref == "HEAD":
        print("This is a preview (to_ref=HEAD). Run with specific version to update CHANGES.rst")
    else:
        response = input("Update CHANGES.rst? [y/N] ")
        if response.lower() == "y":
            prepend_to_changes_file(entry)
            print(f"\n✅ Changelog updated")
            print("\nNext steps:")
            print("  1. Review and edit CHANGES.rst")
            print("  2. Commit: git commit -am 'Update changelog for {version}'")


if __name__ == "__main__":
    main()
