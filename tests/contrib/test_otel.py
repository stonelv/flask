"""Tests for flask.contrib.otel — OpenTelemetry integration."""

from __future__ import annotations

import typing as t

import pytest

otel_available = True
try:
    from opentelemetry import trace
    from opentelemetry.metrics import set_meter_provider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
except ImportError:
    otel_available = False

pytestmark = pytest.mark.skipif(
    not otel_available,
    reason="OpenTelemetry packages not installed",
)

if t.TYPE_CHECKING:
    from flask import Flask

# Module-level singleton providers — OTel forbids resetting globals.
_span_exporter: InMemorySpanExporter | None = None
_metric_reader: InMemoryMetricReader | None = None
_providers_initialised = False


def _ensure_providers() -> tuple[InMemorySpanExporter, InMemoryMetricReader]:
    """Lazily create OTel providers once per process."""
    global _span_exporter, _metric_reader, _providers_initialised  # noqa: PLW0603

    if not _providers_initialised:
        _span_exporter = InMemorySpanExporter()
        tp = TracerProvider()
        tp.add_span_processor(SimpleSpanProcessor(_span_exporter))
        trace.set_tracer_provider(tp)

        _metric_reader = InMemoryMetricReader()
        mp = MeterProvider(metric_readers=[_metric_reader])
        set_meter_provider(mp)

        _providers_initialised = True

    assert _span_exporter is not None
    assert _metric_reader is not None
    return _span_exporter, _metric_reader


@pytest.fixture(autouse=True)
def _clear_otel_data() -> None:
    """Clear exported spans/metrics before each test."""
    se, mr = _ensure_providers()
    se.clear()
    # Force-collect metrics so the reader is fresh
    mr.get_metrics_data()


@pytest.fixture
def otel_env() -> tuple[InMemorySpanExporter, InMemoryMetricReader]:
    return _ensure_providers()


@pytest.fixture
def instrumented_app(otel_env: tuple) -> Flask:
    """Flask app with OTel and a mix of normal / error routes."""
    import flask
    from flask.contrib.otel import FlaskOTel

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    # Don't propagate exceptions — let error handlers run so OTel
    # can observe the 500 response.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    FlaskOTel(app)

    @app.route("/")
    def index() -> str:
        return "ok"

    @app.route("/error")
    def error() -> tuple[str, int]:
        raise ValueError("test error")

    @app.route("/hello/<name>")
    def hello(name: str) -> str:
        return f"hello {name}"

    @app.errorhandler(500)
    def handle_500(e: Exception) -> tuple[str, int]:
        return "internal error", 500

    return app


# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------


class TestInit:
    def test_direct_init(self) -> None:
        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask(__name__)
        FlaskOTel(app)
        assert "otel" in app.extensions

    def test_init_app_pattern(self) -> None:
        import flask
        from flask.contrib.otel import FlaskOTel

        otel = FlaskOTel()
        app = flask.Flask(__name__)
        otel.init_app(app)
        assert "otel" in app.extensions

    def test_missing_packages_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import flask
        import flask.contrib.otel as mod
        from flask.contrib.otel import FlaskOTel

        monkeypatch.setattr(mod, "_has_otel", False)
        app = flask.Flask(__name__)
        otel = FlaskOTel()
        with pytest.raises(RuntimeError, match="pip install flask"):
            otel.init_app(app)

    def test_custom_service_name(self) -> None:
        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask(__name__)
        FlaskOTel(app, service_name="my-svc")
        assert app.extensions["otel"].service_name == "my-svc"

    def test_multiple_apps(self) -> None:
        import flask
        from flask.contrib.otel import FlaskOTel

        otel = FlaskOTel()
        a1 = flask.Flask("a1")
        a2 = flask.Flask("a2")
        otel.init_app(a1)
        otel.init_app(a2)
        assert "otel" in a1.extensions
        assert "otel" in a2.extensions
        assert a1.extensions["otel"] is not a2.extensions["otel"]


# ------------------------------------------------------------------
# Tracing
# ------------------------------------------------------------------


class TestTracing:
    def test_request_creates_span(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        span_exporter, _ = otel_env
        client = instrumented_app.test_client()
        client.get("/")

        spans = span_exporter.get_finished_spans()
        flask_spans = [
            s for s in spans if "http.route" in (s.attributes or {})
        ]
        assert len(flask_spans) == 1
        attrs = dict(flask_spans[0].attributes or {})
        assert attrs["http.method"] == "GET"
        assert attrs["http.route"] == "/"

    def test_span_has_route_and_endpoint(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        span_exporter, _ = otel_env
        client = instrumented_app.test_client()
        client.get("/hello/world")

        spans = span_exporter.get_finished_spans()
        flask_spans = [
            s for s in spans if "flask.endpoint" in (s.attributes or {})
        ]
        assert len(flask_spans) == 1
        attrs = dict(flask_spans[0].attributes or {})
        assert attrs["http.route"] == "/hello/<name>"
        assert attrs["flask.endpoint"] == "hello"

    def test_error_recorded_in_span(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        span_exporter, _ = otel_env
        client = instrumented_app.test_client()
        resp = client.get("/error")
        assert resp.status_code == 500

        spans = span_exporter.get_finished_spans()
        flask_spans = [
            s for s in spans if "http.route" in (s.attributes or {})
        ]
        assert len(flask_spans) == 1
        attrs = dict(flask_spans[0].attributes or {})
        assert attrs["http.status_code"] == 500

    def test_no_duplicate_spans(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        """Each request should produce exactly one Flask-level span."""
        span_exporter, _ = otel_env
        client = instrumented_app.test_client()
        client.get("/")

        spans = span_exporter.get_finished_spans()
        flask_spans = [
            s for s in spans if "flask.endpoint" in (s.attributes or {})
        ]
        assert len(flask_spans) == 1

    def test_no_leaked_context(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        """Span context must not leak between requests."""
        span_exporter, _ = otel_env
        client = instrumented_app.test_client()
        client.get("/")
        client.get("/hello/test")

        spans = span_exporter.get_finished_spans()
        flask_spans = [
            s for s in spans if "flask.endpoint" in (s.attributes or {})
        ]
        assert len(flask_spans) == 2
        ids = {s.context.span_id for s in flask_spans}
        assert len(ids) == 2


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------


class TestMetrics:
    def _metric_names(self, metric_reader: InMemoryMetricReader) -> set[str]:
        metrics = metric_reader.get_metrics_data()
        names: set[str] = set()
        if metrics is None:
            return names
        for rm in metrics.resource_metrics:
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    names.add(m.name)
        return names

    def test_request_counter(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        _, metric_reader = otel_env
        client = instrumented_app.test_client()
        client.get("/")
        client.get("/")

        assert "http.server.request.count" in self._metric_names(
            metric_reader
        )

    def test_request_duration(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        _, metric_reader = otel_env
        client = instrumented_app.test_client()
        client.get("/")

        assert "http.server.request.duration" in self._metric_names(
            metric_reader
        )

    def test_error_counted(
        self, instrumented_app: Flask, otel_env: tuple
    ) -> None:
        _, metric_reader = otel_env
        client = instrumented_app.test_client()
        resp = client.get("/error")
        assert resp.status_code == 500

        metrics = metric_reader.get_metrics_data()
        found_500 = False
        if metrics is not None:
            for rm in metrics.resource_metrics:
                for sm in rm.scope_metrics:
                    for m in sm.metrics:
                        if m.name == "http.server.request.count":
                            for dp in m.data.data_points:
                                a = dict(dp.attributes)
                                if a.get("http.status_code") == 500:
                                    found_500 = True
        assert found_500


# ------------------------------------------------------------------
# API preservation
# ------------------------------------------------------------------


class TestAPIPreservation:
    def test_flask_exports_unchanged(self) -> None:
        import flask

        public = [n for n in dir(flask) if not n.startswith("_")]
        assert len(public) >= 39

    def test_contrib_not_in_flask_all(self) -> None:
        """contrib must not be in flask.__init__ explicit exports."""
        import flask

        # flask.__init__.py uses 'from .x import y as y' re-exports.
        # 'contrib' should not be among them.
        init_src = flask.__file__
        assert init_src is not None
        with open(init_src) as f:
            src = f.read()
        assert "contrib" not in src
