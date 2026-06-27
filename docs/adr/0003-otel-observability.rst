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

#. **The instrumentation is a reusable module, not just an example.**
   ``examples/observability/observability_example/telemetry.py`` exposes
   ``setup_telemetry(app, *, span_exporter=None)`` -- a single entry point
   that wires traces/metrics/logs into **any** Flask app via the seams below.
   Reuse it by vendoring that one module (or installing the example project)
   and calling ``setup_telemetry(app)`` in your factory. It depends only on
   Flask's public surface, so it tracks Flask API changes without coupling to
   the framework's internals.

#. **The example project demonstrates the reusable module end-to-end.**
   ``examples/observability/`` is a flit project with
   ``Private :: Do Not Upload`` (mirroring ``examples/javascript/``). Its
   OpenTelemetry dependencies live in *that project's* ``pyproject.toml``
   and are never resolved by the main ``uv.lock``. Zero files under
   ``src/flask/`` change.

#. **Exporter selection is environment-driven.** If
   ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, traces/metrics ship to a collector
   via OTLP; otherwise a ``ConsoleSpanExporter`` / ``ConsoleMetricExporter``
   prints to stdout, so the example runs with no infrastructure.

#. **The module demonstrates every seam:** ``FlaskInstrumentor`` wraps
   ``app.wsgi_app`` for auto spans/metrics; signal subscribers add custom
   attributes and an error counter; ``before_request`` / ``after_request``
   emit per-request logs and a custom duration histogram; an OTel logging
   handler attaches ``trace_id`` / ``span_id`` to ``app.logger`` records.

#. **A ``docker-compose.yml`` provides the full e2e stack** -- otel-collector
   (receives OTLP), Jaeger (traces UI), Prometheus (metrics), Grafana
   (dashboards) -- so "from clone" a contributor can ``docker compose up``
   and see all three signals.

#. **The example is exercised in CI.** A dedicated ``observability`` job in
   ``tests.yaml`` (gated by ``smoke``) installs the local Flask (editable)
   plus the example's OTel deps and runs the example's pytest, which uses
   ``InMemorySpanExporter`` to assert spans/metrics are emitted and that the
   console path does not crash without a collector.

Consequences
------------

Positive: a production-grade, **reusable** instrumentation module (one call,
``setup_telemetry(app)``) that uses only public seams, runs standalone, and
never risks the framework's API or its locked dependency graph; the example
both documents and tests it, and CI keeps it from drifting.

Negative: the reusable module is not published as its own package (it lives
in the example tree); consumers vendor the file or install the example
project. This is intentional -- publishing a separate instrumentation
package is out of scope for this platform.

Alternatives considered
-----------------------

* Bundle a thin telemetry shim into ``src/flask``: rejected -- it would
  change the public surface and add a runtime dependency to the framework
  itself, against the project's "micro" philosophy.
* Put the OTel libs in a main ``observability`` dependency group: rejected
  for ``uv.lock`` churn (see ADR 0001).
