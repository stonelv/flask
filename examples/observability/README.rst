Observability Example
=====================

A small Flask app instrumented end-to-end with OpenTelemetry (logs, metrics,
traces) using **only Flask's existing extension seams** -- no part of
``src/flask`` is modified. The instrumentation attaches through:

* ``app.wsgi_app`` -- ``FlaskInstrumentor`` wraps it for automatic
  per-request SERVER spans and HTTP metrics;
* the Blinker ``got_request_exception`` signal -- custom span + error
  attribution for unhandled exceptions;
* ``@app.before_request`` / ``@app.after_request`` -- a custom
  ``flask.request.duration`` histogram and an error counter;
* ``app.logger`` -- an OTel logging handler so log records carry
  ``trace_id`` / ``span_id``.


Install
-------

.. code-block:: bash

    cd examples/observability
    python -m venv .venv
    . .venv/bin/activate
    pip install -e ".[observability,test]"


Run without infrastructure (console exporter)
---------------------------------------------

With no ``OTEL_EXPORTER_OTLP_ENDPOINT`` set, traces and metrics print to
stdout, so you can see all three signals with no collector running:

.. code-block:: bash

    flask --app observability_example run
    # in another shell:
    curl http://127.0.0.1:5000/
    curl http://127.0.0.1:5000/api
    curl http://127.0.0.1:5000/error


Run the full stack (OTLP -> collector -> Jaeger/Prometheus/Grafana)
-------------------------------------------------------------------

.. code-block:: bash

    docker compose up            # collector, Jaeger, Prometheus, Grafana
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
        flask --app observability_example run

Then open:

* `Jaeger <http://localhost:16686>`_ -- traces;
* `Prometheus <http://localhost:9090>`_ -- metrics (try
  ``flask_request_duration``);
* `Grafana <http://localhost:3000>`_ (admin/admin) -- both datasources are
  provisioned automatically.


Test
----

.. code-block:: bash

    pytest

The tests use an ``InMemorySpanExporter`` to assert that requests produce
spans, that failing requests are marked, and that the console-exporter path
does not crash without a collector.
