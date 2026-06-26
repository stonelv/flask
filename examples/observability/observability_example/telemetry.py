"""Wire OpenTelemetry logs/metrics/traces into a Flask app.

Exporter selection is environment-driven so the example runs with no
infrastructure:

* if ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, traces/metrics ship to a
  collector via OTLP/HTTP (see ``docker-compose.yml``);
* otherwise a ``ConsoleSpanExporter`` / ``ConsoleMetricExporter`` prints to
  stdout, so a plain ``flask run`` already shows the three signals.

Passing ``span_exporter`` (e.g. an ``InMemorySpanExporter``) wires that
exporter in instead -- used by the tests to assert spans are emitted.
"""

from __future__ import annotations

import time

from flask import g, got_request_exception, request

# Module-level guard so repeated calls (e.g. across tests) don't try to
# re-instrument logging.
_logging_instrumented = False


def _otlp_endpoint() -> str | None:
    """Read the OTLP endpoint at call time (not import time) so tests can
    toggle it with ``monkeypatch.delenv`` without reloading the module."""
    import os

    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")


def setup_telemetry(app, *, span_exporter=None) -> None:
    """Configure tracing, metrics, and logging for ``app``.

    Uses only public Flask seams: ``app.wsgi_app`` (via FlaskInstrumentor),
    the ``got_request_exception`` signal, and the ``before_request`` /
    ``after_request`` decorators. No ``src/flask`` change.
    """
    from opentelemetry import metrics, trace
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.trace import Status, StatusCode

    resource = Resource.create({"service.name": "flask-observability-example"})

    # --- traces: set the global provider only once (avoids the "overriding
    # is not allowed" warning), then attach the chosen span processor. ---
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

    if span_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    elif _otlp_endpoint():
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # --- metrics: skip entirely in unit tests (span_exporter set); otherwise
    # console or OTLP. Set the global meter provider only once. ---
    if span_exporter is None:
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )

        current = metrics.get_meter_provider()
        if not isinstance(current, MeterProvider):
            if _otlp_endpoint():
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                    OTLPMetricExporter,
                )

                reader = PeriodicExportingMetricReader(OTLPMetricExporter())
            else:
                reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
            metrics.set_meter_provider(
                MeterProvider(resource=resource, metric_readers=[reader])
            )

    # --- logs: add trace context to log records. Idempotent. ---
    global _logging_instrumented
    if not _logging_instrumented:
        LoggingInstrumentor().instrument(set_logging=True)
        _logging_instrumented = True

    # Auto-instrument Flask: wraps ``app.wsgi_app`` for SERVER spans + HTTP
    # metrics. This is the documented middleware seam -- no source change.
    FlaskInstrumentor().instrument_app(app)

    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)
    request_duration = meter.create_histogram("flask.request.duration", unit="ms")
    error_counter = meter.create_counter("flask.request.errors")

    @app.before_request
    def _start_timer() -> None:
        g._telemetry_start = time.perf_counter()

    @app.after_request
    def _record(response):
        start = getattr(g, "_telemetry_start", None) or time.perf_counter()
        duration_ms = (time.perf_counter() - start) * 1000
        attrs = {"route": request.path, "method": request.method}
        request_duration.record(duration_ms, attrs)
        if response.status_code >= 500:
            error_counter.add(1, {**attrs, "status": str(response.status_code)})
        return response

    @got_request_exception.connect_via(app)
    def _on_exception(_sender, exception=None, **_kwargs):
        # Custom span attributing unhandled exceptions (in addition to the
        # automatic SERVER span from FlaskInstrumentor).
        with tracer.start_as_current_span("flask.request.exception") as span:
            span.set_status(Status(StatusCode.ERROR, str(exception)))
            if exception is not None:
                span.record_exception(exception)
