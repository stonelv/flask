"""Tests proving the extension emits real telemetry, using in-memory exporters.

Run in the extension's own environment (it depends on the OpenTelemetry SDK);
Flask core's test suite never imports any of this.

    cd extensions/flask-telemetry
    uv run --with . --with pytest pytest      # or: pip install -e .[test] && pytest
"""

from __future__ import annotations

import logging

import pytest
from flask_telemetry import Telemetry
from opentelemetry.sdk._logs.export import InMemoryLogExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

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

    tel = Telemetry(
        app,
        service_name="test-app",
        span_exporter=span_exporter,
        metric_reader=metric_reader,
        log_exporter=InMemoryLogExporter(),
    )
    # BatchSpanProcessor is async; add a synchronous one for deterministic tests.
    tel.tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    return app


def test_extension_registers_on_app(app):
    assert isinstance(app.extensions["telemetry"], Telemetry)


def test_request_produces_a_span(app, span_exporter):
    client = app.test_client()
    assert client.get("/").status_code == 200
    app.extensions["telemetry"].force_flush()

    spans = span_exporter.get_finished_spans()
    assert spans, "expected at least one span for the request"
    names = {s.name for s in spans}
    assert any("/" in n or "index" in n for n in names), names


def test_metrics_are_collected(app, metric_reader):
    app.test_client().get("/")
    data = metric_reader.get_metrics_data()
    assert data is not None
    assert getattr(data, "resource_metrics", []), "expected http.server.* metrics"


def test_init_app_defers_configuration(span_exporter):
    # the deferred-init form of the Flask extension protocol
    tel = Telemetry(span_exporter=span_exporter, log_exporter=InMemoryLogExporter())
    assert tel.tracer_provider is None
    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        return "ok"

    tel.init_app(app)
    tel.tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    app.test_client().get("/")
    tel.force_flush()
    assert span_exporter.get_finished_spans()
