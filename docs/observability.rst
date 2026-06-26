.. _observability:

Observability with OpenTelemetry
================================

Flask includes an optional OpenTelemetry integration that provides
automatic tracing, metrics, and structured logging. Install it with
the ``otel`` extra:

.. code-block:: text

    pip install flask[otel]

Quickstart
----------

.. code-block:: python

    from flask import Flask
    from flask.contrib.otel import FlaskOTel

    app = Flask(__name__)
    otel = FlaskOTel(app)

    @app.route("/")
    def index():
        return "Hello, World!"

This automatically instruments the application with:

- **Traces**: A span is created for each HTTP request, capturing
  method, route, status code, and timing.
- **Metrics**: Request count and duration are recorded as
  OpenTelemetry metrics.
- **Logging**: Trace and span IDs are injected into Python log
  records for correlation.

Application Factory Pattern
----------------------------

.. code-block:: python

    from flask.contrib.otel import FlaskOTel

    otel = FlaskOTel()

    def create_app():
        app = Flask(__name__)
        otel.init_app(app)
        return app

Configuration
-------------

``FlaskOTel`` accepts these keyword arguments:

``service_name``
    Override the service name reported to OpenTelemetry backends.
    Defaults to ``app.name``.

``excluded_urls``
    Comma-separated URL patterns to exclude from tracing
    (e.g. ``"/health,/ready"``).

``enable_logging``
    Whether to inject ``otel_trace_id`` and ``otel_span_id`` into
    log records. Defaults to ``True``.

Exporter Setup
--------------

The extension uses whatever tracer and meter providers are globally
configured. For example, to export to an OTLP endpoint:

.. code-block:: python

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry import trace

    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
    )
    trace.set_tracer_provider(provider)

    # Then initialize Flask + FlaskOTel as usual.

Metrics Reference
-----------------

The following metrics are recorded:

``http.server.request.count`` (Counter)
    Number of HTTP requests, labeled by ``http.method``,
    ``http.route``, and ``http.status_code``.

``http.server.request.duration`` (Histogram)
    Request duration in milliseconds, with the same labels.

Benchmarks
----------

Flask ships a benchmark suite under ``benchmarks/`` that can be used
to establish performance baselines:

.. code-block:: text

    make bench
    # or
    tox run -e bench

Benchmark results are output in JSON format for CI comparison.
