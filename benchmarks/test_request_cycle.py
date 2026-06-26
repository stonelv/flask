"""Benchmark full request lifecycle."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_simple_request_cycle(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure a complete request-response cycle with a simple view."""

    @app.route("/simple")
    def simple() -> str:
        return "Hello, World!"

    result = benchmark(client.get, "/simple")
    assert result.status_code == 200
    assert result.data == b"Hello, World!"


def test_request_with_before_after(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure request with before_request and after_request hooks."""

    @app.before_request
    def before() -> None:
        flask.g.started = True

    @app.after_request
    def after(response: flask.Response) -> flask.Response:
        response.headers["X-Custom"] = "true"
        return response

    @app.route("/hooks")
    def hooks_view() -> str:
        assert flask.g.started
        return "with hooks"

    result = benchmark(client.get, "/hooks")
    assert result.status_code == 200


def test_request_with_teardown(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure request with teardown_request handler."""
    cleanup_log: list[str] = []

    @app.teardown_request
    def teardown(exc: BaseException | None) -> None:
        cleanup_log.append("torn_down")

    @app.route("/teardown")
    def teardown_view() -> str:
        return "teardown test"

    result = benchmark(client.get, "/teardown")
    assert result.status_code == 200


def test_request_with_multiple_hooks(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure request with multiple before/after/teardown hooks."""
    for _i in range(5):

        @app.before_request
        def before() -> None:
            pass

        @app.after_request
        def after(response: flask.Response) -> flask.Response:
            return response

        @app.teardown_request
        def teardown(exc: BaseException | None) -> None:
            pass

    @app.route("/multi-hooks")
    def multi_hooks() -> str:
        return "multi hooks"

    result = benchmark(client.get, "/multi-hooks")
    assert result.status_code == 200
