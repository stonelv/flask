"""Runnable demo for flask-telemetry against a local OTLP collector.

cd extensions/flask-telemetry
pip install -e .
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python example_app.py
# then: curl http://localhost:5000/ ; curl http://localhost:5000/work
"""

from __future__ import annotations

import logging
import time

from flask_telemetry import Telemetry

from flask import Flask
from flask import jsonify

app = Flask(__name__)
Telemetry(app, service_name="flask-telemetry-example")
log = logging.getLogger(__name__)


@app.route("/")
def index() -> str:
    log.info("handling index request")  # carries the active trace_id/span_id
    return "hello, observable world"


@app.route("/work")
def work():
    time.sleep(0.05)
    log.info("did some work")
    return jsonify(status="ok", did_work=True)


if __name__ == "__main__":
    app.run(port=5000)
