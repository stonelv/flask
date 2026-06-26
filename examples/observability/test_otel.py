"""Tests that prove the OpenTelemetry wiring actually produces signals.

These run in the example's own environment (it depends on the OpenTelemetry
SDK); the Flask core test suite never imports any of this. They use in-memory
exporters instead of a live OTLP collector, so they are fully self-contained.

Run with:
    cd examples/observability
    uv run --with . --with pytest pytest        # or: pip install -e . pytest && pytest
"""

from __future__ import annotations

import logging

import pytest
from opentelemetry.sdk._logs.export import InMemoryLogExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from otel_setup import configure_telemetry

from flask import Flask


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def metric_reader() -> InMemoryMetricReader:
    return InMemoryMetricReader()


@pytest.fixture
def app(span_exporter: InMemorySpanExporter, metric_reader: InMemoryMetricReader):
    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        logging.getLogger(__name__).info("handling index")
        return "ok"

    tel = configure_telemetry(
        app,
        service_name="test-app",
        span_exporter=span_exporter,
        metric_reader=metric_reader,
        log_exporter=InMemoryLogExporter(),
    )
    # BatchSpanProcessor is async; add a synchronous one for deterministic tests.
    tel.tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    app._telemetry = tel  # type: ignore[attr-defined]
    return app


def test_request_produces_a_span(app, span_exporter):
    client = app.test_client()
    assert client.get("/").status_code == 200
    app._telemetry.tracer_provider.force_flush()

    spans = span_exporter.get_finished_spans()
    assert spans, "expected at least one span for the request"
    # The Flask instrumentation names the server span after the route rule.
    names = {s.name for s in spans}
    assert any("/" in n or "index" in n for n in names), names


def test_metrics_are_collected(app, metric_reader):
    client = app.test_client()
    client.get("/")
    data = metric_reader.get_metrics_data()
    assert data is not None
    # at least one resource/scope/metric should be present after a request
    resource_metrics = getattr(data, "resource_metrics", [])
    assert resource_metrics, "expected http.server.* metrics after a request"
