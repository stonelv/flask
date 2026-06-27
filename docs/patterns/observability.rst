Observability with OpenTelemetry
================================

Flask ships no telemetry of its own. End-to-end observability -- logs,
metrics, and traces -- is added by attaching OpenTelemetry to the framework's
existing extension seams, without modifying any public API.

The seams
---------

Flask exposes four clean attachment points for instrumentation:

* **The WSGI middleware seam**, :meth:`~flask.Flask.wsgi_app`. Wrapping it
  lets a middleware observe every request/response -- this is where
  ``opentelemetry-instrumentation-flask``'s ``FlaskInstrumentor`` attaches to
  emit automatic per-request SERVER spans and HTTP metrics::

      from opentelemetry.instrumentation.flask import FlaskInstrumentor
      FlaskInstrumentor().instrument_app(app)

* **Blinker signals** (:doc:`/signals`). Subscribe to
  :data:`~flask.got_request_exception` to record exceptions,
  :data:`~flask.request_started` / :data:`~flask.request_finished` for
  request lifecycle span events::

      from flask import got_request_exception

      @got_request_exception.connect_via(app)
      def on_exception(sender, exception=None, **_):
          ...

* **Request hooks**: :meth:`~flask.Flask.before_request` and
  :meth:`~flask.Flask.after_request` to emit custom metrics such as a request
  duration histogram or an error counter.

* **The app logger**, :attr:`~flask.Flask.logger`. Attach an OTel logging
  handler so log records carry the active ``trace_id`` / ``span_id``,
  correlating logs with traces.

Exporters
---------

Pick the exporter by environment: ship traces/metrics to a collector over
OTLP when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, otherwise fall back to a
console exporter so the app is observable with no infrastructure. This keeps
the same code runnable in development and production.

A working example
-----------------

A complete, runnable application -- the app, the telemetry wiring, a
``docker-compose`` stack (otel-collector, Jaeger, Prometheus, Grafana), and
tests that assert spans are emitted -- lives in the ``examples/observability``
directory. See its ``README.rst`` for install and run instructions.

Reusing the instrumentation
---------------------------

The example's ``telemetry`` module is **reusable**, not example-specific.
``setup_telemetry(app)`` wires all three signals into *any* Flask app via the
seams above, depending only on Flask's public surface. To instrument your own
application, vendor the module (or install the example project) and call it
from your application factory::

    from observability_example.telemetry import setup_telemetry

    def create_app():
        app = Flask(__name__)
        # ... routes, config ...
        setup_telemetry(app)  # traces + metrics + logs, OTLP or console
        return app

That single call:

* wraps ``app.wsgi_app`` for automatic per-request spans and HTTP metrics;
* subscribes to ``got_request_exception`` for error attribution;
* records a ``flask.request.duration`` histogram and an error counter via
  ``before_request`` / ``after_request``;
* attaches ``trace_id`` / ``span_id`` to ``app.logger`` records.

Acceptance: any Flask app that calls ``setup_telemetry(app)`` emits traces,
metrics, and structured logs (verified by the example's tests with an
in-memory span exporter, run in CI by the ``observability`` job). No
``src/flask`` file is modified and no runtime dependency is added to Flask
itself.
