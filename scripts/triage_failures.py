#!/usr/bin/env python3
"""Attribute failing tests to their most recent author and module.

Reads a pytest JUnit-XML report, finds failures/errors, and for each one uses
``git blame`` on the failing line to identify the last author. Results are
grouped by test module and written as a Markdown summary to the file named by
``$GITHUB_STEP_SUMMARY`` (or stdout when run locally).

Designed to degrade gracefully: if blame is unavailable (e.g. a shallow
checkout), it still emits the failure list without attribution. It never exits
non-zero, so it can run as an ``if: failure()`` step without masking the real
test result.

Usage:
    python scripts/triage_failures.py [junit.xml]   # default: junit.xml
"""

from __future__ import annotations

import collections
import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def blame_author(path: str, line: int | None) -> str | None:
    """Return the last author of ``path`` (at ``line`` if given), or None."""
    if not path or not os.path.exists(path):
        return None
    cmd = ["git", "blame", "--porcelain"]
    if line:
        cmd += ["-L", f"{line},{line}"]
    cmd.append(path)
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    for row in out.splitlines():
        if row.startswith("author "):
            return row[len("author ") :].strip()
    return None


def parse_failures(xml_path: str) -> list[dict[str, object]]:
    """Extract failing/erroring test cases from a JUnit-XML report."""
    tree = ET.parse(xml_path)
    failures: list[dict[str, object]] = []
    for case in tree.iter("testcase"):
        problems = case.findall("failure") + case.findall("error")
        if not problems:
            continue
        line_attr = case.get("line")
        failures.append(
            {
                "module": case.get("classname", "") or "unknown",
                "name": case.get("name", "") or "unknown",
                "file": case.get("file", "") or "",
                "line": int(line_attr) + 1 if line_attr is not None else None,
                "message": (problems[0].get("message") or "").splitlines()[0:1],
            }
        )
    return failures


def render(failures: list[dict[str, object]]) -> str:
    if not failures:
        return "## ✅ Test triage\n\nNo failing tests found in the report.\n"

    by_module: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    for f in failures:
        author = blame_author(str(f["file"]), f["line"])  # type: ignore[arg-type]
        f["author"] = author or "unknown"
        by_module[str(f["module"])].append(f)

    lines = [f"## ❌ Test triage — {len(failures)} failing\n"]
    for module in sorted(by_module):
        cases = by_module[module]
        authors = sorted({str(c["author"]) for c in cases})
        lines.append(f"### `{module}` — likely owner: {', '.join(authors)}\n")
        lines.append("| Test | Last author | Location |")
        lines.append("|------|-------------|----------|")
        for c in cases:
            loc = f"{c['file']}:{c['line']}" if c["line"] else (c["file"] or "—")
            lines.append(f"| `{c['name']}` | {c['author']} | `{loc}` |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    xml_path = argv[1] if len(argv) > 1 else "junit.xml"
    if not os.path.exists(xml_path):
        print(f"triage: report '{xml_path}' not found; nothing to do.")
        return 0
    try:
        failures = parse_failures(xml_path)
    except ET.ParseError as exc:
        print(f"triage: could not parse '{xml_path}': {exc}")
        return 0

    summary = render(failures)
    out_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(summary)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
