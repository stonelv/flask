"""Fixtures for the micro-benchmark suite.

Kept independent from ``tests/conftest.py`` so the benchmarks can be run in
isolation (``pytest benchmarks/``) without pulling in the full test harness.
The default ``pytest`` run does not collect this directory — ``testpaths`` in
``pyproject.toml`` is limited to ``tests``.
"""

from __future__ import annotations

import os

import pytest

from flask import Flask


@pytest.fixture
def app() -> Flask:
    app = Flask("bench_app", root_path=os.path.dirname(__file__))
    app.config.update(TESTING=True, SECRET_KEY="bench key")

    @app.route("/")
    def index() -> str:
        return "ok"

    @app.route("/user/<int:user_id>/post/<slug>")
    def post(user_id: int, slug: str) -> str:
        return f"{user_id}:{slug}"

    @app.route("/json")
    def json_route() -> dict[str, object]:
        return {"items": list(range(20)), "ok": True}

    return app


@pytest.fixture
def client(app: Flask):
    return app.test_client()
