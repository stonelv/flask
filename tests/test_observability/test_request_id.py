"""Test request ID generation and propagation."""

import pytest

from flask import Flask
from flask.observability import init_observability


@pytest.fixture
def instrumented_app():
    """Create a Flask app with request ID enabled."""
    app = Flask(__name__)
    init_observability(app, exporter="none", tracing=False, metrics=False, request_id=True)

    @app.route("/hello")
    def hello():
        from flask.observability._request_id import get_request_id

        return get_request_id()

    yield app


def test_request_id_generated(instrumented_app):
    """Test that a request ID is generated for each request."""
    client = instrumented_app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200

    # Check that X-Request-ID header is present in response
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) == 36  # UUID4 format


def test_request_id_propagated(instrumented_app):
    """Test that incoming X-Request-ID is propagated."""
    client = instrumented_app.test_client()

    incoming_id = "12345678-1234-5678-1234-567812345678"
    response = client.get("/hello", headers={"X-Request-ID": incoming_id})

    assert response.status_code == 200

    # Check that the same ID is returned in response
    request_id = response.headers.get("X-Request-ID")
    assert request_id == incoming_id


def test_request_id_unique(instrumented_app):
    """Test that each request gets a unique ID."""
    client = instrumented_app.test_client()

    response1 = client.get("/hello")
    response2 = client.get("/hello")

    id1 = response1.headers.get("X-Request-ID")
    id2 = response2.headers.get("X-Request-ID")

    assert id1 is not None
    assert id2 is not None
    assert id1 != id2


def test_request_id_accessible_in_handler(instrumented_app):
    """Test that request ID is accessible within request handler."""
    client = instrumented_app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200

    # The response body contains the request ID from get_request_id()
    request_id_from_handler = response.data.decode("utf-8")
    request_id_from_header = response.headers.get("X-Request-ID")

    assert request_id_from_handler == request_id_from_header


def test_request_id_disabled():
    """Test that no request ID is added when disabled."""
    app = Flask(__name__)
    init_observability(app, exporter="none", tracing=False, metrics=False, request_id=False)

    @app.route("/hello")
    def hello():
        return "Hello"

    client = app.test_client()
    response = client.get("/hello")

    assert response.status_code == 200
    assert "X-Request-ID" not in response.headers


def test_request_id_cleared_after_request(instrumented_app):
    """Test that request ID is cleared after request completes."""
    from flask.observability._request_id import get_request_id

    client = instrumented_app.test_client()

    # Outside of request context, should be None
    assert get_request_id() is None

    # During request, should be set
    response = client.get("/hello")
    assert response.status_code == 200

    # After request, should be None again
    assert get_request_id() is None
