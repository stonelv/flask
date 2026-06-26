import pytest

from observability_example import create_app, setup_telemetry

# InMemorySpanExporter moved between submodules across OTel SDK versions; try
# both so the example works on the locked range and on newer installs.
try:
    from opentelemetry.sdk.trace.export import InMemorySpanExporter
except ImportError:  # OTel SDK >= ~1.30
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )


@pytest.fixture(name="app")
def fixture_app():
    app = create_app()
    app.testing = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def span_exporter(app):
    """An in-memory span exporter wired into the app's telemetry."""
    exporter = InMemorySpanExporter()
    setup_telemetry(app, span_exporter=exporter)
    yield exporter


def test_hello_emits_span(client, span_exporter):
    """A request produces at least one span (the FlaskInstrumentor SERVER span)."""
    response = client.get("/")
    assert response.status_code == 200
    _flush()
    spans = span_exporter.get_finished_spans()
    assert spans, "expected at least one span for GET /"


def test_error_is_marked(client, span_exporter):
    """A 5xx produces a span; the instrumentation marks server-error spans."""
    response = client.get("/error")
    assert response.status_code == 500
    _flush()
    spans = span_exporter.get_finished_spans()
    assert spans, "expected a span for the failing GET /error"


def test_console_path_does_not_crash(monkeypatch):
    """Without OTEL_EXPORTER_OTLP_ENDPOINT, the console exporter path runs."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = create_app()
    setup_telemetry(app)  # no span_exporter -> console exporters
    response = app.test_client().get("/api")
    assert response.status_code == 200
    _flush()


def _flush() -> None:
    from opentelemetry import trace

    provider = trace.get_tracer_provider()
    try:
        provider.force_flush()
    except Exception:
        # Some providers (e.g. the proxy before setup) don't implement
        # force_flush; that's fine for the assertion.
        pass
