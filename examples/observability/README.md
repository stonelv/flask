# Flask + OpenTelemetry (opt-in example)

End-to-end observability — **traces, metrics, and correlated logs** — for a
Flask app, without changing anything in Flask itself.

This is a standalone example with its own `pyproject.toml`. Installing Flask
**never** pulls in OpenTelemetry; you opt in by running this project. See
[`docs/adr/0004-observability-as-optional-extension.md`](../../docs/adr/0004-observability-as-optional-extension.md)
for why observability lives here instead of in core.

## What you get

| Signal | How |
|--------|-----|
| Traces | one span per request via `opentelemetry-instrumentation-flask` |
| Metrics | `http.server.*` duration/count, exported over OTLP periodically |
| Logs | standard `logging` records stamped with `trace_id`/`span_id` |

`otel_setup.py` contains the reusable wiring (`configure_telemetry(app)`); copy
it into your own project as a starting point.

## Run it

1. Start an OTLP collector locally. The quickest option is the OpenTelemetry
   Collector listening on gRPC `4317`:

   ```bash
   docker run --rm -p 4317:4317 -p 4318:4318 \
     otel/opentelemetry-collector:latest
   ```

   (Point its exporter at Jaeger/Prometheus/Loki or use the `debug` exporter to
   print to the collector's stdout.)

2. Install and run the example:

   ```bash
   cd examples/observability
   pip install -e .
   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python app.py
   ```

3. Generate some traffic:

   ```bash
   curl http://localhost:5000/
   curl http://localhost:5000/work
   ```

You should see request spans, `http.server.*` metrics, and log lines carrying
the same `trace_id` as the spans.

## Configuration

All standard OTel environment variables work, e.g.:

- `OTEL_EXPORTER_OTLP_ENDPOINT` — collector address (default `http://localhost:4317`)
- `OTEL_SERVICE_NAME` — overrides the service name
- `OTEL_RESOURCE_ATTRIBUTES` — extra resource attributes

## Production notes

- Prefer running a collector as a sidecar/agent rather than exporting directly to
  a backend from the app process.
- Batch processors are used for spans and logs to limit overhead; tune their
  queue/timeout for your throughput.
- This example uses the gRPC OTLP exporter; swap to
  `opentelemetry-exporter-otlp-proto-http` if you need HTTP/4318.
