"""Flask app instrumented with OpenTelemetry via existing seams only.

Nothing in ``src/flask`` is modified. The instrumentation attaches through:

* ``app.wsgi_app`` -- ``FlaskInstrumentor`` wraps it for automatic
  per-request SERVER spans and HTTP metrics.
* the Blinker ``got_request_exception`` signal -- custom span + error
  attribution for unhandled exceptions.
* ``@app.before_request`` / ``@app.after_request`` -- a custom
  ``flask.request.duration`` histogram and an error counter.
* ``app.logger`` -- an OTel logging handler so log records carry
  ``trace_id`` / ``span_id``.

See ``telemetry.setup_telemetry`` for the exporter selection (OTLP when a
collector is reachable via ``OTEL_EXPORTER_OTLP_ENDPOINT``; a console
exporter otherwise, so the example runs with no infrastructure).
"""

from __future__ import annotations

from observability_example.app import create_app
from observability_example.telemetry import setup_telemetry

__all__ = ["create_app", "setup_telemetry"]
