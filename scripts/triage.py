#!/usr/bin/env python3
"""Failed-test auto-attribution.

Parses JUnit XML produced by ``pytest --junit-xml``, maps each failing test to
its owning source module (via a static test->module map that encodes this
repo's naming exceptions), resolves reviewers from ``.github/CODEOWNERS``
(longest-prefix match), and falls back to ``git log`` on the mapped source file
when no CODEOWNERS entry matches. Emits a Markdown table to stdout -- the CI
step appends it to ``$GITHUB_STEP_SUMMARY``.

The test->module map encodes the non-obvious mappings in this repo:

    test_basic / test_user_error_handler / test_subclassing / test_converters /
    test_async / test_regression  ->  src/flask/app.py
    test_appctx / test_reqctx     ->  src/flask/ctx.py
    test_request                  ->  src/flask/wrappers.py   (NOT a request.py)

For anything else the default rule is ``src/flask/<stem-without-test_>.py``;
if that file does not exist on disk, the failure is treated as tests-only and
attributed to the test file itself.

Degrades gracefully: no junit files -> exit 0 ("no failures"); missing
CODEOWNERS -> blame-only; shallow checkout -> blame reports a hint instead of
crashing.

Usage::

    python scripts/triage.py --junit test-results            # dir of junit-*.xml
    python scripts/triage.py --junit junit-py3.14.xml        # single file
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"

# Static test-stem -> source-module map (the exceptions; default rule below).
TEST_TO_MODULE: dict[str, str] = {
    "test_basic": "src/flask/app.py",
    "test_user_error_handler": "src/flask/app.py",
    "test_subclassing": "src/flask/app.py",
    "test_converters": "src/flask/app.py",
    "test_async": "src/flask/app.py",
    "test_regression": "src/flask/app.py",
    "test_appctx": "src/flask/ctx.py",
    "test_reqctx": "src/flask/ctx.py",
    "test_request": "src/flask/wrappers.py",
}


def module_for_test(stem: str, repo_root: Path) -> str:
    """Return the source module path a failing test stem is most likely about.

    Falls back to the test file itself when the default-derived path does not
    exist (tests-only changes).
    """
    if stem in TEST_TO_MODULE:
        return TEST_TO_MODULE[stem]
    default = f"src/flask/{stem.removeprefix('test_')}.py"
    if (repo_root / default).exists():
        return default
    return f"tests/{stem}.py"


def parse_codeowners(path: Path) -> list[tuple[str, list[str]]]:
    """Return ``[(pattern, [owners])]`` preserving file order (last match wins)."""
    if not path.exists():
        return []
    rules: list[tuple[str, list[str]]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        pattern = parts[0]
        owners = [p for p in parts[1:] if p.startswith("@")]
        rules.append((pattern, owners))
    return rules


def match_codeowners(path: str, rules) -> list[str]:
    """Longest-matching-pattern-wins CODEOWNERS resolution."""
    best: tuple[int, list[str]] = (-1, [])
    for pattern, owners in rules:
        if _matches(path, pattern):
            # prefer the most specific (longest) pattern
            score = len(pattern.replace("**", "").replace("*", ""))
            if score >= best[0]:
                best = (score, owners)
    return best[1]


def _matches(path: str, pattern: str) -> bool:
    """Minimal CODEOWNERS-style matcher: ``*`` in one segment, ``**`` across."""
    # Normalize: a trailing dir pattern like ``/src/flask/`` matches everything
    # under that dir.
    if pattern.endswith("/"):
        pattern = pattern + "**"
    pattern = pattern.removeprefix("/")
    if "**" in pattern:
        regex = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        return re.fullmatch(regex, path) is not None
    # segment-wise fnmatch
    return fnmatch.fnmatch(path, pattern)


def git_last_change(repo_root: Path, path: str) -> str:
    """Return ``'<short-hash> | <author> <<email>> | <date>'`` or a hint."""
    try:
        out = subprocess.run(
            [
                "git", "log", "-1",
                "--format=%h · %an <%ae> · %ad",
                "--date=short",
                "--", path,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "git unavailable"
    result = out.stdout.strip()
    if not result:
        return "no history (shallow checkout?)"
    return result


def collect_failures(junit_paths: list[Path]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for jp in junit_paths:
        tree = ElementTree.parse(jp)
        for tc in tree.iter("testcase"):
            failure = tc.find("failure")
            error = tc.find("error")
            if failure is None and error is None:
                continue
            classname = tc.get("classname", "")
            stem = classname.rsplit(".", 1)[-1] or Path(tc.get("file", "x.py")).stem
            name = tc.get("name", "")
            nodeid = f"{classname}::{name}" if classname else name
            kind = "error" if error is not None else "failure"
            failures.append({"nodeid": nodeid, "stem": stem, "kind": kind})
    return failures


def build_report(failures: list[dict[str, str]]) -> str:
    if not failures:
        return "## Test failure auto-attribution\n\nNo failures detected."

    rules = parse_codeowners(CODEOWNERS)
    lines = [
        "## Test failure auto-attribution",
        "",
        "| Failing test | Source module | CODEOWNERS | Last change |",
        "|---|---|---|---|",
    ]
    suggested: set[str] = set()
    for f in failures:
        module = module_for_test(f["stem"], ROOT)
        owners = match_codeowners(module, rules)
        last = git_last_change(ROOT, module)
        owners_str = " ".join(owners) if owners else "-"
        suggested.update(owners)
        lines.append(
            f"| `{f['nodeid']}` ({f['kind']}) | `{module}` | {owners_str} | {last} |"
        )
    if suggested:
        lines.append("")
        lines.append("### Suggested reviewers")
        for o in sorted(suggested):
            lines.append(f"- {o}")
    return "\n".join(lines)


def resolve_junit(arg: Path) -> list[Path]:
    if arg.is_dir():
        return sorted(arg.glob("junit-*.xml")) or sorted(arg.glob("*.xml"))
    return [arg]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--junit", type=Path, required=True, help="junit xml file or directory"
    )
    args = parser.parse_args()

    junit_paths = resolve_junit(args.junit)
    if not junit_paths:
        print(
            "## Test failure auto-attribution\n\nNo JUnit XML found.",
            file=sys.stderr,
        )
        return 0

    failures = collect_failures(junit_paths)
    print(build_report(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
