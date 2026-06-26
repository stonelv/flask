"""Benchmarks for JSON encoding/decoding and url_for."""

from __future__ import annotations

from flask import Flask
from flask import url_for


def test_json_response(benchmark, client) -> None:
    """Dispatch a route that serialises a dict to a JSON response."""

    def run() -> int:
        return client.get("/json").status_code

    assert benchmark(run) == 200


def test_json_dumps_loads(benchmark, app: Flask) -> None:
    """Round-trip a payload through Flask's JSON provider."""
    payload = {"items": list(range(100)), "nested": {"a": 1, "b": [1, 2, 3]}}

    def run() -> object:
        text = app.json.dumps(payload)
        return app.json.loads(text)

    assert benchmark(run) == payload


def test_url_for(benchmark, app: Flask) -> None:
    """Building a URL for a dynamic endpoint within a request context."""

    def run() -> str:
        with app.test_request_context():
            return url_for("post", user_id=42, slug="hello")

    assert benchmark(run).endswith("/user/42/post/hello")
