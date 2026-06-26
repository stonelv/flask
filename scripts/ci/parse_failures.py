"""Parse JUnit XML test results and categorize failures for CI.

Usage: python scripts/ci/parse_failures.py results.xml [--github-actions]
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def categorize_failure(failure_msg: str, failure_type: str) -> str:
    """Categorize a test failure by its root cause."""
    if "ImportError" in failure_type or "ModuleNotFoundError" in failure_type:
        return "import_error"
    if "TimeoutError" in failure_type or "Timeout" in failure_msg:
        return "timeout"
    if "fixture" in failure_msg.lower() and "Error" in failure_type:
        return "fixture_error"
    if "AssertionError" in failure_type:
        return "assertion_failure"
    return "test_failure"


def parse_junit_xml(xml_path: str) -> dict:
    """Parse JUnit XML and return categorized results."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    results: dict = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errored": 0,
        "skipped": 0,
        "failures": [],
    }

    testsuites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    for suite in testsuites:
        for testcase in suite.findall("testcase"):
            results["total"] += 1
            classname = testcase.get("classname", "")
            name = testcase.get("name", "")
            full_name = f"{classname}::{name}" if classname else name

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                results["failed"] += 1
                msg = failure.get("message", "")
                ftype = failure.get("type", "")
                category = categorize_failure(msg, ftype)
                results["failures"].append(
                    {
                        "test": full_name,
                        "category": category,
                        "type": ftype,
                        "message": msg[:500],
                    }
                )
            elif error is not None:
                results["errored"] += 1
                msg = error.get("message", "")
                ftype = error.get("type", "")
                category = categorize_failure(msg, ftype)
                results["failures"].append(
                    {
                        "test": full_name,
                        "category": category,
                        "type": ftype,
                        "message": msg[:500],
                    }
                )
            elif skipped is not None:
                results["skipped"] += 1
            else:
                results["passed"] += 1

    return results


def format_github_annotations(results: dict) -> str:
    """Format failures as GitHub Actions annotations."""
    lines: list[str] = []
    by_category: dict[str, list] = {}

    for f in results["failures"]:
        by_category.setdefault(f["category"], []).append(f)

    category_labels = {
        "assertion_failure": "Assertion Failures",
        "import_error": "Import Errors",
        "timeout": "Timeouts",
        "fixture_error": "Fixture Errors",
        "test_failure": "Test Failures",
    }

    for category, failures in sorted(by_category.items()):
        label = category_labels.get(category, category)
        lines.append(f"\n### {label} ({len(failures)})")
        for f in failures:
            lines.append(f"- `{f['test']}`: {f['message'][:200]}")
            print(f"::error title={label}: {f['test']}::{f['message'][:200]}")

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <junit-xml-path> [--github-actions]")
        sys.exit(1)

    xml_path = sys.argv[1]
    github_actions = "--github-actions" in sys.argv

    if not Path(xml_path).exists():
        print(f"Warning: JUnit XML not found at {xml_path}")
        sys.exit(0)

    results = parse_junit_xml(xml_path)

    summary = (
        f"Tests: {results['total']} total, "
        f"{results['passed']} passed, "
        f"{results['failed']} failed, "
        f"{results['errored']} errored, "
        f"{results['skipped']} skipped"
    )

    if github_actions:
        print("::group::Test Results Summary")
        print(summary)
        if results["failures"]:
            print(format_github_annotations(results))
        print("::endgroup::")
    else:
        print(summary)
        if results["failures"]:
            print(format_github_annotations(results))

    json_path = Path(xml_path).with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results written to {json_path}")


if __name__ == "__main__":
    main()
