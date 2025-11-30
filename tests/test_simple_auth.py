"""Unit tests for Flask Simple Auth extension"""

import pytest
from flask import Flask, jsonify
from src.flask.simple_auth import SimpleAuth, simple_auth


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SIMPLE_AUTH_API_KEYS"] = ["valid_key_1", "valid_key_2"]
    app.config["SIMPLE_AUTH_API_KEY_HEADER"] = "X-API-Key"
    return app


@pytest.fixture
def auth_app(app):
    """Create a test app with SimpleAuth initialized."""
    auth = SimpleAuth(app)

    # Register protected route
    @app.route("/protected")
    @auth.require_api_key
    def protected_route():
        return jsonify({"message": "Access granted"})

    return app


@pytest.fixture
def client(auth_app):
    """Create a test client for the auth app."""
    return auth_app.test_client()


@pytest.fixture
def custom_loader_app(app):
    """Create an app with a custom key loader."""
    auth = SimpleAuth(app)

    @auth.key_loader_callback
    def custom_loader(key):
        return key == "custom_valid_key"

    # Register protected route for custom loader
    @app.route("/custom_loader_protected")
    @auth.require_api_key
    def protected_route():
        return jsonify({"message": "Access granted"})

    return app


@pytest.fixture
def custom_loader_client(custom_loader_app):
    """Create a test client for the custom loader app."""
    return custom_loader_app.test_client()


# Test routes (now registered in fixtures)
def test_protected_route(auth_app):
    """Test that protected route is registered."""
    # Check if the route exists in the url_map
    found = False
    for rule in auth_app.url_map.iter_rules():
        if rule.rule == "/protected":
            found = True
            break
    assert found


def test_custom_loader_protected_route(custom_loader_app):
    """Test that custom loader protected route is registered."""
    # Check if the route exists in the url_map
    found = False
    for rule in custom_loader_app.url_map.iter_rules():
        if rule.rule == "/custom_loader_protected":
            found = True
            break
    assert found


# Tests for static API keys
def test_valid_api_key(client):
    """Test accessing protected route with a valid API key."""
    response = client.get("/protected", headers={"X-API-Key": "valid_key_1"})
    assert response.status_code == 200
    assert response.json == {"message": "Access granted"}


def test_invalid_api_key(client):
    """Test accessing protected route with an invalid API key."""
    response = client.get("/protected", headers={"X-API-Key": "invalid_key"})
    assert response.status_code == 403
    assert "Invalid API key" in response.data.decode()


def test_missing_api_key(client):
    """Test accessing protected route without providing an API key."""
    response = client.get("/protected")
    assert response.status_code == 401
    assert "API key is missing" in response.data.decode()


# Tests for custom key loader
def test_custom_loader_valid_key(custom_loader_client):
    """Test custom key loader with a valid key."""
    response = custom_loader_client.get(
        "/custom_loader_protected",
        headers={"X-API-Key": "custom_valid_key"}
    )
    assert response.status_code == 200
    assert response.json == {"message": "Access granted"}


def test_custom_loader_invalid_key(custom_loader_client):
    """Test custom key loader with an invalid key."""
    response = custom_loader_client.get(
        "/custom_loader_protected",
        headers={"X-API-Key": "invalid_custom_key"}
    )
    assert response.status_code == 403
    assert "Invalid API key" in response.data.decode()


# Test configuration
def test_custom_header(app):
    """Test using a custom API key header."""
    app.config["SIMPLE_AUTH_API_KEY_HEADER"] = "Custom-API-Key"
    auth = SimpleAuth(app)

    @app.route("/custom_header")
    @auth.require_api_key
    def custom_header_route():
        return jsonify({"message": "Access granted"})

    client = app.test_client()
    response = client.get("/custom_header", headers={"Custom-API-Key": "valid_key_1"})
    assert response.status_code == 200


def test_empty_api_keys(app):
    """Test with empty API keys list."""
    app.config["SIMPLE_AUTH_API_KEYS"] = []
    auth = SimpleAuth(app)

    @app.route("/empty_keys")
    @auth.require_api_key
    def empty_keys_route():
        return jsonify({"message": "Access granted"})

    client = app.test_client()
    response = client.get("/empty_keys", headers={"X-API-Key": "any_key"})
    assert response.status_code == 403


# Test init_app method
def test_init_app():
    """Test initializing the extension with init_app method."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SIMPLE_AUTH_API_KEYS"] = ["init_app_key"]

    auth = SimpleAuth()
    auth.init_app(app)

    @app.route("/init_app_protected")
    @auth.require_api_key
    def init_app_protected():
        return jsonify({"message": "Access granted"})

    client = app.test_client()
    response = client.get("/init_app_protected", headers={"X-API-Key": "init_app_key"})
    assert response.status_code == 200