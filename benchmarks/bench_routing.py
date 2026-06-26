"""Benchmark URL routing with different route table sizes."""

from __future__ import annotations

import flask


def test_routing_10_routes(benchmark, small_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing with 10 registered routes."""
    client = small_app.test_client()

    def do_request() -> None:
        client.get("/route-5")

    benchmark(do_request)


def test_routing_100_routes(benchmark, medium_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing with 100 registered routes."""
    client = medium_app.test_client()

    def do_request() -> None:
        client.get("/route-50")

    benchmark(do_request)


def test_routing_500_routes(benchmark, large_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing with 500 registered routes."""
    client = large_app.test_client()

    def do_request() -> None:
        client.get("/route-250")

    benchmark(do_request)


def test_routing_first_route(benchmark, large_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing to the first registered route (best case)."""
    client = large_app.test_client()

    def do_request() -> None:
        client.get("/route-0")

    benchmark(do_request)


def test_routing_last_route(benchmark, large_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing to the last registered route (worst case)."""
    client = large_app.test_client()

    def do_request() -> None:
        client.get("/route-499")

    benchmark(do_request)


def test_routing_miss(benchmark, large_app: flask.Flask) -> None:  # type: ignore[no-untyped-def]
    """Benchmark routing a URL that does not match (404)."""
    client = large_app.test_client()

    def do_request() -> None:
        client.get("/nonexistent-path")

    benchmark(do_request)
