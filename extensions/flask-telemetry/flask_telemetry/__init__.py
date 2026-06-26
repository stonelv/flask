"""flask-telemetry: a reusable OpenTelemetry extension for Flask.

This is a **separate, installable extension package**, not part of Flask core
(see ``docs/adr/0004-observability-as-optional-extension.md``). It follows the
standard Flask extension pattern — construct ``Telemetry(app)`` or call
``Telemetry().init_app(app)`` — and wires traces, metrics, and trace-correlated
logs through the documented ``opentelemetry-instrumentation-flask`` hooks.

Example::

    from flask import Flask
    from flask_telemetry import Telemetry

    app = Flask(__name__)
    Telemetry(app, service_name="my-service")

By default every signal exports over OTLP using the standard
``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable. Inject in-memory exporters
to test without a collector.
"""

from __future__ import annotations

import logging
import typing as t

from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter

if t.TYPE_CHECKING:
    from flask import Flask

__all__ = ["Telemetry"]
__version__ = "0.1.0"


class Telemetry:
    """Flask extension that wires OpenTelemetry traces, metrics, and logs.

    Follows the standard Flask extension protocol: pass ``app`` to configure
    immediately, or defer with :meth:`init_app`. After initialisation the
    instance is registered at ``app.extensions["telemetry"]`` and exposes
    ``tracer_provider``, ``meter_provider``, and ``logger_provider`` (useful for
    ``force_flush()`` in tests).
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        service_name: str = "flask-app",
        span_exporter: SpanExporter | None = None,
        metric_reader: MetricReader | None = None,
        log_exporter: LogExporter | None = None,
    ) -> None:
        self.service_name = service_name
        self._span_exporter = span_exporter
        self._metric_reader = metric_reader
        self._log_exporter = log_exporter
        self.tracer_provider: TracerProvider | None = None
        self.meter_provider: MeterProvider | None = None
        self.logger_provider: LoggerProvider | None = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> Telemetry:
        """Configure telemetry for ``app`` and register the extension."""
        resource = Resource.create({SERVICE_NAME: self.service_name})

        # --- Traces ---------------------------------------------------------
        span_exporter = self._span_exporter or self._default_span_exporter()
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        # --- Metrics --------------------------------------------------------
        metric_reader = self._metric_reader or self._default_metric_reader()
        meter_provider = MeterProvider(
            resource=resource, metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(meter_provider)

        # --- Logs (correlated with the active span) -------------------------
        log_exporter = self._log_exporter or self._default_log_exporter()
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
        LoggingInstrumentor().instrument(set_logging_format=True)

        # --- Flask request instrumentation ----------------------------------
        FlaskInstrumentor().instrument_app(
            app,
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )

        self.tracer_provider = tracer_provider
        self.meter_provider = meter_provider
        self.logger_provider = logger_provider
        app.extensions = getattr(app, "extensions", {})
        app.extensions["telemetry"] = self
        return self

    def force_flush(self) -> None:
        """Flush pending spans/metrics/logs. Mainly for tests and shutdown."""
        if self.tracer_provider is not None:
            self.tracer_provider.force_flush()
        if self.logger_provider is not None:
            self.logger_provider.force_flush()

    # -- default OTLP exporters (imported lazily so they're optional) --------
    @staticmethod
    def _default_span_exporter() -> SpanExporter:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter()

    @staticmethod
    def _default_metric_reader() -> MetricReader:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        return PeriodicExportingMetricReader(OTLPMetricExporter())

    @staticmethod
    def _default_log_exporter() -> LogExporter:
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

        return OTLPLogExporter()
