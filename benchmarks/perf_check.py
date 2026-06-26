#!/usr/bin/env python3
"""Performance regression gate.

Runs every benchmark in ``benchmarks.bench_core.BENCHMARKS``, compares each
median against ``benchmarks/baseline.json``, and prints a Markdown table
suitable for ``$GITHUB_STEP_SUMMARY``.

Exit codes:
    0  no hard regression (advisory regressions are reported but do not fail)
    1  a hard-regression benchmark (listed in ``thresholds.hard_regression``)
       regressed beyond ``thresholds.hard_regression_ratio``

In Phase 1 the whole gate is advisory: ``--advisory`` (the default) makes any
regression, including a hard one, exit 0 so a flaky runner never blocks a PR.
Promote to blocking in a later phase by dropping ``--advisory`` in CI once a
variance budget has been established across >= 10 runs.

Usage::

    python benchmarks/perf_check.py                 # advisory (CI, Phase 1)
    python benchmarks/perf_check.py --no-advisory    # hard gate (Phase 3+)
    python benchmarks/perf_check.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``benchmarks`` importable when run as ``python benchmarks/perf_check.py``
# from the repo root (tox env cwd) without relying on the package being
# installed -- the bench modules live in this directory.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchmarks.bench_core import BENCHMARKS  # noqa: E402

BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text())


def run_all(samples: int = 1) -> dict[str, dict[str, float]]:
    """Run every benchmark ``samples`` times and aggregate.

    With ``samples > 1`` the baseline median is the median of the per-run
    medians (robust to a single noisy run), min is the best per-run median,
    and stdev is the spread across runs. This is what ``--update-baseline
    --samples N`` writes -- a real multi-sample baseline, not one hot run.
    """
    import statistics

    results: dict[str, dict[str, float]] = {}
    for name, fn in BENCHMARKS.items():
        runs = [fn() for _ in range(max(1, samples))]
        medians = [r["median_us"] for r in runs]
        results[name] = {
            "median_us": statistics.median(medians),
            "min_us": min(r["min_us"] for r in runs),
            "stdev_us": (
                statistics.stdev(medians) if len(medians) > 1 else runs[0]["stdev_us"]
            ),
            "iterations": runs[0]["iterations"],
        }
    return results


def build_report(
    baseline: dict, results: dict[str, dict[str, float]], advisory: bool
) -> tuple[str, int]:
    thresholds = baseline.get("thresholds", {})
    hard_set = set(thresholds.get("hard_regression", []))
    advisory_ratio = float(thresholds.get("advisory_regression_ratio", 1.15))
    hard_ratio = float(thresholds.get("hard_regression_ratio", 1.25))

    lines: list[str] = ["## Performance regression check", ""]
    lines.append(
        f"advisory_ratio={advisory_ratio:.2f} "
        f"hard_ratio={hard_ratio:.2f} "
        f"mode={'advisory' if advisory else 'blocking'}"
    )
    lines.append("")
    lines.append("| benchmark | baseline (us) | current (us) | ratio | status |")
    lines.append("|---|---|---|---|---|")

    exit_code = 0
    regressions: list[str] = []

    for name in sorted(results):
        current = results[name]["median_us"]
        base = baseline["benchmarks"][name]["median_us"]
        ratio = current / base if base else float("inf")
        status = "ok"
        if ratio > hard_ratio and name in hard_set:
            status = "HARD REGRESSION"
            regressions.append(name)
            if not advisory:
                exit_code = 1
        elif ratio > advisory_ratio:
            status = "advisory regression"
        elif ratio < 1 / advisory_ratio:
            status = "improvement"
        lines.append(
            f"| `{name}` | {base:.2f} | {current:.2f} | {ratio:.2f} | {status} |"
        )

    if regressions:
        lines.append("")
        lines.append(
            f"**Hard regressions:** {', '.join(regressions)} "
            f"(>{hard_ratio:.2f}x baseline). "
            + (
                "Advisory mode -- not failing the build."
                if advisory
                else "Failing the build."
            )
        )

    return "\n".join(lines), exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-advisory",
        dest="advisory",
        action="store_false",
        help="Make hard regressions fail the build (Phase 3+).",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite baseline.json from the current run. Manual only.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Number of sampled runs per benchmark (use with --update-baseline "
        "for a real multi-sample baseline; median of per-run medians).",
    )
    args = parser.parse_args()

    if args.update_baseline:
        baseline = load_baseline()
        results = run_all(samples=args.samples)
        for name, stats in results.items():
            baseline["benchmarks"][name].update(stats)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"Updated {BASELINE_PATH} (samples={args.samples} per benchmark)")
        return 0

    baseline = load_baseline()
    results = run_all(samples=args.samples)
    report, exit_code = build_report(baseline, results, advisory=args.advisory)
    print(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
