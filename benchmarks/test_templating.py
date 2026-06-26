"""Benchmark Jinja2 template rendering."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_render_template_string_simple(
    benchmark: BenchmarkFixture, app: flask.Flask
) -> None:
    """Measure rendering a simple template string."""

    def render() -> str:
        with app.app_context():
            return flask.render_template_string("Hello, {{ name }}!", name="World")

    result = benchmark(render)
    assert result == "Hello, World!"


def test_render_template_string_with_loop(
    benchmark: BenchmarkFixture, app: flask.Flask
) -> None:
    """Measure rendering a template string with a loop."""
    items = list(range(100))

    def render() -> str:
        with app.app_context():
            return flask.render_template_string(
                "{% for item in items %}{{ item }}\n{% endfor %}",
                items=items,
            )

    benchmark(render)


def test_render_template_string_with_conditionals(
    benchmark: BenchmarkFixture, app: flask.Flask
) -> None:
    """Measure rendering a template with conditionals."""

    def render() -> str:
        with app.app_context():
            return flask.render_template_string(
                "{% if show %}{{ title }}{% else %}hidden{% endif %}",
                show=True,
                title="Benchmark",
            )

    result = benchmark(render)
    assert result == "Benchmark"


def test_render_template_string_with_filters(
    benchmark: BenchmarkFixture, app: flask.Flask
) -> None:
    """Measure rendering with Jinja2 filters."""

    def render() -> str:
        with app.app_context():
            return flask.render_template_string(
                "{{ name | upper | trim }} - {{ count | string }}",
                name="  hello  ",
                count=42,
            )

    result = benchmark(render)
    assert result == "HELLO - 42"
