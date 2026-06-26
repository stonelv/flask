"""Benchmark template rendering performance."""

from __future__ import annotations

import flask


def _make_template_app() -> flask.Flask:
    """Create an app that renders an inline template."""
    app = flask.Flask(__name__)

    @app.route("/simple")
    def simple() -> str:
        return flask.render_template_string("<h1>Hello {{ name }}</h1>", name="World")

    @app.route("/loop")
    def loop() -> str:
        items = [
            {"id": i, "name": f"Item {i}", "active": i % 2 == 0}
            for i in range(50)
        ]
        return flask.render_template_string(
            "<ul>{% for item in items %}"
            "<li class='{{ \"active\" if item.active }}'>{{ item.name }}</li>"
            "{% endfor %}</ul>",
            items=items,
        )

    @app.route("/nested")
    def nested() -> str:
        data = {
            "title": "Report",
            "sections": [
                {
                    "heading": f"Section {i}",
                    "paragraphs": [f"Paragraph {j}" for j in range(5)],
                }
                for i in range(10)
            ],
        }
        return flask.render_template_string(
            "<h1>{{ data.title }}</h1>"
            "{% for section in data.sections %}"
            "<h2>{{ section.heading }}</h2>"
            "{% for p in section.paragraphs %}<p>{{ p }}</p>{% endfor %}"
            "{% endfor %}",
            data=data,
        )

    return app


def test_template_simple(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark simple template with one variable substitution."""
    app = _make_template_app()
    client = app.test_client()

    def do_request() -> None:
        client.get("/simple")

    benchmark(do_request)


def test_template_loop(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark template with a loop over 50 items."""
    app = _make_template_app()
    client = app.test_client()

    def do_request() -> None:
        client.get("/loop")

    benchmark(do_request)


def test_template_nested(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Benchmark template with nested loops (10 sections x 5 paragraphs)."""
    app = _make_template_app()
    client = app.test_client()

    def do_request() -> None:
        client.get("/nested")

    benchmark(do_request)
