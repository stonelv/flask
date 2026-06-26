# flask-telemetry

A **reusable OpenTelemetry extension for Flask** — traces, metrics, and
trace-correlated logs — packaged as a separate, installable distribution.

This is a real Flask extension following the standard pattern, **not** part of
Flask core and **not** just a demo snippet. Installing Flask never pulls in
OpenTelemetry; you opt in by depending on `flask-telemetry`. See
[`docs/adr/0004-observability-as-optional-extension.md`](../../docs/adr/0004-observability-as-optional-extension.md)
for the rationale.

## Install

```bash
pip install -e extensions/flask-telemetry          # from this repo
# or, once published: pip install flask-telemetry
```

## Use

```python
from flask import Flask
from flask_telemetry import Telemetry

app = Flask(__name__)
Telemetry(app, service_name="my-service")           # immediate init
# or deferred:
# tel = Telemetry(service_name="my-service")
# tel.init_app(app)
```

The extension registers itself at `app.extensions["telemetry"]` and exposes
`tracer_provider`, `meter_provider`, `logger_provider`, and `force_flush()`.

| Signal | How |
|--------|-----|
| Traces | one span per request via `opentelemetry-instrumentation-flask` |
| Metrics | `http.server.*` duration/count, exported over OTLP periodically |
| Logs | standard `logging` records stamped with `trace_id`/`span_id` |

## Configuration

All standard OTel environment variables apply, e.g.
`OTEL_EXPORTER_OTLP_ENDPOINT` (default `http://localhost:4317`),
`OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`. For tests, inject in-memory
exporters via the `span_exporter` / `metric_reader` / `log_exporter` arguments.

## Run the demo

```bash
docker run --rm -p 4317:4317 otel/opentelemetry-collector:latest   # a collector
cd extensions/flask-telemetry && pip install -e .
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python example_app.py
curl http://localhost:5000/ ; curl http://localhost:5000/work
```

## Test

```bash
cd extensions/flask-telemetry
pip install -e .[test] && pytest          # uses in-memory exporters, no collector
```

CI runs these tests in an isolated environment (`.github/workflows/ci-fast.yaml`),
so the extension is proven to emit spans/metrics on every change while the core
package stays OTel-free.
