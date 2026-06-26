#!/usr/bin/env python3
"""Generate GitHub release notes for a released version.

Thin wrapper around ``scripts/changes.py notes``: extracts the ``Released``
section for ``--version`` from ``CHANGES.rst`` and writes markdown to stdout.
The release workflow pipes this into ``gh release edit --notes-file``.

Usage::

    python scripts/release_notes.py --version 3.2.0 > notes.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES_PY = ROOT / "scripts" / "changes.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="released version, e.g. 3.2.0")
    args = parser.parse_args()

    result = subprocess.run(
        [sys.executable, str(CHANGES_PY), "notes", "--version", args.version],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
