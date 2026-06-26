"""Test OpenTelemetry tracing integration."""

import pytest

pytest.importorskip("opentelemetry")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.status import StatusCode

from flask import Flask
from flask.observability import init_observability


def _setup_tracing(app, exporter):
    """Set up tracing for an app using an already-set provider."""
    processor = SimpleSpanProcessor(exporter)
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(processor)
    init_observability(app, exporter="none", tracing=True, metrics=False, request_id=False)


def _reset_tracer_provider():
    """Reset the global tracer provider for test isolation."""
    # OTel API prevents overriding the provider, so we reset the internal flag
    provider = TracerProvider()
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace.set_tracer_provider(provider)


def _make_instrumented_app():
    """Create a Flask app with tracing and an in-memory span exporter."""
    _reset_tracer_provider()

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = True

    init_observability(app, exporter="none", tracing=True, metrics=False, request_id=False)

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    @app.route("/error")
    def error():
        raise ValueError("Test error")

    @app.route("/status/<int:code>")
    def status(code):
        from flask import abort

        abort(code)

    return app, exporter


def test_tracing_creates_span():
    """Test that a span is created for each request."""
    app, exporter = _make_instrumented_app()

    client = app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200

    spans = exporter.get_finished_spans()
    assert len(spans) >= 1
    names = [s.name for s in spans]
    assert any("/hello" in n for n in names)


def test_tracing_sets_http_attributes():
    """Test that HTTP attributes are set on spans."""
    app, exporter = _make_instrumented_app()

    client = app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200

    spans = exporter.get_finished_spans()
    # Find the span for our request
    hello_spans = [s for s in spans if s.attributes.get("http.method") == "GET"]
    assert len(hello_spans) >= 1

    span = hello_spans[0]
    assert span.attributes.get("http.method") == "GET"
    assert span.attributes.get("http.status_code") == 200


def test_tracing_records_exceptions():
    """Test that exceptions are recorded on spans."""
    app, exporter = _make_instrumented_app()

    client = app.test_client()

    with pytest.raises(ValueError, match="Test error"):
        client.get("/error")

    spans = exporter.get_finished_spans()
    assert len(spans) >= 1

    # At least one span should have error status
    error_spans = [s for s in spans if s.status.status_code == StatusCode.ERROR]
    assert len(error_spans) >= 1


def test_tracing_sets_status_code():
    """Test that span status reflects HTTP status code."""
    app, exporter = _make_instrumented_app()

    client = app.test_client()

    # Test 200 OK
    response = client.get("/hello")
    assert response.status_code == 200

    spans = exporter.get_finished_spans()
    ok_spans = [s for s in spans if s.status.status_code == StatusCode.OK]
    assert len(ok_spans) >= 1


def test_tracing_disabled():
    """Test that no spans are created when tracing is disabled."""
    _reset_tracer_provider()

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    app = Flask(__name__)
    init_observability(app, exporter="none", tracing=False, metrics=False, request_id=False)

    @app.route("/hello")
    def hello():
        return "Hello"

    client = app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200

    spans = exporter.get_finished_spans()
    assert len(spans) == 0
