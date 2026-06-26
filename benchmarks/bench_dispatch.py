"""Benchmark request dispatch latency."""

from __future__ import annotations

import flask


def test_dispatch_simple_get(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark a simple GET request dispatch."""
    app = flask.Flask(__name__)

    @app.route("/")
    def index() -> str:
        return "ok"

    client = app.test_client()

    def do_request() -> None:
        client.get("/")

    benchmark(do_request)


def test_dispatch_with_path_param(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark GET request with a path parameter."""
    app = flask.Flask(__name__)

    @app.route("/user/<int:user_id>")
    def user(user_id: int) -> str:
        return f"user {user_id}"

    client = app.test_client()

    def do_request() -> None:
        client.get("/user/42")

    benchmark(do_request)


def test_dispatch_json_response(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark request returning JSON via jsonify."""
    app = flask.Flask(__name__)

    @app.route("/data")
    def data() -> flask.Response:
        return flask.jsonify({"key": "value", "items": list(range(10))})

    client = app.test_client()

    def do_request() -> None:
        client.get("/data")

    benchmark(do_request)


def test_dispatch_post_with_body(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark POST request with JSON body."""
    app = flask.Flask(__name__)

    @app.route("/submit", methods=["POST"])
    def submit() -> tuple[str, int]:
        flask.request.get_json(silent=True)
        return "accepted", 201

    client = app.test_client()

    def do_request() -> None:
        client.post("/submit", json={"name": "test", "value": 42})

    benchmark(do_request)


def test_dispatch_error_handler(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark request that hits a custom error handler."""
    app = flask.Flask(__name__)

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[str, int]:
        return "not found", 404

    client = app.test_client()

    def do_request() -> None:
        client.get("/nonexistent")

    benchmark(do_request)
