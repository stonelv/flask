from __future__ import annotations

from io import BytesIO
from typing import Generator

from flask import Blueprint
from flask import Flask
from flask import Request
from flask import request
from flask.testing import FlaskClient


def test_max_content_length(app: Flask, client: FlaskClient) -> None:
    app.config["MAX_CONTENT_LENGTH"] = 50

    @app.post("/")
    def index():
        request.form["myfile"]
        AssertionError()

    @app.errorhandler(413)
    def catcher(error):
        return "42"

    rv = client.post("/", data={"myfile": "foo" * 50})
    assert rv.data == b"42"


def test_limit_config(app: Flask):
    app.config["MAX_CONTENT_LENGTH"] = 100
    app.config["MAX_FORM_MEMORY_SIZE"] = 50
    app.config["MAX_FORM_PARTS"] = 3
    r = Request({})

    # no app context, use Werkzeug defaults
    assert r.max_content_length is None
    assert r.max_form_memory_size == 500_000
    assert r.max_form_parts == 1_000

    # in app context, use config
    with app.app_context():
        assert r.max_content_length == 100
        assert r.max_form_memory_size == 50
        assert r.max_form_parts == 3

    # regardless of app context, use override
    r.max_content_length = 90
    r.max_form_memory_size = 30
    r.max_form_parts = 4

    assert r.max_content_length == 90
    assert r.max_form_memory_size == 30
    assert r.max_form_parts == 4

    with app.app_context():
        assert r.max_content_length == 90
        assert r.max_form_memory_size == 30
        assert r.max_form_parts == 4


def test_trusted_hosts_config(app: Flask) -> None:
    app.config["TRUSTED_HOSTS"] = ["example.test", ".other.test"]

    @app.get("/")
    def index() -> str:
        return ""

    client = app.test_client()
    r = client.get(base_url="http://example.test")
    assert r.status_code == 200
    r = client.get(base_url="http://a.other.test")
    assert r.status_code == 200
    r = client.get(base_url="http://bad.test")
    assert r.status_code == 400


def test_route_level_max_content_length_override(app: Flask, client: FlaskClient) -> None:
    """Test that max_content_length can be set per route and overrides global config."""
    app.config["MAX_CONTENT_LENGTH"] = 100

    @app.post("/global")
    def use_global():
        return str(len(request.get_data()))

    @app.post("/small", max_content_length=50)
    def use_small():
        return str(len(request.get_data()))

    @app.post("/large", max_content_length=200)
    def use_large():
        return str(len(request.get_data()))

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/global", data="x" * 80)
    assert response.status_code == 200
    response = client.post("/global", data="x" * 150)
    assert response.status_code == 413

    response = client.post("/small", data="x" * 40)
    assert response.status_code == 200
    response = client.post("/small", data="x" * 60)
    assert response.status_code == 413

    response = client.post("/large", data="x" * 150)
    assert response.status_code == 200
    response = client.post("/large", data="x" * 250)
    assert response.status_code == 413


def test_blueprint_level_max_content_length_override(app: Flask, client: FlaskClient) -> None:
    """Test that max_content_length can be set on a blueprint."""
    app.config["MAX_CONTENT_LENGTH"] = 100

    bp = Blueprint("api", __name__)
    bp.max_content_length = 150

    @bp.post("/upload")
    def bp_upload():
        return str(len(request.get_data()))

    @bp.post("/custom", max_content_length=200)
    def bp_custom():
        return str(len(request.get_data()))

    @app.post("/global")
    def app_global():
        return str(len(request.get_data()))

    app.register_blueprint(bp, url_prefix="/api")

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/global", data="x" * 80)
    assert response.status_code == 200
    response = client.post("/global", data="x" * 120)
    assert response.status_code == 413

    response = client.post("/api/upload", data="x" * 120)
    assert response.status_code == 200
    response = client.post("/api/upload", data="x" * 180)
    assert response.status_code == 413

    response = client.post("/api/custom", data="x" * 180)
    assert response.status_code == 200
    response = client.post("/api/custom", data="x" * 220)
    assert response.status_code == 413


def test_max_content_length_priority_order(app: Flask, client: FlaskClient) -> None:
    """Test that route-level > blueprint-level > global config."""
    app.config["MAX_CONTENT_LENGTH"] = 100

    bp = Blueprint("api", __name__)
    bp.max_content_length = 150

    @bp.post("/blueprint_only")
    def blueprint_only():
        return str(len(request.get_data()))

    @bp.post("/route_override", max_content_length=200)
    def route_override():
        return str(len(request.get_data()))

    @app.post("/global_only")
    def global_only():
        return str(len(request.get_data()))

    app.register_blueprint(bp, url_prefix="/api")

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/global_only", data="x" * 80)
    assert response.status_code == 200
    response = client.post("/global_only", data="x" * 120)
    assert response.status_code == 413

    response = client.post("/api/blueprint_only", data="x" * 120)
    assert response.status_code == 200
    response = client.post("/api/blueprint_only", data="x" * 160)
    assert response.status_code == 413

    response = client.post("/api/route_override", data="x" * 180)
    assert response.status_code == 200
    response = client.post("/api/route_override", data="x" * 220)
    assert response.status_code == 413


def test_streaming_request_with_max_content_length(app: Flask, client: FlaskClient) -> None:
    """Test max_content_length with streaming requests.

    This tests that max_content_length works correctly when reading
    from request.stream, which is the way to handle streaming uploads.
    """
    app.config["MAX_CONTENT_LENGTH"] = 100

    @app.post("/stream")
    def stream_upload():
        data = request.stream.read()
        return str(len(data))

    @app.post("/small_stream", max_content_length=50)
    def small_stream():
        data = request.stream.read()
        return str(len(data))

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    small_data = b"x" * 40
    medium_data = b"x" * 80
    large_data = b"x" * 120

    response = client.post("/stream", data=BytesIO(small_data))
    assert response.status_code == 200
    response = client.post("/stream", data=BytesIO(medium_data))
    assert response.status_code == 200
    response = client.post("/stream", data=BytesIO(large_data))
    assert response.status_code == 413

    response = client.post("/small_stream", data=BytesIO(small_data))
    assert response.status_code == 200
    response = client.post("/small_stream", data=BytesIO(medium_data))
    assert response.status_code == 413


def test_413_response_has_readable_error_message(app: Flask, client: FlaskClient) -> None:
    """Test that 413 responses contain readable error messages."""
    app.config["MAX_CONTENT_LENGTH"] = 50

    @app.post("/upload")
    def upload():
        return str(len(request.get_data()))

    response = client.post("/upload", data="x" * 100)
    assert response.status_code == 413
    assert b"Request Entity Too Large" in response.data
    assert b"exceeds" in response.data.lower() or b"limit" in response.data.lower()


def test_nested_blueprint_max_content_length(app: Flask, client: FlaskClient) -> None:
    """Test that max_content_length works with nested blueprints."""
    app.config["MAX_CONTENT_LENGTH"] = 100

    parent = Blueprint("parent", __name__)
    parent.max_content_length = 150

    child = Blueprint("child", __name__)
    child.max_content_length = 200

    grandchild = Blueprint("grandchild", __name__)

    @parent.post("/parent_only")
    def parent_only():
        return str(len(request.get_data()))

    @child.post("/child_only")
    def child_only():
        return str(len(request.get_data()))

    @grandchild.post("/grandchild_only")
    def grandchild_only():
        return str(len(request.get_data()))

    @grandchild.post("/custom", max_content_length=300)
    def custom_route():
        return str(len(request.get_data()))

    child.register_blueprint(grandchild, url_prefix="/gc")
    parent.register_blueprint(child, url_prefix="/c")
    app.register_blueprint(parent, url_prefix="/p")

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/p/parent_only", data="x" * 120)
    assert response.status_code == 200
    response = client.post("/p/parent_only", data="x" * 160)
    assert response.status_code == 413

    response = client.post("/p/c/child_only", data="x" * 180)
    assert response.status_code == 200
    response = client.post("/p/c/child_only", data="x" * 220)
    assert response.status_code == 413

    response = client.post("/p/c/gc/grandchild_only", data="x" * 180)
    assert response.status_code == 200
    response = client.post("/p/c/gc/grandchild_only", data="x" * 220)
    assert response.status_code == 413

    response = client.post("/p/c/gc/custom", data="x" * 250)
    assert response.status_code == 200
    response = client.post("/p/c/gc/custom", data="x" * 350)
    assert response.status_code == 413
