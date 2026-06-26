"""Benchmarks for application and request context push/pop overhead."""

from __future__ import annotations

from flask import Flask


def test_app_context_push_pop(benchmark, app: Flask) -> None:
    """Cost of entering and leaving an application context."""

    def run() -> None:
        with app.app_context():
            pass

    benchmark(run)


def test_request_context_push_pop(benchmark, app: Flask) -> None:
    """Cost of a full test request context (builds a request environ)."""

    def run() -> None:
        with app.test_request_context("/user/1/post/x"):
            pass

    benchmark(run)
