"""Minimal Flask applications used by the benchmark harness.

Built once per session; imported by ``bench_core``/``bench_routing``/
``bench_templating``. Kept deliberately small so the measurement isolates
framework dispatch cost.
"""

from __future__ import annotations

import io

from flask import Flask
from flask import jsonify
from flask import render_template_string

TEMPLATE = """\
<!doctype html>
<html>
  <head><title>{{ title }}</title></head>
  <body>
    <h1>{{ title }}</h1>
    <ul>
      {% for item in items %}<li>{{ item }}</li>{% endfor %}
    </ul>
  </body>
</html>
"""


def make_app() -> tuple[Flask, Flask, Flask]:
    """Return (hello_app, api_app, template_app), each with a single route."""
    hello_app = Flask("bench_hello")

    @hello_app.get("/")
    def hello() -> str:
        return "Hello, World!"

    api_app = Flask("bench_api")

    @api_app.get("/api")
    def api():
        return jsonify({"message": "ok", "code": 200})

    template_app = Flask("bench_template")

    @template_app.get("/page")
    def page() -> str:
        return render_template_string(TEMPLATE, title="bench", items=range(10))

    return hello_app, api_app, template_app


def make_routing_app() -> Flask:
    """An app with several routes of varying complexity for routing bench."""
    app = Flask("bench_routing")

    @app.get("/")
    def index() -> str:
        return "index"

    @app.get("/users/<int:user_id>")
    def user(user_id: int) -> str:
        return f"user {user_id}"

    @app.get("/posts/<int:post_id>/comments/<int:comment_id>")
    def comment(post_id: int, comment_id: int) -> str:
        return f"comment {comment_id} on {post_id}"

    @app.get("/static/<path:filename>")
    def static_proxy(filename: str) -> str:
        return filename

    return app


# A buffer the templating benchmark can render into without going through a
# running server. Exposed so bench modules can reset it between runs if needed.
render_buffer = io.StringIO()
