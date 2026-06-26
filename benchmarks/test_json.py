"""Benchmark JSON serialization and jsonify."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_jsonify_simple_dict(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure jsonify with a simple dictionary."""

    @app.route("/json-simple")
    def json_simple() -> flask.Response:
        return flask.jsonify({"key": "value", "number": 42, "flag": True})

    result = benchmark(client.get, "/json-simple")
    assert result.status_code == 200


def test_jsonify_nested_dict(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure jsonify with nested data structures."""
    data = {
        "users": [
            {"id": i, "name": f"user_{i}", "email": f"user{i}@example.com", "active": i % 2 == 0}
            for i in range(20)
        ],
        "total": 20,
        "page": 1,
    }

    @app.route("/json-nested")
    def json_nested() -> flask.Response:
        return flask.jsonify(data)

    result = benchmark(client.get, "/json-nested")
    assert result.status_code == 200


def test_jsonify_list(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure jsonify with a list of items."""
    items = [{"id": i, "value": f"item_{i}"} for i in range(50)]

    @app.route("/json-list")
    def json_list() -> flask.Response:
        return flask.jsonify(items)

    result = benchmark(client.get, "/json-list")
    assert result.status_code == 200


def test_json_encode_decode(benchmark: BenchmarkFixture, app: flask.Flask) -> None:
    """Measure raw JSON encode/decode via Flask's json module."""
    data = {"key": "value", "items": list(range(100)), "nested": {"a": 1, "b": 2}}

    def encode_decode() -> dict[str, object]:
        with app.app_context():
            encoded = flask.json.dumps(data)
            return flask.json.loads(encoded)

    result = benchmark(encode_decode)
    assert result["key"] == "value"
