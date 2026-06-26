.. _observability:

Observability
=============

Flask 3.2 includes built-in OpenTelemetry observability support, providing distributed tracing, metrics collection, request ID tracking, and structured logging.

Installation
------------

Install Flask with observability dependencies::

    pip install Flask[observability]

Or install manually::

    pip install opentelemetry-api opentelemetry-sdk

Quick Start
-----------

Enable observability in your Flask application:

.. code-block:: python

    from flask import Flask
    from flask.observability import init_observability

    app = Flask(__name__)
    init_observability(app)

This enables all observability features with default configuration:

- **Distributed Tracing**: Automatic span creation for HTTP requests
- **Metrics**: Request counts, durations, and error rates
- **Request IDs**: Automatic ``X-Request-ID`` header propagation
- **Structured Logging**: JSON-formatted logs with trace context

Features
--------

Distributed Tracing
~~~~~~~~~~~~~~~~~~~

Each HTTP request automatically creates a span with:

- HTTP method, URL, and status code
- Request duration
- Exception information (if an error occurs)
- Trace context propagation via ``X-B3-TraceId`` and ``X-B3-SpanId`` headers

Example trace output:

.. code-block:: text

    Span: GET /api/users
    ├─ Attributes:
    │  ├─ http.method: GET
    │  ├─ http.url: /api/users
    │  ├─ http.status_code: 200
    │  └─ http.target: /api/users
    └─ Duration: 45ms

Metrics
~~~~~~~

Flask automatically collects these metrics:

- ``flask.http.requests``: Total request count (counter)
- ``flask.http.duration``: Request duration histogram
- ``flask.http.errors``: Error count by status code
- ``flask.http.active_requests``: Currently active requests (gauge)

Metrics are exported to your configured OpenTelemetry collector.

Request ID Tracking
~~~~~~~~~~~~~~~~~~~

Flask automatically:

1. Generates a unique ``X-Request-ID`` for each request (if not provided)
2. Propagates incoming ``X-Request-ID`` headers
3. Adds the request ID to all log records
4. Returns the request ID in the response headers

Example:

.. code-block:: python

    from flask import request

    @app.route('/api/users')
    def get_users():
        # Request ID is available via:
        request_id = request.headers.get('X-Request-ID')
        # ... also automatically in all logs
        app.logger.info("Processing request")
        return users

Structured Logging
~~~~~~~~~~~~~~~~~~

When enabled, Flask logs are formatted as JSON with trace context:

.. code-block:: json

    {
      "timestamp": "2024-01-15T10:30:45.123Z",
      "level": "INFO",
      "logger": "flask.app",
      "message": "Processing request",
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
      "span_id": "00f067aa0ba902b7",
      "request_id": "req-12345"
    }

Configuration
-------------

``init_observability()`` accepts these parameters:

.. code-block:: python

    init_observability(
        app,
        service_name="my-flask-app",      # Service name for traces
        exporter="otlp",                   # Exporter: "otlp", "console", "none"
        tracing=True,                      # Enable/disable tracing
        metrics=True,                      # Enable/disable metrics
        request_id=True,                   # Enable/disable request ID tracking
        structured_logging=True,           # Enable/disable JSON logging
    )

Exporter Options
~~~~~~~~~~~~~~~~

**OTLP (default)**: Export to OpenTelemetry Collector

.. code-block:: python

    init_observability(app, exporter="otlp")

Set collector endpoint via environment variable:

.. code-block:: bash

    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

**Console**: Print traces/metrics to stdout (useful for debugging)

.. code-block:: python

    init_observability(app, exporter="console")

**None**: Disable export (useful for testing)

.. code-block:: python

    init_observability(app, exporter="none")

Selective Feature Enablement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable only specific features:

.. code-block:: python

    # Only tracing, no metrics
    init_observability(app, metrics=False)

    # Only metrics, no tracing
    init_observability(app, tracing=False)

    # Only request IDs, no observability
    init_observability(app, tracing=False, metrics=False, structured_logging=False)

Manual Instrumentation
----------------------

Create custom spans for specific operations:

.. code-block:: python

    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    @app.route('/api/users')
    def get_users():
        with tracer.start_as_current_span("database_query"):
            users = db.query_users()
        return users

Add custom attributes to spans:

.. code-block:: python

    from opentelemetry import trace

    @app.route('/api/users/<int:user_id>')
    def get_user(user_id):
        span = trace.get_current_span()
        span.set_attribute("user.id", user_id)
        # ... process request
        return user

Custom Metrics
~~~~~~~~~~~~~~

Create custom metrics:

.. code-block:: python

    from opentelemetry import metrics

    meter = metrics.get_meter(__name__)
    request_counter = meter.create_counter("custom.requests")

    @app.route('/api/checkout')
    def checkout():
        request_counter.add(1, {"endpoint": "checkout"})
        # ... process checkout
        return success

Performance Considerations
--------------------------

The observability module adds minimal overhead:

- **Tracing**: < 5% overhead (benchmarked)
- **Metrics**: < 2% overhead
- **Request IDs**: Negligible overhead
- **Structured Logging**: ~10% overhead (JSON serialization)

Disable features you don't need to minimize impact:

.. code-block:: python

    # Production: full observability
    init_observability(app)

    # High-throughput: metrics only
    init_observability(app, tracing=False, structured_logging=False)

    # Development: console output
    init_observability(app, exporter="console")

Troubleshooting
---------------

**No traces appearing**

1. Verify OpenTelemetry packages are installed: ``pip list | grep opentelemetry``
2. Check exporter configuration: ``exporter="otlp"`` or ``"console"``
3. Verify collector endpoint: ``export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"``

**High overhead**

1. Disable unused features: ``init_observability(app, tracing=False)``
2. Use sampling to reduce trace volume (configure in collector)
3. Disable structured logging if not needed

**Request IDs not propagating**

1. Ensure ``request_id=True`` in ``init_observability()``
2. Check for middleware that might strip headers
3. Verify clients are sending ``X-Request-ID`` headers

Examples
--------

Jaeger Integration
~~~~~~~~~~~~~~~~~~

Export traces to Jaeger:

.. code-block:: python

    from flask import Flask
    from flask.observability import init_observability

    app = Flask(__name__)

    # Set Jaeger endpoint
    import os
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

    init_observability(app, service_name="my-flask-app")

Prometheus Integration
~~~~~~~~~~~~~~~~~~~~~~

Export metrics to Prometheus:

.. code-block:: python

    from flask import Flask
    from flask.observability import init_observability
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry import metrics

    app = Flask(__name__)

    # Configure Prometheus reader
    reader = PrometheusMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))

    init_observability(app)

    # Expose /metrics endpoint
    @app.route('/metrics')
    def metrics_endpoint():
        from prometheus_client import generate_latest
        return generate_latest()

Testing
-------

Use the ``none`` exporter in tests to avoid network calls:

.. code-block:: python

    from flask import Flask
    from flask.observability import init_observability

    app = Flask(__name__)
    init_observability(app, exporter="none")

    def test_request():
        with app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
            # Request ID is in response headers
            assert 'X-Request-ID' in response.headers

API Reference
-------------

.. autofunction:: flask.observability.init_observability

.. autofunction:: flask.observability.get_request_id

See Also
--------

- :doc:`/benchmarks` - Performance benchmarks
- :doc:`/logging` - Standard Flask logging
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
