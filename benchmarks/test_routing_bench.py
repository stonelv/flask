"""Benchmarks for URL routing and full request dispatch — the hottest path."""

from __future__ import annotations

from flask import Flask


def test_dispatch_static_route(benchmark, client) -> None:
    """End-to-end dispatch of a simple static route through the test client."""

    def run() -> int:
        return client.get("/").status_code

    assert benchmark(run) == 200


def test_dispatch_dynamic_route(benchmark, client) -> None:
    """Dispatch of a route with typed converters (int + string)."""

    def run() -> int:
        return client.get("/user/42/post/hello-world").status_code

    assert benchmark(run) == 200


def test_url_map_match(benchmark, app: Flask) -> None:
    """Just the URL map matching, isolated from request/response handling."""
    adapter = app.url_map.bind("localhost")

    def run() -> tuple[str, dict[str, object]]:
        return adapter.match("/user/42/post/hello-world")

    endpoint, _ = benchmark(run)
    assert endpoint == "post"
