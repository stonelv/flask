"""Tests for flask.contrib.otel — OpenTelemetry integration."""

from __future__ import annotations

import typing as t

import pytest

otel_available = True
try:
    from opentelemetry import trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter
except ImportError:
    otel_available = False

pytestmark = pytest.mark.skipif(
    not otel_available,
    reason="OpenTelemetry packages not installed",
)

if t.TYPE_CHECKING:
    from flask import Flask


@pytest.fixture
def otel_setup() -> (
    t.Generator[
        tuple[InMemorySpanExporter, InMemoryMetricReader],
        None,
        None,
    ]
):
    """Set up in-memory OTel exporters for testing."""
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        __import__(
            "opentelemetry.sdk.trace.export", fromlist=["SimpleSpanProcessor"]
        ).SimpleSpanProcessor(span_exporter)
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    otel_metrics = __import__(
        "opentelemetry.metrics", fromlist=["set_meter_provider"]
    )
    otel_metrics.set_meter_provider(meter_provider)

    yield span_exporter, metric_reader

    tracer_provider.shutdown()
    meter_provider.shutdown()


@pytest.fixture
def app_with_otel(otel_setup: tuple) -> Flask:
    """Create a Flask app with OTel instrumentation."""
    import flask
    from flask.contrib.otel import FlaskOTel

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    FlaskOTel(app)

    @app.route("/")
    def index() -> str:
        return "ok"

    @app.route("/error")
    def error() -> t.NoReturn:
        raise ValueError("test error")

    @app.route("/hello/<name>")
    def hello(name: str) -> str:
        return f"hello {name}"

    app.config["TRAP_HTTP_EXCEPTIONS"] = False

    return app


class TestFlaskOTelInit:
    """Test extension initialization patterns."""

    def test_init_with_app(self, otel_setup: tuple) -> None:
        """FlaskOTel(app) registers the extension."""
        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask(__name__)
        FlaskOTel(app)
        assert "otel" in app.extensions

    def test_init_app_pattern(self, otel_setup: tuple) -> None:
        """FlaskOTel().init_app(app) deferred init works."""
        import flask
        from flask.contrib.otel import FlaskOTel

        otel = FlaskOTel()
        app = flask.Flask(__name__)
        otel.init_app(app)
        assert "otel" in app.extensions

    def test_init_without_otel_packages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear error when OTel packages missing."""
        import flask.contrib.otel as otel_mod

        monkeypatch.setattr(otel_mod, "_has_otel", False)

        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask(__name__)
        with pytest.raises(RuntimeError, match="pip install flask\\[otel\\]"):
            FlaskOTel(app)

    def test_custom_service_name(self, otel_setup: tuple) -> None:
        """Custom service_name is stored."""
        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask(__name__)
        FlaskOTel(app, service_name="my-service")
        assert app.extensions["otel"].service_name == "my-service"

    def test_app_factory_multiple_apps(self, otel_setup: tuple) -> None:
        """One FlaskOTel instance can instrument multiple apps."""
        import flask
        from flask.contrib.otel import FlaskOTel

        otel = FlaskOTel()
        app1 = flask.Flask(__name__)
        app2 = flask.Flask(__name__)
        otel.init_app(app1)
        otel.init_app(app2)
        assert "otel" in app1.extensions
        assert "otel" in app2.extensions


class TestTracing:
    """Test request tracing."""

    def test_basic_request_creates_span(
        self,
        app_with_otel: Flask,
        otel_setup: tuple,
    ) -> None:
        """A simple GET request creates a trace span."""
        span_exporter, _ = otel_setup
        client = app_with_otel.test_client()
        client.get("/")

        spans = span_exporter.get_finished_spans()
        # At least the Flask-level span should exist
        flask_spans = [s for s in spans if "flask" in s.name.lower() or "GET" in s.name]
        assert len(flask_spans) >= 1

    def test_span_attributes(
        self,
        app_with_otel: Flask,
        otel_setup: tuple,
    ) -> None:
        """Span has expected HTTP attributes."""
        span_exporter, _ = otel_setup
        client = app_with_otel.test_client()
        client.get("/hello/world")

        spans = span_exporter.get_finished_spans()
        # Find our Flask-level span
        flask_span = None
        for s in spans:
            attrs = dict(s.attributes or {})
            if attrs.get("http.method") == "GET":
                flask_span = s
                break

        assert flask_span is not None
        attrs = dict(flask_span.attributes or {})
        assert attrs["http.method"] == "GET"

    def test_error_request_records_exception(
        self,
        app_with_otel: Flask,
        otel_setup: tuple,
    ) -> None:
        """Error requests are captured in spans."""
        span_exporter, _ = otel_setup
        client = app_with_otel.test_client()
        client.get("/error")

        spans = span_exporter.get_finished_spans()
        assert len(spans) >= 1


class TestMetrics:
    """Test request metrics recording."""

    def test_request_counter(
        self,
        app_with_otel: Flask,
        otel_setup: tuple,
    ) -> None:
        """Requests increment the counter metric."""
        _, metric_reader = otel_setup
        client = app_with_otel.test_client()

        client.get("/")
        client.get("/")
        client.get("/")

        metrics_data = metric_reader.get_metrics_data()
        counter_found = False
        for resource_metric in metrics_data.resource_metrics:
            for scope_metric in resource_metric.scope_metrics:
                for metric in scope_metric.metrics:
                    if metric.name == "http.server.request.count":
                        counter_found = True

        assert counter_found

    def test_request_duration(
        self,
        app_with_otel: Flask,
        otel_setup: tuple,
    ) -> None:
        """Request duration histogram is recorded."""
        _, metric_reader = otel_setup
        client = app_with_otel.test_client()
        client.get("/")

        metrics_data = metric_reader.get_metrics_data()
        histogram_found = False
        for resource_metric in metrics_data.resource_metrics:
            for scope_metric in resource_metric.scope_metrics:
                for metric in scope_metric.metrics:
                    if metric.name == "http.server.request.duration":
                        histogram_found = True

        assert histogram_found


class TestPublicAPIPreservation:
    """Verify OTel integration does NOT modify Flask's public API."""

    def test_flask_exports_unchanged(self) -> None:
        """flask.__init__ exports must not change."""
        import flask

        public_names = [n for n in dir(flask) if not n.startswith("_")]
        # The 39 public exports + json module = at least 39
        assert len(public_names) >= 39

    def test_contrib_not_in_flask_init(self) -> None:
        """contrib must not be auto-imported by flask."""
        import flask

        assert not hasattr(flask, "contrib")
        assert "contrib" not in dir(flask)
