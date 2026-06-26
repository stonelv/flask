"""Reusable OpenTelemetry wiring for a Flask app.

This module is deliberately self-contained and lives *outside* the Flask
package (see ``docs/adr/0004-observability-as-optional-extension.md``). Import
``configure_telemetry`` from your own app's entrypoint; Flask core never imports
any of this.

Signals produced:

* **Traces** — one span per request, via ``opentelemetry-instrumentation-flask``.
* **Metrics** — request duration/count histograms exported over OTLP. The Flask
  instrumentation emits ``http.server.*`` metrics automatically.
* **Logs** — standard ``logging`` records are stamped with the active
  ``trace_id``/``span_id`` so logs correlate with traces in your backend.

All exporters default to the OTLP endpoint from the standard environment
variable ``OTEL_EXPORTER_OTLP_ENDPOINT`` (e.g. ``http://localhost:4317``).
"""

from __future__ import annotations

import logging
import typing as t

from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if t.TYPE_CHECKING:
    from flask import Flask


def configure_telemetry(app: Flask, service_name: str = "flask-app") -> None:
    """Wire traces, metrics, and correlated logs into ``app``.

    Idempotent per process: call once during application setup.
    """
    resource = Resource.create({SERVICE_NAME: service_name})

    # --- Traces -------------------------------------------------------------
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ------------------------------------------------------------
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- Logs (correlated with the active span) -----------------------------
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    # injects trace_id/span_id into LogRecords so console logs correlate too
    LoggingInstrumentor().instrument(set_logging_format=True)

    # --- Flask request instrumentation -------------------------------------
    # Spans per request + http.server.* metrics, using Flask's stable WSGI
    # hooks. instrument_app touches only documented extension points.
    FlaskInstrumentor().instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
