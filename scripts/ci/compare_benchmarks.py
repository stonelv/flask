"""Compare benchmark results against a baseline.

Usage::

    python scripts/ci/compare_benchmarks.py current.json baseline.json
        [--threshold=15]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_benchmarks(path: str) -> dict[str, float]:
    """Load benchmark results from pytest-benchmark JSON."""
    with open(path) as f:
        data = json.load(f)

    results = {}
    for bench in data.get("benchmarks", []):
        name = bench.get("name", bench.get("fullname", "unknown"))
        stats = bench.get("stats", {})
        results[name] = stats.get("median", stats.get("mean", 0))

    return results


def compare(
    current_path: str,
    baseline_path: str,
    threshold: float = 15.0,
) -> tuple[bool, str]:
    """Compare current benchmarks against baseline.

    Returns (passed, report) where passed is True if no benchmark
    regressed more than threshold percent.
    """
    current = load_benchmarks(current_path)
    baseline = load_benchmarks(baseline_path)

    if not baseline:
        return True, "No baseline data available. Skipping comparison."

    regressions = []
    improvements = []
    unchanged = []

    for name, current_time in sorted(current.items()):
        if name not in baseline:
            unchanged.append(f"  {name}: {current_time * 1000:.2f}ms (new)")
            continue

        baseline_time = baseline[name]
        if baseline_time == 0:
            continue

        change_pct = ((current_time - baseline_time) / baseline_time) * 100

        if change_pct > threshold:
            regressions.append(
                f"  ⚠️  {name}: {baseline_time * 1000:.2f}ms → "
                f"{current_time * 1000:.2f}ms ({change_pct:+.1f}%)"
            )
        elif change_pct < -threshold:
            improvements.append(
                f"  ✅ {name}: {baseline_time * 1000:.2f}ms → "
                f"{current_time * 1000:.2f}ms ({change_pct:+.1f}%)"
            )
        else:
            unchanged.append(
                f"  ── {name}: {baseline_time * 1000:.2f}ms → "
                f"{current_time * 1000:.2f}ms ({change_pct:+.1f}%)"
            )

    lines = [f"Benchmark Comparison (threshold: ±{threshold}%)", "=" * 50]

    if regressions:
        lines.append(f"\nRegressions ({len(regressions)}):")
        lines.extend(regressions)
    if improvements:
        lines.append(f"\nImprovements ({len(improvements)}):")
        lines.extend(improvements)
    if unchanged:
        lines.append(f"\nUnchanged ({len(unchanged)}):")
        lines.extend(unchanged)

    report = "\n".join(lines)
    passed = len(regressions) == 0

    if not passed:
        for r in regressions:
            print(f"::warning title=Performance Regression::{r.strip()}")

    return passed, report


def main() -> None:
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <current.json> <baseline.json> "
            f"[--threshold=15]"
        )
        sys.exit(1)

    current_path = sys.argv[1]
    baseline_path = sys.argv[2]

    threshold = 15.0
    for arg in sys.argv[3:]:
        if arg.startswith("--threshold="):
            threshold = float(arg.split("=")[1])

    if not Path(baseline_path).exists():
        print("No baseline found. Skipping comparison.")
        sys.exit(0)

    passed, report = compare(current_path, baseline_path, threshold)
    print(report)

    if not passed:
        print(f"\n⚠️  Performance regressions detected (>{threshold}% slower)")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
