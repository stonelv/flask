#!/usr/bin/env python3
"""Compare a pytest-benchmark run against a committed baseline.

Reads two ``--benchmark-json`` files, matches benchmarks by name, and compares
the median time of each. Exits non-zero if any benchmark is slower than the
baseline by more than the threshold, so it can act as a CI gate.

Usage:
    python benchmarks/compare.py baseline.json current.json --threshold 0.10
    python benchmarks/compare.py baseline.json current.json --markdown report.md
"""

from __future__ import annotations

import argparse
import json
import sys


def load_medians(path: str) -> dict[str, float]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out: dict[str, float] = {}
    for bench in data.get("benchmarks", []):
        key = bench.get("fullname") or bench.get("name", "")
        stats = bench.get("stats", {})
        if key and "median" in stats:
            out[key] = float(stats["median"])
    return out


def short(name: str) -> str:
    """Drop the file path prefix, keep the test id, for readable reports."""
    return name.split("::", 1)[-1] if "::" in name else name


def build_rows(
    baseline: dict[str, float], current: dict[str, float], threshold: float
) -> tuple[list[tuple[str, float, float, float, bool]], int]:
    rows: list[tuple[str, float, float, float, bool]] = []
    regressions = 0
    for name in sorted(current):
        cur = current[name]
        base = baseline.get(name)
        if base is None or base == 0:
            rows.append((name, base or 0.0, cur, float("nan"), False))
            continue
        delta = cur / base - 1.0
        is_reg = delta > threshold
        regressions += is_reg
        rows.append((name, base, cur, delta, is_reg))
    return rows, regressions


def write_markdown(
    path: str,
    rows: list[tuple[str, float, float, float, bool]],
    threshold: float,
    regressions: int,
) -> None:
    lines = ["## Performance comparison", ""]
    status = "❌ regression" if regressions else "✅ within threshold"
    lines.append(f"Threshold: **{threshold * 100:.0f}%** — {status}")
    lines.append("")
    lines.append("| Benchmark | Baseline (µs) | Current (µs) | Δ |")
    lines.append("|---|--:|--:|--:|")
    for name, base, cur, delta, is_reg in rows:
        if delta != delta:  # NaN -> new benchmark
            d = "new"
        else:
            d = f"{delta * 100:+.1f}%" + (" ⚠️" if is_reg else "")
        lines.append(f"| `{short(name)}` | {base * 1e6:.2f} | {cur * 1e6:.2f} | {d} |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("current")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="max allowed median slowdown as a fraction (0.10 = 10%%)",
    )
    parser.add_argument(
        "--markdown",
        metavar="FILE",
        help="also write a Markdown report to FILE",
    )
    args = parser.parse_args(argv[1:])

    baseline = load_medians(args.baseline)
    current = load_medians(args.current)

    if not current:
        print("compare: current run has no benchmarks; nothing to compare.")
        return 0

    rows, regressions = build_rows(baseline, current, args.threshold)

    width = max((len(short(n)) for n, *_ in rows), default=10)
    print(f"{'benchmark':<{width}}  {'baseline':>10}  {'current':>10}  {'delta':>8}")
    print("-" * (width + 34))
    for name, base, cur, delta, is_reg in rows:
        flag = "  <== REGRESSION" if is_reg else ""
        delta_s = "  new" if delta != delta else f"{delta * 100:+7.1f}%"  # NaN check
        cells = f"{base * 1e6:9.2f}us  {cur * 1e6:9.2f}us  {delta_s}{flag}"
        print(f"{short(name):<{width}}  {cells}")

    new = sum(1 for *_, d, _ in rows if d != d)
    missing = sorted(set(baseline) - set(current))
    print()
    print(
        f"summary: {len(current)} benchmarks, {regressions} regression(s) "
        f"over {args.threshold * 100:.0f}% threshold, {new} new, "
        f"{len(missing)} missing from current run."
    )

    if args.markdown:
        write_markdown(args.markdown, rows, args.threshold, regressions)

    if regressions:
        print("FAIL: performance regression detected.")
        return 1
    print("OK: no regression beyond threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
