#!/usr/bin/env python3
"""Compare a pytest-benchmark run against a baseline.

Reads two ``--benchmark-json`` files, matches benchmarks by name, and compares
the **median** time of each (median is far more stable than mean under CI
jitter). Reports the per-benchmark relative standard deviation so the noise
floor is visible. Exits non-zero if any benchmark regresses beyond the
threshold, so it can act as a CI gate.

Absolute timings are environment-specific: a baseline produced on one machine is
not comparable to a run on another. Always compare two runs collected in the
*same* environment (the CI workflow benchmarks the base commit on the same
runner — see .github/workflows/benchmarks.yaml).

Usage:
    python benchmarks/compare.py baseline.json current.json --threshold 0.10
    python benchmarks/compare.py baseline.json current.json --markdown report.md
    python benchmarks/compare.py baseline.json current.json --ignore-within-noise
"""

from __future__ import annotations

import argparse
import json
import sys


def load_stats(path: str) -> dict[str, dict[str, float]]:
    """Return {name: {median, stddev, rounds}} for each benchmark."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out: dict[str, dict[str, float]] = {}
    for bench in data.get("benchmarks", []):
        key = bench.get("fullname") or bench.get("name", "")
        stats = bench.get("stats", {})
        if key and "median" in stats:
            out[key] = {
                "median": float(stats["median"]),
                "stddev": float(stats.get("stddev", 0.0)),
                "rounds": float(stats.get("rounds", 0.0)),
            }
    return out


def short(name: str) -> str:
    """Drop the file path prefix, keep the test id, for readable reports."""
    return name.split("::", 1)[-1] if "::" in name else name


def rel_noise(stat: dict[str, float]) -> float:
    """Relative standard deviation of the current run (0 if median is 0)."""
    median = stat["median"]
    return stat["stddev"] / median if median else 0.0


class Row:
    __slots__ = ("name", "base", "cur", "delta", "noise", "is_reg", "is_new")

    def __init__(
        self,
        name: str,
        base: float,
        cur: float,
        delta: float,
        noise: float,
        is_reg: bool,
        is_new: bool,
    ) -> None:
        self.name = name
        self.base = base
        self.cur = cur
        self.delta = delta
        self.noise = noise
        self.is_reg = is_reg
        self.is_new = is_new


def build_rows(
    baseline: dict[str, dict[str, float]],
    current: dict[str, dict[str, float]],
    threshold: float,
    ignore_within_noise: bool,
) -> tuple[list[Row], int]:
    rows: list[Row] = []
    regressions = 0
    for name in sorted(current):
        cur_stat = current[name]
        cur = cur_stat["median"]
        noise = rel_noise(cur_stat)
        base_stat = baseline.get(name)
        if base_stat is None or base_stat["median"] == 0:
            rows.append(Row(name, 0.0, cur, float("nan"), noise, False, True))
            continue
        base = base_stat["median"]
        delta = cur / base - 1.0
        is_reg = delta > threshold
        # When asked, do not count a "regression" smaller than the combined
        # noise of the two runs — it is indistinguishable from jitter.
        if is_reg and ignore_within_noise:
            combined = noise + rel_noise(base_stat)
            if delta <= combined:
                is_reg = False
        regressions += is_reg
        rows.append(Row(name, base, cur, delta, noise, is_reg, False))
    return rows, regressions


def write_markdown(
    path: str, rows: list[Row], threshold: float, regressions: int
) -> None:
    lines = ["## Performance comparison", ""]
    status = "❌ regression" if regressions else "✅ within threshold"
    lines.append(f"Threshold: **{threshold * 100:.0f}%** — {status}")
    lines.append("")
    lines.append("| Benchmark | Baseline (µs) | Current (µs) | Δ | Noise (±) |")
    lines.append("|---|--:|--:|--:|--:|")
    for r in rows:
        d = "new" if r.is_new else f"{r.delta * 100:+.1f}%" + (" ⚠️" if r.is_reg else "")
        lines.append(
            f"| `{short(r.name)}` | {r.base * 1e6:.2f} | {r.cur * 1e6:.2f} | "
            f"{d} | {r.noise * 100:.1f}% |"
        )
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
        "--markdown", metavar="FILE", help="also write a Markdown report to FILE"
    )
    parser.add_argument(
        "--ignore-within-noise",
        action="store_true",
        help="do not flag a regression smaller than the runs' combined noise",
    )
    args = parser.parse_args(argv[1:])

    baseline = load_stats(args.baseline)
    current = load_stats(args.current)

    if not current:
        print("compare: current run has no benchmarks; nothing to compare.")
        return 0

    rows, regressions = build_rows(
        baseline, current, args.threshold, args.ignore_within_noise
    )

    width = max((len(short(r.name)) for r in rows), default=10)
    header = (
        f"{'benchmark':<{width}}  {'baseline':>10}  {'current':>10}  "
        f"{'delta':>8}  {'noise':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        flag = "  <== REGRESSION" if r.is_reg else ""
        delta_s = "  new" if r.is_new else f"{r.delta * 100:+7.1f}%"
        cells = (
            f"{r.base * 1e6:9.2f}us  {r.cur * 1e6:9.2f}us  "
            f"{delta_s}  {r.noise * 100:5.1f}%{flag}"
        )
        print(f"{short(r.name):<{width}}  {cells}")

    new = sum(1 for r in rows if r.is_new)
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
