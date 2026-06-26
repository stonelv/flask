"""Shared fixtures for performance benchmarks."""

from __future__ import annotations

import flask
import pytest


@pytest.fixture
def app() -> flask.Flask:
    app = flask.Flask(__name__)
    app.config["SECRET_KEY"] = "benchmark-secret"
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app: flask.Flask) -> flask.testing.FlaskClient:
    return app.test_client()


@pytest.fixture
def complex_app() -> flask.Flask:
    """A Flask app with blueprints, multiple routes, and error handlers."""
    app = flask.Flask(__name__)
    app.config["SECRET_KEY"] = "benchmark-secret"
    app.config["TESTING"] = True

    # Register multiple blueprints
    for i in range(5):
        bp = flask.Blueprint(f"bp{i}", __name__)

        @bp.route(f"/bp{i}/<int:id>")
        def bp_route(id: int) -> str:
            return f"bp{i}-{id}"

        @bp.route(f"/bp{i}/static")
        def bp_static() -> str:
            return f"bp{i}-static"

        app.register_blueprint(bp, url_prefix=f"/api/v{i}")

    # Register many routes on the app itself
    @app.route("/")
    def index() -> str:
        return "index"

    @app.route("/hello/<name>")
    def hello(name: str) -> str:
        return f"Hello {name}"

    @app.route("/json")
    def json_view() -> flask.Response:
        return flask.jsonify({"message": "hello", "items": list(range(10))})

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[flask.Response, int]:
        return flask.jsonify({"error": "not found"}), 404

    return app
