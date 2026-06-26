"""Benchmark observability overhead (run only when observability is installed)."""

from __future__ import annotations

import pytest
import flask
from pytest_benchmark.fixture import BenchmarkFixture

try:
    from flask.observability import init_observability

    HAS_OBSERVABILITY = True
except ImportError:
    HAS_OBSERVABILITY = False

pytestmark = pytest.mark.skipif(
    not HAS_OBSERVABILITY,
    reason="Flask[observability] not installed",
)


def test_baseline_request(benchmark: BenchmarkFixture, app: flask.Flask) -> None:
    """Baseline: request without observability."""

    @app.route("/baseline")
    def baseline() -> str:
        return "ok"

    client = app.test_client()
    result = benchmark(client.get, "/baseline")
    assert result.status_code == 200


def test_instrumented_request(benchmark: BenchmarkFixture, app: flask.Flask) -> None:
    """Instrumented: request with observability (none exporter, no network)."""

    init_observability(app, exporter="none", structured_logging=False)

    @app.route("/instrumented")
    def instrumented() -> str:
        return "ok"

    client = app.test_client()
    result = benchmark(client.get, "/instrumented")
    assert result.status_code == 200
