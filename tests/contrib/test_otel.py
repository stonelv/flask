"""Tests for flask.contrib.otel — OpenTelemetry integration."""

from __future__ import annotations

import logging
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

# ------------------------------------------------------------------ #
# Module-level providers (OTel forbids resetting globals)            #
# ------------------------------------------------------------------ #

_span_exporter: InMemorySpanExporter | None = None
_metric_reader: InMemoryMetricReader | None = None
_providers_ready = False


def _ensure_providers() -> tuple[InMemorySpanExporter, InMemoryMetricReader]:
    global _span_exporter, _metric_reader, _providers_ready  # noqa: PLW0603
    if not _providers_ready:
        _span_exporter = InMemorySpanExporter()
        tp = TracerProvider()
        tp.add_span_processor(SimpleSpanProcessor(_span_exporter))
        trace.set_tracer_provider(tp)

        _metric_reader = InMemoryMetricReader()
        mp = MeterProvider(metric_readers=[_metric_reader])
        set_meter_provider(mp)
        _providers_ready = True

    assert _span_exporter is not None
    assert _metric_reader is not None
    return _span_exporter, _metric_reader


@pytest.fixture(autouse=True)
def _clear_otel_data() -> None:
    se, mr = _ensure_providers()
    se.clear()
    mr.get_metrics_data()


@pytest.fixture
def otel_env() -> tuple[InMemorySpanExporter, InMemoryMetricReader]:
    return _ensure_providers()


# ------------------------------------------------------------------ #
# Helper: build an instrumented app                                  #
# ------------------------------------------------------------------ #


def _make_app(
    *,
    excluded_urls: str | None = None,
    enable_logging: bool = True,
) -> Flask:
    import flask
    from flask.contrib.otel import FlaskOTel

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
    FlaskOTel(
        app,
        excluded_urls=excluded_urls,
        enable_logging=enable_logging,
    )

    @app.route("/")
    def index() -> str:
        return "ok"

    @app.route("/error")
    def error() -> t.NoReturn:
        raise ValueError("test error")

    @app.route("/hello/<name>")
    def hello(name: str) -> str:
        return f"hello {name}"

    @app.route("/health")
    def health() -> str:
        return "healthy"

    @app.route("/log")
    def log_it() -> str:
        app.logger.info("traced log message")
        return "logged"

    return app


@pytest.fixture
def app(otel_env: tuple) -> Flask:
    return _make_app()


# ------------------------------------------------------------------ #
# Helpers                                                            #
# ------------------------------------------------------------------ #


def _flask_spans(
    exporter: InMemorySpanExporter,
) -> list:
    """Return only the Flask-level spans (have ``flask.endpoint``)."""
    return [
        s
        for s in exporter.get_finished_spans()
        if "flask.endpoint" in (s.attributes or {})
    ]


def _wsgi_spans(exporter: InMemorySpanExporter) -> list:
    """Return WSGI-middleware spans (have ``http.method`` but no
    ``flask.endpoint``)."""
    return [
        s
        for s in exporter.get_finished_spans()
        if "http.method" in (s.attributes or {})
        and "flask.endpoint" not in (s.attributes or {})
    ]


def _metric_names(reader: InMemoryMetricReader) -> set[str]:
    data = reader.get_metrics_data()
    names: set[str] = set()
    if data is None:
        return names
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                names.add(m.name)
    return names


def _metric_points(
    reader: InMemoryMetricReader, name: str
) -> list[dict[str, t.Any]]:
    """Return data-point attribute dicts for a given metric name."""
    data = reader.get_metrics_data()
    pts: list[dict[str, t.Any]] = []
    if data is None:
        return pts
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                if m.name == name:
                    for dp in m.data.data_points:
                        pts.append(dict(dp.attributes))
    return pts


# ================================================================== #
# Init tests                                                         #
# ================================================================== #


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

    def test_missing_packages_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import flask
        import flask.contrib.otel as mod
        from flask.contrib.otel import FlaskOTel

        monkeypatch.setattr(mod, "_has_otel", False)
        otel = FlaskOTel()
        with pytest.raises(RuntimeError, match="pip install flask"):
            otel.init_app(flask.Flask(__name__))

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
        a1, a2 = flask.Flask("a1"), flask.Flask("a2")
        otel.init_app(a1)
        otel.init_app(a2)
        assert a1.extensions["otel"] is not a2.extensions["otel"]


# ================================================================== #
# Tracing tests                                                      #
# ================================================================== #


class TestTracing:
    def test_flask_span_created(
        self, app: Flask, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app.test_client().get("/")
        assert len(_flask_spans(se)) == 1

    def test_wsgi_span_created(
        self, app: Flask, otel_env: tuple
    ) -> None:
        """WSGI middleware must produce a transport-level span."""
        se, _ = otel_env
        app.test_client().get("/")
        assert len(_wsgi_spans(se)) >= 1

    def test_flask_span_attributes(
        self, app: Flask, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app.test_client().get("/hello/world")
        fs = _flask_spans(se)
        assert len(fs) == 1
        a = dict(fs[0].attributes or {})
        assert a["http.method"] == "GET"
        assert a["http.route"] == "/hello/<name>"
        assert a["flask.endpoint"] == "hello"
        assert a["http.scheme"] == "http"

    def test_error_span_status(
        self, app: Flask, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        resp = app.test_client().get("/error")
        assert resp.status_code == 500
        fs = _flask_spans(se)
        assert len(fs) == 1
        a = dict(fs[0].attributes or {})
        assert a["http.status_code"] == 500

    def test_no_duplicate_flask_spans(
        self, app: Flask, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app.test_client().get("/")
        assert len(_flask_spans(se)) == 1

    def test_no_context_leak(
        self, app: Flask, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        c = app.test_client()
        c.get("/")
        c.get("/hello/x")
        fs = _flask_spans(se)
        assert len(fs) == 2
        assert len({s.context.span_id for s in fs}) == 2


# ================================================================== #
# excluded_urls tests                                                #
# ================================================================== #


class TestExcludedUrls:
    def test_excluded_url_no_flask_span(
        self, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app = _make_app(excluded_urls="/health")
        app.test_client().get("/health")
        assert len(_flask_spans(se)) == 0

    def test_excluded_url_no_metrics(
        self, otel_env: tuple
    ) -> None:
        _, mr = otel_env
        app = _make_app(excluded_urls="/health")
        app.test_client().get("/health")
        pts = _metric_points(mr, "http.server.request.count")
        assert all(
            p.get("http.route") != "/health" for p in pts
        )

    def test_non_excluded_url_still_traced(
        self, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app = _make_app(excluded_urls="/health")
        app.test_client().get("/")
        assert len(_flask_spans(se)) == 1

    def test_multiple_excluded(
        self, otel_env: tuple
    ) -> None:
        se, _ = otel_env
        app = _make_app(excluded_urls="/health,/hello")
        c = app.test_client()
        c.get("/health")
        c.get("/hello/x")
        c.get("/")
        assert len(_flask_spans(se)) == 1  # only "/"


# ================================================================== #
# Metrics tests                                                      #
# ================================================================== #


class TestMetrics:
    def test_counter_recorded(
        self, app: Flask, otel_env: tuple
    ) -> None:
        _, mr = otel_env
        c = app.test_client()
        c.get("/")
        c.get("/")
        assert "http.server.request.count" in _metric_names(mr)

    def test_duration_recorded(
        self, app: Flask, otel_env: tuple
    ) -> None:
        _, mr = otel_env
        app.test_client().get("/")
        assert "http.server.request.duration" in _metric_names(mr)

    def test_error_route_counted_as_500(
        self, app: Flask, otel_env: tuple
    ) -> None:
        _, mr = otel_env
        app.test_client().get("/error")
        pts = _metric_points(mr, "http.server.request.count")
        assert any(p.get("http.status_code") == 500 for p in pts)

    def test_metric_labels(
        self, app: Flask, otel_env: tuple
    ) -> None:
        _, mr = otel_env
        app.test_client().get("/hello/world")
        pts = _metric_points(mr, "http.server.request.count")
        matching = [
            p for p in pts if p.get("http.route") == "/hello/<name>"
        ]
        assert len(matching) == 1
        assert matching[0]["http.method"] == "GET"
        assert matching[0]["http.status_code"] == 200


# ================================================================== #
# Logging integration tests                                          #
# ================================================================== #


class TestLogging:
    def test_trace_id_injected(
        self, otel_env: tuple
    ) -> None:
        app = _make_app(enable_logging=True)
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        app.logger.addHandler(_Capture())
        app.logger.setLevel(logging.DEBUG)
        app.test_client().get("/log")

        assert len(records) >= 1
        rec = records[-1]
        assert hasattr(rec, "otel_trace_id")
        assert hasattr(rec, "otel_span_id")
        assert rec.otel_trace_id != "0" * 32  # type: ignore[attr-defined]

    def test_logging_disabled(
        self, otel_env: tuple
    ) -> None:
        """When enable_logging=False the extension must not install its
        own log filter on the app logger."""
        import flask
        from flask.contrib.otel import FlaskOTel

        app = flask.Flask("logging_disabled_test")
        app.config["TESTING"] = True
        app.config["PROPAGATE_EXCEPTIONS"] = False
        FlaskOTel(app, enable_logging=False)

        # The _OTelLogFilter should NOT be among the filters
        filter_classes = [type(f).__name__ for f in app.logger.filters]
        assert "_OTelLogFilter" not in filter_classes


# ================================================================== #
# API preservation                                                   #
# ================================================================== #


class TestAPIPreservation:
    def test_flask_exports_unchanged(self) -> None:
        import flask

        public = [n for n in dir(flask) if not n.startswith("_")]
        assert len(public) >= 39

    def test_contrib_not_in_init_source(self) -> None:
        import flask

        assert flask.__file__ is not None
        with open(flask.__file__) as f:
            assert "contrib" not in f.read()
