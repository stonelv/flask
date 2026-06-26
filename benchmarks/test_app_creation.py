"""Benchmark Flask application creation and configuration."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_app_creation_minimal(benchmark: BenchmarkFixture) -> None:
    """Measure creating a minimal Flask app."""

    def create() -> flask.Flask:
        return flask.Flask(__name__)

    benchmark(create)


def test_app_creation_with_config(benchmark: BenchmarkFixture) -> None:
    """Measure creating an app with typical configuration."""

    def create() -> flask.Flask:
        app = flask.Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SECURE"] = True
        return app

    benchmark(create)


def test_app_creation_with_blueprint(benchmark: BenchmarkFixture) -> None:
    """Measure creating an app with blueprint registration."""

    def create() -> flask.Flask:
        app = flask.Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        bp = flask.Blueprint("api", __name__)

        @bp.route("/items/<int:id>")
        def get_item(id: int) -> str:
            return str(id)

        @bp.route("/items", methods=["POST"])
        def create_item() -> str:
            return "created"

        app.register_blueprint(bp, url_prefix="/api")
        return app

    benchmark(create)
