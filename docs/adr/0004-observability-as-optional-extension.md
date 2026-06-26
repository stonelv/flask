# 0004 — Observability as an opt-in extension, never in core

- Status: Accepted
- Date: 2026-06-23

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

## Decision

Observability lives entirely outside `src/flask`, as an **opt-in example** under
`examples/observability/` with its **own `pyproject.toml`**. It composes the
existing ecosystem (`FlaskInstrumentor().instrument_app(app)`) plus a reusable
`otel_setup.py` that wires a `TracerProvider`, `MeterProvider`, and
`LoggerProvider` with OTLP export and trace/span-id log correlation.

Invariant: `grep -r opentelemetry src/` must return nothing. The core lock file
(`uv.lock`) never gains OTel dependencies.

## Consequences

- Good: Flask core stays minimal and behaviour-stable; users adopt
  observability by copying a known-good, runnable example; we ride the OTel
  project's release cadence instead of owning instrumentation.
- Cost: the example is illustrative, not a supported product surface; it is
  exercised manually / in its own isolated env, not by the core test matrix.

## Alternatives considered

- **Optional disabled-by-default hooks in core**: rejected — still grows the API
  surface and maintenance burden; conflicts with the no-API-change constraint.
- **A published `flask-otel` package in this repo**: heavier governance than an
  example warrants, and overlaps the official instrumentation package.
