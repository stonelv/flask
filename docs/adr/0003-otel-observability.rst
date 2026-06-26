ADR 0003: OpenTelemetry observability via existing seams only
=============================================================

:Date: 2026-06-26
:Status: Accepted

Context
-------

Flask ships no telemetry. End-to-end observability (logs, metrics, traces)
must be added without changing any public API behavior in ``src/flask``. The
framework already exposes several clean extension seams:

* ten Blinker signals (``request_started``, ``request_finished``,
  ``got_request_exception``, ``request_tearing_down``, the app-context
  signals, ``before_render_template`` / ``template_rendered``,
  ``message_flashed``), re-exported from ``flask``;
* the ``before_request`` / ``after_request`` / ``teardown_request`` /
  ``errorhandler`` decorators;
* the documented WSGI middleware seam, ``app.wsgi_app`` (wrap it to instrument
  every request);
* ``app.logger`` (via ``flask.logging.create_logger``).

OpenTelemetry is a non-trivial dependency set (api, sdk, OTLP exporter,
Flask instrumentation, logging instrumentation). Adding it to the main
``[dependency-groups]`` would regenerate ``uv.lock``.

Decision
--------

#. **All instrumentation lives in a new standalone example,
   ``examples/observability/``**, a flit project with
   ``Private :: Do Not Upload`` (mirroring ``examples/javascript/``). Its
   OpenTelemetry dependencies live in *that project's* ``pyproject.toml``
   and are never resolved by the main ``uv.lock``. Zero files under
   ``src/flask/`` change.

#. **Exporter selection is environment-driven.** If
   ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, traces/metrics ship to a collector
   via OTLP; otherwise a ``ConsoleSpanExporter`` / ``ConsoleMetricExporter``
   prints to stdout, so the example runs with no infrastructure.

#. **The example demonstrates every seam:** ``FlaskInstrumentor`` wraps
   ``app.wsgi_app`` for auto spans/metrics; signal subscribers add custom
   attributes and an error counter; ``before_request`` / ``after_request``
   emit per-request logs and a custom duration histogram; an OTel logging
   handler attaches ``trace_id`` / ``span_id`` to ``app.logger`` records.

#. **A ``docker-compose.yml`` provides the full e2e stack** -- otel-collector
   (receives OTLP), Jaeger (traces UI), Prometheus (metrics), Grafana
   (dashboards) -- so "from clone" a contributor can ``docker compose up``
   and see all three signals.

#. **The example ships its own tests** using ``InMemorySpanExporter`` to
   assert spans/metrics are emitted, asserting the console path does not
   crash without a collector. Like the other examples, it is not part of the
   main CI matrix.

Consequences
------------

Positive: a production-grade observability reference that uses only public
seams, runs standalone, and never risks the framework's API or its locked
dependency graph.

Negative: the example is exercised locally, not in the main CI matrix, so a
drift between it and a Flask API change is caught by the example's own tests
rather than the main suite. This matches the existing examples' policy.

Alternatives considered
-----------------------

* Bundle a thin telemetry shim into ``src/flask``: rejected -- it would
  change the public surface and add a runtime dependency to the framework
  itself, against the project's "micro" philosophy.
* Put the OTel libs in a main ``observability`` dependency group: rejected
  for ``uv.lock`` churn (see ADR 0001).
