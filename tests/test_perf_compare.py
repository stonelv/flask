"""Tests for the benchmark comparison gate in ``benchmarks/compare.py``.

These use synthetic JSON so they are deterministic and environment-independent:
they prove the *gate logic* (threshold, exit codes, noise handling, reporting)
without depending on real timings. The actual benchmarks live in ``benchmarks/``
and are not collected by the default test run.
"""

from __future__ import annotations

import importlib.util
import json
import os

_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCRIPT = os.path.join(_ROOT, "benchmarks", "compare.py")


def _load():
    spec = importlib.util.spec_from_file_location("bench_compare", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


compare = _load()


def _bench(name, median, stddev=0.0, rounds=100):
    return {
        "fullname": name,
        "stats": {"median": median, "stddev": stddev, "rounds": rounds},
    }


def _write(path, benches):
    path.write_text(json.dumps({"benchmarks": benches}), encoding="utf-8")
    return str(path)


def test_no_regression_exits_zero(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4), _bench("t::b", 2e-4)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1.04e-4), _bench("t::b", 1.9e-4)])
    assert compare.main(["compare.py", base, cur, "--threshold", "0.10"]) == 0


def test_regression_exits_nonzero(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1.30e-4)])  # +30%
    assert compare.main(["compare.py", base, cur, "--threshold", "0.10"]) == 1


def test_threshold_is_respected(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1.30e-4)])  # +30%
    # 50% threshold tolerates it
    assert compare.main(["compare.py", base, cur, "--threshold", "0.50"]) == 0


def test_new_benchmark_is_not_a_regression(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1e-4), _bench("t::new", 9e-4)])
    assert compare.main(["compare.py", base, cur]) == 0


def test_ignore_within_noise_suppresses_jittery_regression(tmp_path):
    # +12% delta but each run has ~10% noise -> within combined noise, not a regression
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4, stddev=1e-5)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1.12e-4, stddev=1.12e-5)])
    assert compare.main(["compare.py", base, cur, "--threshold", "0.10"]) == 1
    assert (
        compare.main(
            ["compare.py", base, cur, "--threshold", "0.10", "--ignore-within-noise"]
        )
        == 0
    )


def test_markdown_report_written(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4)])
    cur = _write(tmp_path / "c.json", [_bench("t::a", 1.05e-4)])
    report = tmp_path / "report.md"
    compare.main(["compare.py", base, cur, "--markdown", str(report)])
    text = report.read_text(encoding="utf-8")
    assert "Performance comparison" in text
    assert "Noise (±)" in text
    assert "`a`" in text  # short() strips the "t::" path prefix


def test_empty_current_is_noop(tmp_path):
    base = _write(tmp_path / "b.json", [_bench("t::a", 1e-4)])
    cur = _write(tmp_path / "c.json", [])
    assert compare.main(["compare.py", base, cur]) == 0
