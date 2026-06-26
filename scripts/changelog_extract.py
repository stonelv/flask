#!/usr/bin/env python3
"""Extract one version's section from CHANGES.rst for release notes.

The Pallets changelog uses RST headings like::

    Version 3.2.0
    -------------

    Released 2026-06-23

    -   Some change. :pr:`1234`

This prints the body of the requested version's section (everything up to the
next ``Version ...`` heading), so the publish workflow can use it as the GitHub
release notes without hand-copying.

Usage:
    python scripts/changelog_extract.py 3.2.0 [CHANGES.rst]
"""

from __future__ import annotations

import re
import sys


def extract(version: str, text: str) -> str:
    lines = text.splitlines()
    head = re.compile(r"^Version\s+(.+?)\s*$")
    start = None
    for i, line in enumerate(lines):
        m = head.match(line)
        if m and m.group(1) == version:
            start = i
            break
    if start is None:
        raise SystemExit(f"changelog: no 'Version {version}' section found")

    # body starts after the heading + its underline
    body_start = start + 2
    end = len(lines)
    for j in range(body_start, len(lines)):
        if head.match(lines[j]):
            end = j
            break

    body = "\n".join(lines[body_start:end]).strip()
    return body


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    version = argv[1]
    path = argv[2] if len(argv) > 2 else "CHANGES.rst"
    with open(path, encoding="utf-8") as fh:
        print(extract(version, fh.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
