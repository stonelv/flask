"""Unit tests for flask_simple_auth extension

This module contains tests for the API key authentication functionality
provided by the flask_simple_auth extension.
"""

import pytest
from flask import Flask
from flask_simple_auth import SimpleAuth, require_api_key, init_app


@pytest.fixture
def app():
    """Create a Flask application fixture for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client fixture for testing"""
    return app.test_client()


def test_extension_initialization(app):
    """Test that the extension can be initialized correctly"""
    auth = SimpleAuth(app)
    assert 'simple_auth' in app.extensions
    assert app.extensions['simple_auth'] == auth


def test_extension_init_app(app):
    """Test that the extension can be initialized with init_app"""
    auth = SimpleAuth()
    auth.init_app(app)
    assert 'simple_auth' in app.extensions
    assert app.extensions['simple_auth'] == auth


def test_default_settings(app):
    """Test that default settings are applied correctly"""
    SimpleAuth(app)
    assert app.config['SIMPLE_AUTH_API_KEY_HEADER'] == 'X-API-KEY'
    assert app.config['SIMPLE_AUTH_API_KEYS'] is None


def test_route_protection_with_static_keys(app, client):
    """Test route protection with static API keys"""
    app.config['SIMPLE_AUTH_API_KEYS'] = ['valid-key-123']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key
    def protected_route():
        return {'message': 'Success'}

    # Test without API key
    response = client.get('/protected')
    assert response.status_code == 401
    assert response.get_json()['error'] == 'API key is missing'

    # Test with invalid API key
    response = client.get('/protected', headers={'X-API-KEY': 'invalid-key'})
    assert response.status_code == 403
    assert response.get_json()['error'] == 'Invalid API key'

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-KEY': 'valid-key-123'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_route_protection_with_custom_header(app, client):
    """Test route protection with custom API key header"""
    app.config['SIMPLE_AUTH_API_KEY_HEADER'] = 'Authorization'
    app.config['SIMPLE_AUTH_API_KEYS'] = ['valid-key-456']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key
    def protected_route():
        return {'message': 'Success'}

    # Test with custom header
    response = client.get('/protected', headers={'Authorization': 'valid-key-456'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_route_protection_with_key_loader(app, client):
    """Test route protection with dynamic key loader function"""
    SimpleAuth(app)

    # Create a custom key loader
    def custom_key_loader(api_key):
        return api_key == 'valid-dynamic-key'

    app.key_loader = custom_key_loader

    @app.route('/protected')
    @require_api_key
    def protected_route():
        return {'message': 'Success'}

    # Test with invalid API key
    response = client.get('/protected', headers={'X-API-KEY': 'invalid-key'})
    assert response.status_code == 403
    assert response.get_json()['error'] == 'Invalid API key'

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-KEY': 'valid-dynamic-key'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_decorator_without_initialization(app, client):
    """Test that the decorator works without initializing the extension first"""
    # Don't initialize the extension, just use the decorator
    @app.route('/protected')
    @require_api_key
    def protected_route():
        return {'message': 'Success'}

    # Now initialize the extension
    app.config['SIMPLE_AUTH_API_KEYS'] = ['valid-key-789']
    init_app(app)

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-KEY': 'valid-key-789'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_multiple_keys(app, client):
    """Test route protection with multiple valid API keys"""
    app.config['SIMPLE_AUTH_API_KEYS'] = ['key1', 'key2', 'key3']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key
    def protected_route():
        return {'message': 'Success'}

    # Test with all valid keys
    for key in ['key1', 'key2', 'key3']:
        response = client.get('/protected', headers={'X-API-KEY': key})
        assert response.status_code == 200

    # Test with invalid key
    response = client.get('/protected', headers={'X-API-KEY': 'invalid-key'})
    assert response.status_code == 403
