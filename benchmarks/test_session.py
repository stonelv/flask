"""Benchmark session signing, serialization, and deserialization."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_session_save(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure session save (sign + serialize cookie)."""

    @app.route("/session-set")
    def session_set() -> str:
        flask.session["user_id"] = 42
        flask.session["username"] = "testuser"
        flask.session["preferences"] = {"theme": "dark", "lang": "en"}
        return "ok"

    result = benchmark(client.get, "/session-set")
    assert result.status_code == 200


def test_session_load(benchmark: BenchmarkFixture, app: flask.Flask) -> None:
    """Measure session load (verify signature + deserialize cookie)."""

    @app.route("/session-set")
    def session_set() -> str:
        flask.session["user_id"] = 42
        flask.session["items"] = list(range(20))
        return "ok"

    @app.route("/session-get")
    def session_get() -> str:
        user_id = flask.session.get("user_id")
        return str(user_id)

    with app.test_client() as c:
        c.get("/session-set")

        result = benchmark(c.get, "/session-get")
        assert result.data == b"42"


def test_session_modify(benchmark: BenchmarkFixture, app: flask.Flask) -> None:
    """Measure modifying session data across requests."""

    @app.route("/session-init")
    def session_init() -> str:
        flask.session["counter"] = 0
        return "ok"

    @app.route("/session-incr")
    def session_incr() -> str:
        flask.session["counter"] = flask.session.get("counter", 0) + 1
        return str(flask.session["counter"])

    with app.test_client() as c:
        c.get("/session-init")
        result = benchmark(c.get, "/session-incr")
        assert result.status_code == 200
