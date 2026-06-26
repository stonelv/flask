"""Benchmark URL routing and dispatch."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_simple_route_match(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure routing a simple static route."""

    @app.route("/hello")
    def hello() -> str:
        return "hello"

    result = benchmark(client.get, "/hello")
    assert result.status_code == 200


def test_parameterized_route_match(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure routing a route with parameters."""

    @app.route("/users/<int:user_id>/posts/<string:post_id>")
    def get_post(user_id: int, post_id: str) -> str:
        return f"{user_id}-{post_id}"

    result = benchmark(client.get, "/users/42/posts/abc123")
    assert result.status_code == 200


def test_complex_routing(benchmark: BenchmarkFixture, complex_app: flask.Flask) -> None:
    """Measure routing in an app with many blueprints and routes."""
    client = complex_app.test_client()
    result = benchmark(client.get, "/api/v3/bp3/42")
    assert result.status_code == 200


def test_route_404(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure handling a non-existent route."""

    @app.route("/exists")
    def exists() -> str:
        return "yes"

    result = benchmark(client.get, "/does-not-exist")
    assert result.status_code == 404
