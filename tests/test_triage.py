"""Tests for the CI failure-triage helper in ``scripts/triage_failures.py``.

The script is loaded by path because ``scripts`` is not an importable package.
These tests run as part of the normal suite so the CI-only tool can't silently
rot.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCRIPT = os.path.join(_ROOT, "scripts", "triage_failures.py")


def _load():
    spec = importlib.util.spec_from_file_location("triage_failures", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


triage = _load()


def _write_junit(path, *, with_failure=True):
    failure = (
        '<failure message="assert 404 == 200">AssertionError</failure>'
        if with_failure
        else ""
    )
    path.write_text(
        f"""<testsuites><testsuite name="pytest" tests="2" failures="1">
 <testcase classname="tests.test_basic" name="test_ok"
           file="tests/test_basic.py" line="10"/>
 <testcase classname="tests.test_basic" name="test_boom"
           file="tests/test_basic.py" line="42">{failure}</testcase>
</testsuite></testsuites>""",
        encoding="utf-8",
    )


def test_parse_failures_extracts_only_failing(tmp_path):
    junit = tmp_path / "j.xml"
    _write_junit(junit)
    failures = triage.parse_failures(str(junit))
    assert len(failures) == 1
    f = failures[0]
    assert f["module"] == "tests.test_basic"
    assert f["name"] == "test_boom"
    assert f["file"] == "tests/test_basic.py"
    # JUnit line is 0-based; the script reports 1-based.
    assert f["line"] == 43


def test_render_groups_by_module_and_has_table(tmp_path):
    junit = tmp_path / "j.xml"
    _write_junit(junit)
    failures = triage.parse_failures(str(junit))
    out = triage.render(failures)
    assert "Test triage" in out
    assert "`tests.test_basic`" in out
    assert "test_boom" in out
    assert "| Test |" in out  # markdown table header


def test_render_handles_no_failures():
    out = triage.render([])
    assert "No failing tests" in out


def test_main_writes_step_summary_and_exits_zero(tmp_path, monkeypatch):
    junit = tmp_path / "j.xml"
    _write_junit(junit)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    rc = triage.main(["triage_failures.py", str(junit)])
    assert rc == 0
    assert "Test triage" in summary.read_text(encoding="utf-8")


def test_main_missing_report_is_noop():
    # Never fail the build just because there is no report.
    assert triage.main(["triage_failures.py", "/no/such/report.xml"]) == 0


@pytest.mark.parametrize("bad", ["not xml at all", "<broken>"])
def test_main_handles_unparseable_report(tmp_path, bad):
    junit = tmp_path / "bad.xml"
    junit.write_text(bad, encoding="utf-8")
    assert triage.main(["triage_failures.py", str(junit)]) == 0
