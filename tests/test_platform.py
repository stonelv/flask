"""Automated dry-run tests for the release/rollback/perf-gate/triage tooling.

These tests exercise the platform's own logic WITHOUT importing Flask (the
scripts are standard-library-only; perf_check's gate logic is tested with
stub benchmark callables). They verify the invariants that matter:

* **release two-phase**: the tag points at a *clean-version* commit
  (``bump`` sets the released version; ``start-dev`` sets next-dev on a
  separate step);
* **rollback** runbook interpolates versions and uses the two-phase flow;
* **perf gate** blocks on hard regressions (``--no-advisory`` -> exit 1) and
  warns on advisory ones;
* **triage** maps failing tests to source modules, including the 9
  non-obvious exceptions.

Run (no Flask needed, bypasses the flask-importing conftest)::

    pytest --noconftest tests/test_platform.py -q
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
BENCH = REPO / "benchmarks"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


changes = _load("platform_changes", SCRIPTS / "changes.py")
rollback = _load("platform_rollback", SCRIPTS / "rollback.py")
triage = _load("platform_triage", SCRIPTS / "triage.py")
perf = _load("platform_perf", BENCH / "perf_check.py")


CHANGES_HEAD = textwrap.dedent("""\
    Version 3.2.0
    -------------

    Unreleased

    -   Drop support for Python 3.9. :pr:`5730`
    -   ``RequestContext`` merged. :issue:`5639`

    """)


# --------------------------------------------------------------------------- #
# release: version math + classification
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "released,level,expected",
    [
        ("3.2.0", "patch", "3.2.1.dev"),
        ("3.2.0", "minor", "3.3.0.dev"),
        ("3.2.0", "major", "4.0.0.dev"),
    ],
)
def test_bump_version(released, level, expected):
    assert changes.bump_version(released, level) == expected


@pytest.mark.parametrize(
    "dev,expected",
    [("3.2.0.dev", "3.2.0"), ("3.2.0", "3.2.0"), ("3.2.1.dev0", "3.2.1")],
)
def test_release_version(dev, expected):
    assert changes.release_version(dev) == expected


def test_changelog_role_conversion():
    md = changes.rst_to_markdown_changes(CHANGES_HEAD)
    assert "(#5730)" in md  # :pr: -> (#NNNN)
    assert "(#5639)" in md  # :issue: -> (#NNNN)
    assert ":pr:" not in md and ":issue:" not in md
    assert "- Drop support" in md  # bullet -> "- "


# --------------------------------------------------------------------------- #
# release: two-phase on a temp repo (the critical tag-at-clean-version fix)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def temp_repo(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "Flask"\nversion = "3.2.0.dev"\n')
    changes_rst = tmp_path / "CHANGES.rst"
    changes_rst.write_text(CHANGES_HEAD)
    monkeypatch.setattr(changes, "PYPROJECT", pyproject)
    monkeypatch.setattr(changes, "CHANGES_RST", changes_rst)
    return pyproject, changes_rst


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_bump_dry_run_writes_nothing(temp_repo):
    pyproject, _ = temp_repo
    rc = changes.cmd_bump(
        _ns(level="patch", dry_run=True, apply=False, github_output=False)
    )
    assert rc == 0
    # dry-run must not change pyproject
    assert 'version = "3.2.0.dev"' in pyproject.read_text()


def test_two_phase_tag_points_at_clean_version(temp_repo):
    """The critical invariant: at tag time pyproject = clean released version,
    NOT the next .dev. start-dev (post-tag) sets the next .dev separately."""
    pyproject, changes_rst = temp_repo

    # step 1 (the tagged release commit)
    rc = changes.cmd_bump(
        _ns(level="patch", dry_run=False, apply=True, github_output=False)
    )
    assert rc == 0
    assert 'version = "3.2.0"' in pyproject.read_text()  # CLEAN, no .dev
    head_text = changes_rst.read_text()
    assert "Released 2026" in head_text  # Unreleased -> Released <date>
    head_lines = head_text.splitlines()
    assert "Unreleased" not in head_lines[:6]

    # >>> tag v3.2.0 would be created HERE <<<  (pyproject = 3.2.0 clean)
    tag_state_version = changes.current_version()
    assert tag_state_version == "3.2.0", (
        f"tag must point at clean 3.2.0, got {tag_state_version}"
    )

    # step 2 (post-tag commit reopens dev)
    rc = changes.cmd_start_dev(_ns(next_dev="3.2.1.dev", dry_run=False, apply=True))
    assert rc == 0
    assert 'version = "3.2.1.dev"' in pyproject.read_text()
    head = changes_rst.read_text().splitlines()
    assert head[0] == "Version 3.2.1"  # new block prepended
    assert "Unreleased" in head[:5]


def test_notes_extracts_version(temp_repo):
    _, changes_rst = temp_repo
    # mark 3.2.0 as released so notes can find a Released section
    changes.rename_unreleased_to_released  # noqa: B018 (sanity)
    text = changes_rst.read_text()
    released = changes.rename_unreleased_to_released(text, "3.2.0")
    changes_rst.write_text(released)
    out = _capture(lambda: changes.cmd_notes(_ns(version="3.2.0")))
    assert "## 3.2.0" in out
    assert "(#5730)" in out


def _capture(fn):
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# rollback
# --------------------------------------------------------------------------- #
def test_rollback_next_patch():
    assert rollback._next_patch("3.2.1") == "3.2.2"


def test_rollback_runbook_two_phase_interpolation():
    rb = rollback.runbook("3.2.1", commit=None, has_token=False)
    assert "v3.2.1" in rb
    assert "v3.2.2" in rb  # next patch
    assert "3.2.3.dev" in rb  # next-next dev
    assert "start-dev --next-dev 3.2.3.dev" in rb  # two-phase in runbook
    assert "bump --level patch --apply" in rb
    assert "pypi.org/manage/project/flask/release/3.2.1/yank/" in rb


def test_rollback_yank_without_token_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(rollback, "release_commit", lambda _v: None)
    monkeypatch.delenv("PYPI_API_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["rollback.py", "--version", "3.2.1", "--yank"])
    rc = rollback.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "PYPI_API_TOKEN" in err


# --------------------------------------------------------------------------- #
# perf gate (stub benchmarks, no Flask)
# --------------------------------------------------------------------------- #
def _stub_bench(median):
    def fn():
        return {
            "median_us": median,
            "min_us": median,
            "stdev_us": 0.0,
            "iterations": 10.0,
        }

    return fn


def _stub_baseline(median):
    return {
        "version": 1,
        "thresholds": {
            "hard_regression": ["core_request_roundtrip"],
            "advisory_regression_ratio": 1.15,
            "hard_regression_ratio": 1.25,
        },
        "benchmarks": {
            "core_request_roundtrip": {
                "median_us": median,
                "min_us": median,
                "stdev_us": 0.0,
                "iterations": 10.0,
            }
        },
    }


def test_perf_hard_gate_blocks_on_regression():
    baseline = _stub_baseline(median=10.0)
    results = perf.run_all(
        samples=1,
        benchmarks={"core_request_roundtrip": _stub_bench(25.0)},  # 2.5x
    )
    _, exit_code = perf.build_report(baseline, results, advisory=False)
    assert exit_code == 1, "hard regression must fail the build"


def test_perf_advisory_does_not_block():
    baseline = _stub_baseline(median=10.0)
    results = perf.run_all(
        samples=1, benchmarks={"core_request_roundtrip": _stub_bench(25.0)}
    )
    report, exit_code = perf.build_report(baseline, results, advisory=True)
    assert exit_code == 0
    assert "advisory" in report.lower()


def test_perf_no_regression_passes():
    baseline = _stub_baseline(median=10.0)
    results = perf.run_all(
        samples=1, benchmarks={"core_request_roundtrip": _stub_bench(10.0)}
    )
    report, exit_code = perf.build_report(baseline, results, advisory=False)
    assert exit_code == 0
    assert "| ok |" in report


def test_perf_improvement_detected():
    baseline = _stub_baseline(median=10.0)
    results = perf.run_all(
        samples=1,
        benchmarks={"core_request_roundtrip": _stub_bench(5.0)},  # 0.5x
    )
    report, _ = perf.build_report(baseline, results, advisory=False)
    assert "improvement" in report.lower()


def test_perf_multisample_aggregation():
    # 3 sampled runs with medians 10, 20, 30 -> aggregate median 20
    seq = iter([10.0, 20.0, 30.0])
    results = perf.run_all(
        samples=3, benchmarks={"core_request_roundtrip": _stub_bench_fn(seq)}
    )
    assert results["core_request_roundtrip"]["median_us"] == 20.0


def _stub_bench_fn(seq):
    def fn():
        m = next(seq)
        return {"median_us": m, "min_us": m, "stdev_us": 0.0, "iterations": 10.0}

    return fn


def test_perf_update_baseline_writes(monkeypatch, tmp_path):
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps(_stub_baseline(median=10.0)))
    monkeypatch.setattr(perf, "BASELINE_PATH", baseline_file)
    # main() calls run_all(samples=...); inject a stub so no Flask is imported.
    monkeypatch.setattr(
        perf,
        "run_all",
        lambda samples=1, benchmarks=None: {
            "core_request_roundtrip": {
                "median_us": 42.0,
                "min_us": 40.0,
                "stdev_us": 1.0,
                "iterations": 10.0,
            }
        },
    )
    monkeypatch.setattr(
        sys, "argv", ["perf_check.py", "--update-baseline", "--samples", "2"]
    )
    rc = perf.main()
    assert rc == 0
    written = json.loads(baseline_file.read_text())
    assert written["benchmarks"]["core_request_roundtrip"]["median_us"] == 42.0


# --------------------------------------------------------------------------- #
# triage: module mapping (incl. 9 exceptions) + CODEOWNERS + junit
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "stem,expected",
    [
        ("test_basic", "src/flask/app.py"),
        ("test_user_error_handler", "src/flask/app.py"),
        ("test_subclassing", "src/flask/app.py"),
        ("test_converters", "src/flask/app.py"),
        ("test_async", "src/flask/app.py"),
        ("test_regression", "src/flask/app.py"),
        ("test_appctx", "src/flask/ctx.py"),
        ("test_reqctx", "src/flask/ctx.py"),
        ("test_request", "src/flask/wrappers.py"),  # NOT a request.py
        ("test_templating", "src/flask/templating.py"),  # default rule, exists
    ],
)
def test_triage_module_mapping(stem, expected):
    assert triage.module_for_test(stem, REPO) == expected


def test_triage_default_falls_back_to_test_file(tmp_path):
    # a stem with no matching src/flask/<x>.py -> tests/<stem>.py
    assert triage.module_for_test("test_totally_made_up", tmp_path) == (
        "tests/test_totally_made_up.py"
    )


def test_triage_codeowners_longest_match(tmp_path):
    f = tmp_path / "CODEOWNERS"
    f.write_text("* @default\n/src/flask/ @flask-core\n/src/flask/cli.py @cli-owner\n")
    parsed = triage.parse_codeowners(f)
    assert triage.match_codeowners("src/flask/cli.py", parsed) == ["@cli-owner"]
    assert triage.match_codeowners("src/flask/app.py", parsed) == ["@flask-core"]
    assert triage.match_codeowners("docs/index.rst", parsed) == ["@default"]


def test_triage_collect_failures_and_report(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<?xml version="1.0"?><testsuites>'
        '<testsuite name="tests.test_basic">'
        '<testcase classname="tests.test_basic" name="test_x">'
        "<failure>boom</failure></testcase>"
        "</testsuite>"
        '<testsuite name="tests.test_blueprints">'
        '<testcase classname="tests.test_blueprints" name="test_y" time="0.1"/>'
        "</testsuite>"
        "</testsuites>"
    )
    failures = triage.collect_failures([junit])
    assert len(failures) == 1
    assert failures[0]["stem"] == "test_basic"
    report = triage.build_report(failures)
    assert "src/flask/app.py" in report
    assert "test_blueprints" not in report  # passing test not attributed
