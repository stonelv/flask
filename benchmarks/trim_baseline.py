#!/usr/bin/env python3
"""Trim a pytest-benchmark JSON down to the fields the gate needs.

A raw ``--benchmark-json`` file embeds every per-round sample and can be
multiple megabytes. The committed baseline only needs each benchmark's name and
summary stats, so this produces a tiny, diff-friendly file.

Usage:
    python benchmarks/trim_baseline.py current.json baseline.json
"""

from __future__ import annotations

import json
import sys

# Stats kept for the baseline. ``median`` drives the gate; the others make the
# committed file useful for humans reading a diff.
KEEP_STATS = ("median", "mean", "min", "max", "stddev", "ops", "rounds")


def trim(src: str, dst: str) -> None:
    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)

    slim = {
        "machine_info": {
            k: data.get("machine_info", {}).get(k)
            for k in ("node", "system", "machine", "python_version")
        },
        "benchmarks": [
            {
                "fullname": b.get("fullname") or b.get("name", ""),
                "stats": {
                    k: b.get("stats", {}).get(k)
                    for k in KEEP_STATS
                    if k in b.get("stats", {})
                },
            }
            for b in data.get("benchmarks", [])
        ],
    }

    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(slim, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    trim(argv[1], argv[2])
    print(f"wrote trimmed baseline: {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
