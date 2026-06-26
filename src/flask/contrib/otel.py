"""OpenTelemetry integration for Flask.

Provides automatic tracing, metrics, and structured logging for Flask
applications using the OpenTelemetry standard.

Install with::

    pip install flask[otel]

Usage::

    from flask import Flask
    from flask.contrib.otel import FlaskOTel

    app = Flask(__name__)
    otel = FlaskOTel(app)

Or with the application factory pattern::

    otel = FlaskOTel()

    def create_app():
        app = Flask(__name__)
        otel.init_app(app)
        return app

.. versionadded:: 3.2
"""

from __future__ import annotations

import logging
import time
import typing as t

if t.TYPE_CHECKING:
    from flask import Flask
    from flask.wrappers import Response

_MISSING_OTEL = (
    "OpenTelemetry packages are required for FlaskOTel. "
    "Install them with: pip install flask[otel]"
)

try:
    from opentelemetry import context as otel_context
    from opentelemetry import trace
    from opentelemetry.metrics import get_meter
    from opentelemetry.trace import StatusCode

    _has_otel = True
except ImportError:
    _has_otel = False


class FlaskOTel:
    """OpenTelemetry integration extension for Flask.

    Automatically instruments a Flask application with:

    - **Tracing**: Creates a span for each request capturing method,
      route, blueprint, endpoint, and status code.
    - **Metrics**: Records ``http.server.request.duration`` histogram
      and ``http.server.request.count`` counter, labeled by route,
      method, and status code.
    - **Logging**: Optionally injects trace and span IDs into Python
      log records for correlation.

    :param app: The Flask application to instrument. If not provided,
        call :meth:`init_app` later.
    :param service_name: Override the service name reported to
        OpenTelemetry. Defaults to ``app.name``.
    :param excluded_urls: Comma-separated URL patterns to exclude
        from tracing (e.g. ``"/health,/ready"``).
    :param enable_logging: Whether to inject trace/span IDs into
        log records. Defaults to ``True``.
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        service_name: str | None = None,
        excluded_urls: str | None = None,
        enable_logging: bool = True,
    ) -> None:
        self._service_name = service_name
        self._excluded_urls = excluded_urls
        self._enable_logging = enable_logging

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the extension with a Flask application.

        :param app: The Flask application to instrument.
        :raises RuntimeError: If OpenTelemetry packages are not
            installed.
        """
        if not _has_otel:
            raise RuntimeError(_MISSING_OTEL)

        service_name = self._service_name or app.name

        state = _OTelState(
            service_name=service_name,
            excluded_urls=self._excluded_urls,
            enable_logging=self._enable_logging,
        )
        state.setup(app)
        app.extensions["otel"] = state


class _OTelState:
    """Per-app OpenTelemetry state stored in ``app.extensions['otel']``.

    Keeps tracers, meters, and hook references scoped to a single
    Flask application instance.
    """

    def __init__(
        self,
        service_name: str,
        excluded_urls: str | None,
        enable_logging: bool,
    ) -> None:
        self.service_name = service_name
        self.excluded_urls = excluded_urls
        self.enable_logging = enable_logging

        self.tracer = trace.get_tracer(
            "flask.contrib.otel",
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )
        meter = get_meter(
            "flask.contrib.otel",
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )
        self.request_counter = meter.create_counter(
            "http.server.request.count",
            unit="requests",
            description="Number of HTTP requests received",
        )
        self.request_duration = meter.create_histogram(
            "http.server.request.duration",
            unit="ms",
            description="HTTP request duration in milliseconds",
        )

    def setup(self, app: Flask) -> None:
        """Wire up request hooks and optional logging."""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

        if self.enable_logging:
            self._setup_logging(app)

    # ------------------------------------------------------------------
    # Request lifecycle hooks
    # ------------------------------------------------------------------

    def _before_request(self) -> None:
        """Start a span and record request start time."""
        from flask import g
        from flask import request as req

        g._otel_start_time = time.perf_counter()

        route = req.url_rule.rule if req.url_rule else req.path
        span = self.tracer.start_span(
            f"{req.method} {route}",
            attributes={
                "http.method": req.method,
                "http.url": req.url,
                "http.route": route,
                "http.scheme": req.scheme,
                "flask.endpoint": req.endpoint or "",
                "flask.blueprint": (
                    req.blueprints[0] if req.blueprints else ""
                ),
            },
        )
        token = otel_context.attach(trace.set_span_in_context(span))
        g._otel_span = span
        g._otel_token = token

    def _after_request(self, response: Response) -> Response:
        """Record metrics and finalise the span on success."""
        from flask import g
        from flask import request as req

        span = getattr(g, "_otel_span", None)
        if span is not None and span.is_recording():
            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(StatusCode.ERROR)
            else:
                span.set_status(StatusCode.OK)
            span.end()
            g._otel_span = None  # mark as consumed

        token = getattr(g, "_otel_token", None)
        if token is not None:
            otel_context.detach(token)
            g._otel_token = None

        # Metrics
        start = getattr(g, "_otel_start_time", None)
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000
            route = req.url_rule.rule if req.url_rule else req.path
            labels = {
                "http.method": req.method,
                "http.route": route,
                "http.status_code": response.status_code,
            }
            self.request_counter.add(1, labels)
            self.request_duration.record(duration_ms, labels)

        return response

    def _teardown_request(self, exc: BaseException | None) -> None:
        """Ensure span is ended on error paths not reached by after_request."""
        from flask import g

        span = getattr(g, "_otel_span", None)
        if span is not None and span.is_recording():
            if exc is not None:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
            span.end()
            g._otel_span = None

        token = getattr(g, "_otel_token", None)
        if token is not None:
            otel_context.detach(token)
            g._otel_token = None

    # ------------------------------------------------------------------
    # Logging integration
    # ------------------------------------------------------------------

    @staticmethod
    def _setup_logging(app: Flask) -> None:
        """Inject ``otel_trace_id`` / ``otel_span_id`` into log records."""

        class _OTelLogFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                span = trace.get_current_span()
                ctx = span.get_span_context()
                if ctx and ctx.trace_id:
                    record.otel_trace_id = format(  # type: ignore[attr-defined]
                        ctx.trace_id, "032x"
                    )
                    record.otel_span_id = format(  # type: ignore[attr-defined]
                        ctx.span_id, "016x"
                    )
                else:
                    record.otel_trace_id = "0" * 32  # type: ignore[attr-defined]
                    record.otel_span_id = "0" * 16  # type: ignore[attr-defined]
                return True

        app.logger.addFilter(_OTelLogFilter())
