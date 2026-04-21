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
    """Test that max_content_length works with nested blueprints.

    Priority for nested blueprints:
    - Innermost (most specific) blueprint > outer blueprint > global config
    - If innermost blueprint doesn't have max_content_length set, use the
      closest ancestor that has it set.
    - Route-level max_content_length overrides all blueprint and global settings.

    This test ensures that if the implementation incorrectly uses reversed()
    (which would prioritize outer blueprints), the test will fail.
    """
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


def test_nested_blueprint_innermost_priority(app: Flask, client: FlaskClient) -> None:
    """Test that innermost blueprint has higher priority than outer ones.

    Critical test: This ensures that the innermost (most specific) blueprint's
    max_content_length takes precedence over outer blueprints.

    If the implementation incorrectly iterates from outer to inner (e.g., using
    reversed()), this test will fail because:
    - parent.max_content_length = 150 would be used instead of child.max_content_length = 200
    - grandchild.max_content_length = 250 would be used instead of child.max_content_length = 200

    Expected behavior:
    - child_only route uses child's 200 (not parent's 150)
    - grandchild_only route uses grandchild's 250 (not child's 200 or parent's 150)
    """
    app.config["MAX_CONTENT_LENGTH"] = 100

    parent = Blueprint("parent", __name__)
    parent.max_content_length = 150

    child = Blueprint("child", __name__)
    child.max_content_length = 200

    grandchild = Blueprint("grandchild", __name__)
    grandchild.max_content_length = 250

    @child.post("/child_only")
    def child_only():
        return str(len(request.get_data()))

    @grandchild.post("/grandchild_only")
    def grandchild_only():
        return str(len(request.get_data()))

    child.register_blueprint(grandchild, url_prefix="/gc")
    parent.register_blueprint(child, url_prefix="/c")
    app.register_blueprint(parent, url_prefix="/p")

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/p/c/child_only", data="x" * 180)
    assert response.status_code == 200, (
        "child_only should use child's 200 limit, not parent's 150. "
        "If this fails, the implementation may be iterating blueprints in wrong order."
    )

    response = client.post("/p/c/child_only", data="x" * 220)
    assert response.status_code == 413, (
        "220 bytes should exceed child's 200 limit."
    )

    response = client.post("/p/c/gc/grandchild_only", data="x" * 240)
    assert response.status_code == 200, (
        "grandchild_only should use grandchild's 250 limit, not child's 200. "
        "If this fails, the implementation may be iterating blueprints in wrong order."
    )

    response = client.post("/p/c/gc/grandchild_only", data="x" * 260)
    assert response.status_code == 413, (
        "260 bytes should exceed grandchild's 250 limit."
    )


def test_nested_blueprint_skip_none_values(app: Flask, client: FlaskClient) -> None:
    """Test that blueprints with max_content_length=None are skipped.

    When an inner blueprint doesn't have max_content_length set (None),
    the implementation should look for the closest ancestor that has it set.

    Scenarios tested:
    1. grandchild=None, child=200, parent=150 -> should use child's 200
    2. grandchild=None, child=None, parent=150 -> should use parent's 150
    """
    app.config["MAX_CONTENT_LENGTH"] = 100

    parent = Blueprint("parent", __name__)
    parent.max_content_length = 150

    child = Blueprint("child", __name__)
    child.max_content_length = 200

    grandchild_no_setting = Blueprint("gc_no_setting", __name__)

    parent2 = Blueprint("parent2", __name__)
    parent2.max_content_length = 150

    child2 = Blueprint("child2", __name__)

    grandchild2 = Blueprint("grandchild2", __name__)

    @grandchild_no_setting.post("/route")
    def gc_route():
        return str(len(request.get_data()))

    @grandchild2.post("/route")
    def gc2_route():
        return str(len(request.get_data()))

    child.register_blueprint(grandchild_no_setting, url_prefix="/gc")
    parent.register_blueprint(child, url_prefix="/c")
    app.register_blueprint(parent, url_prefix="/p")

    child2.register_blueprint(grandchild2, url_prefix="/gc")
    parent2.register_blueprint(child2, url_prefix="/c")
    app.register_blueprint(parent2, url_prefix="/p2")

    @app.errorhandler(413)
    def handle_too_large(e):
        return "Too large", 413

    response = client.post("/p/c/gc/route", data="x" * 190)
    assert response.status_code == 200, (
        "Should use child's 200 limit when grandchild has no setting."
    )

    response = client.post("/p/c/gc/route", data="x" * 210)
    assert response.status_code == 413, (
        "210 bytes should exceed child's 200 limit."
    )

    response = client.post("/p2/c/gc/route", data="x" * 140)
    assert response.status_code == 200, (
        "Should use parent's 150 limit when child and grandchild have no setting."
    )

    response = client.post("/p2/c/gc/route", data="x" * 160)
    assert response.status_code == 413, (
        "160 bytes should exceed parent's 150 limit."
    )
