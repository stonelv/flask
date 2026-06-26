"""Shared fixtures for Flask benchmarks."""

from __future__ import annotations

import pytest

import flask


@pytest.fixture
def small_app() -> flask.Flask:
    """Flask app with 10 routes."""
    app = flask.Flask(__name__)

    for i in range(10):

        def view(i: int = i) -> str:
            return f"response {i}"

        app.add_url_rule(f"/route-{i}", endpoint=f"route_{i}", view_func=view)

    return app


@pytest.fixture
def medium_app() -> flask.Flask:
    """Flask app with 100 routes."""
    app = flask.Flask(__name__)

    for i in range(100):

        def view(i: int = i) -> str:
            return f"response {i}"

        app.add_url_rule(f"/route-{i}", endpoint=f"route_{i}", view_func=view)

    return app


@pytest.fixture
def large_app() -> flask.Flask:
    """Flask app with 500 routes."""
    app = flask.Flask(__name__)

    for i in range(500):

        def view(i: int = i) -> str:
            return f"response {i}"

        app.add_url_rule(f"/route-{i}", endpoint=f"route_{i}", view_func=view)

    return app
