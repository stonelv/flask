"""Minimal Flask app with three representative routes."""

from __future__ import annotations

from flask import Flask, abort, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def hello() -> str:
        app.logger.info("serving hello")
        return "Hello, observability!"

    @app.get("/api")
    def api():
        return jsonify({"message": "ok", "code": 200})

    @app.get("/error")
    def error():
        # ``abort(500)`` produces a 5xx the instrumentation marks as an error
        # span; a raised non-HTTP exception would additionally fire the
        # ``got_request_exception`` signal.
        abort(500)

    return app
