"""A minimal Flask app wired with OpenTelemetry traces, metrics, and logs.

Run against a local OTLP collector (see README.md):

    cd examples/observability
    pip install -e .            # or: uv run --with . python app.py
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python app.py

Then: ``curl http://localhost:5000/`` and ``curl http://localhost:5000/work``.
Spans, metrics, and correlated logs appear in your collector/backend.
"""

from __future__ import annotations

import logging
import time

from otel_setup import configure_telemetry

from flask import Flask
from flask import jsonify

app = Flask(__name__)
configure_telemetry(app, service_name="flask-observability-example")

log = logging.getLogger(__name__)


@app.route("/")
def index() -> str:
    # this log line carries the active trace_id/span_id for correlation
    log.info("handling index request")
    return "hello, observable world"


@app.route("/work")
def work():
    # simulate work so the request span has visible duration
    time.sleep(0.05)
    log.info("did some work")
    return jsonify(status="ok", did_work=True)


if __name__ == "__main__":
    app.run(port=5000)
