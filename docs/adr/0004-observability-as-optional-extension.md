# 0004 — Observability as a reusable extension, never in core

- Status: Accepted
- Date: 2026-06-23
- Updated: 2026-06-26 — promoted from an illustrative example to a packaged,
  installable, tested extension (`extensions/flask-telemetry`).

## Context

Production users want end-to-end observability — traces, metrics, correlated
logs — for Flask apps. The temptation is to add OpenTelemetry hooks into Flask
core. That would be a mistake for a *framework*:

- It expands the public API surface and changes runtime behaviour, even when
  "disabled by default" — violating our hard constraint of zero public-API
  behaviour change.
- It pulls a large, fast-moving dependency tree (`opentelemetry-sdk`,
  exporters) into a library that prides itself on a tiny install.
- It duplicates the mature, separately-versioned
  `opentelemetry-instrumentation-flask` package that the OTel project already
  maintains against Flask's stable WSGI/ext points.

But shipping only a copy-paste *example* is also unsatisfying: it is not
installable, not versioned, and not exercised as a unit, so users cannot depend
on it and it can rot.

## Decision

Observability is a **reusable, installable Flask extension** living entirely
outside `src/flask`, at `extensions/flask-telemetry/` with its own
`pyproject.toml`, version, and test suite. It follows the standard Flask
extension protocol — `Telemetry(app)` / `Telemetry().init_app(app)`, registered
at `app.extensions["telemetry"]` — and composes the existing ecosystem
(`FlaskInstrumentor().instrument_app(app)`) to wire a `TracerProvider`,
`MeterProvider`, and `LoggerProvider` with OTLP export and trace/span-id log
correlation. Exporters are injectable, so it is unit-tested with in-memory
exporters and verified in CI (`flask-telemetry-extension` job).

Invariants:

- `grep -r opentelemetry src/` returns nothing.
- The core lock file (`uv.lock`) never gains OTel dependencies.
- The extension is installed and tested only in its own isolated environment.

## Consequences

- Good: Flask core stays minimal and behaviour-stable; users `pip install` a
  real, versioned extension and call a documented API rather than copying a
  snippet; it is tested on every change; we ride the OTel project's release
  cadence for the underlying instrumentation.
- Cost: one more package to maintain in the repo (separate version + deps); it
  is not part of the core test matrix (runs in its own job/env).

## Alternatives considered

- **Optional disabled-by-default hooks in core**: rejected — still grows the API
  surface and maintenance burden; conflicts with the no-API-change constraint.
- **Only an example under `examples/`**: rejected this round — not installable,
  not versioned, not unit-tested; users cannot depend on it.
- **In-core instrumentation duplicating `opentelemetry-instrumentation-flask`**:
  rejected — redundant with the official package and couples core to OTel.
