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
    assert app.config['SIMPLE_AUTH_HEADER_NAME'] == 'X-API-Key'
    assert app.config['SIMPLE_AUTH_KEYS'] is None
    assert app.config['SIMPLE_AUTH_KEY_LOADER'] is None
    assert app.config['SIMPLE_AUTH_UNAUTHORIZED_HANDLER'] is None


def test_route_protection_with_static_keys(app, client):
    """Test route protection with static API keys"""
    app.config['SIMPLE_AUTH_KEYS'] = ['valid-key-123']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test without API key
    response = client.get('/protected')
    assert response.status_code == 401
    assert response.get_json()['error'] == 'unauthorized'

    # Test with invalid API key
    response = client.get('/protected', headers={'X-API-Key': 'invalid-key'})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'unauthorized'

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-Key': 'valid-key-123'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_route_protection_with_custom_header(app, client):
    """Test route protection with custom API key header"""
    app.config['SIMPLE_AUTH_HEADER_NAME'] = 'Authorization'
    app.config['SIMPLE_AUTH_KEYS'] = ['valid-key-456']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test with custom header
    response = client.get('/protected', headers={'Authorization': 'valid-key-456'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_route_protection_with_key_loader(app, client):
    """Test route protection with dynamic key loader function"""
    # Create a custom key loader
    def custom_key_loader(api_key):
        return api_key == 'valid-dynamic-key'

    app.config['SIMPLE_AUTH_KEY_LOADER'] = custom_key_loader
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test with invalid API key
    response = client.get('/protected', headers={'X-API-Key': 'invalid-key'})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'unauthorized'

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-Key': 'valid-dynamic-key'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_decorator_without_initialization(app, client):
    """Test that the decorator works without initializing the extension first"""
    # Don't initialize the extension, just use the decorator
    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Now initialize the extension
    app.config['SIMPLE_AUTH_KEYS'] = ['valid-key-789']
    init_app(app)

    # Test with valid API key
    response = client.get('/protected', headers={'X-API-Key': 'valid-key-789'})
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'


def test_multiple_api_keys(app, client):
    """Test that multiple API keys can be used"""
    app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test with each valid key
    for key in ['key1', 'key2', 'key3']:
        response = client.get('/protected', headers={'X-API-Key': key})
        assert response.status_code == 200
        assert response.get_json()['message'] == 'Success'

    # Test with invalid key
    response = client.get('/protected', headers={'X-API-Key': 'invalid'})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'unauthorized'


def test_allow_none(app, client):
    """Test that allow_none=True allows access without API key"""
    app.config['SIMPLE_AUTH_KEYS'] = ['valid-key']
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key(allow_none=True)
    def protected_route():
        return {'message': 'Success'}

    # Test without API key
    response = client.get('/protected')
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Success'



def test_key_loader_metadata(app, client):
    """Test that key loader can return metadata"""
    def custom_key_loader(api_key):
        if api_key == 'valid-key':
            return {'user_id': 123, 'role': 'admin'}
        return False

    app.config['SIMPLE_AUTH_KEY_LOADER'] = custom_key_loader
    SimpleAuth(app)

    @app.route('/metadata')
    @require_api_key()
    def metadata_route():
        from flask import g
        return {
            'user_id': g.current_api_key_meta['user_id'],
            'role': g.current_api_key_meta['role']
        }

    # Test with valid key
    response = client.get('/metadata', headers={'X-API-Key': 'valid-key'})
    assert response.status_code == 200
    assert response.get_json()['user_id'] == 123
    assert response.get_json()['role'] == 'admin'



def test_key_loader_exception(app, client):
    """Test that key loader raising exception results in 401"""
    def custom_key_loader(api_key):
        raise ValueError('Invalid key format')

    app.config['SIMPLE_AUTH_KEY_LOADER'] = custom_key_loader
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test with any key
    response = client.get('/protected', headers={'X-API-Key': 'any-key'})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'unauthorized'



def test_g_attributes(app, client):
    """Test that g.current_api_key and g.current_api_key_meta are set"""
    def custom_key_loader(api_key):
        if api_key == 'valid-key':
            return {'user_id': 123}
        return False

    app.config['SIMPLE_AUTH_KEY_LOADER'] = custom_key_loader
    SimpleAuth(app)

    @app.route('/g-attributes')
    @require_api_key()
    def g_attributes_route():
        from flask import g
        return {
            'current_api_key': g.current_api_key,
            'current_api_key_meta': g.current_api_key_meta
        }

    # Test with valid key
    response = client.get('/g-attributes', headers={'X-API-Key': 'valid-key'})
    assert response.status_code == 200
    assert response.get_json()['current_api_key'] == 'valid-key'
    assert response.get_json()['current_api_key_meta'] == {'user_id': 123}



def test_custom_unauthorized_handler(app, client):
    """Test that custom unauthorized handler can be used"""
    def custom_unauthorized_handler(error):
        return {'error': 'custom_error', 'message': 'Custom unauthorized message'}, 401

    app.config['SIMPLE_AUTH_KEYS'] = ['valid-key']
    app.config['SIMPLE_AUTH_UNAUTHORIZED_HANDLER'] = custom_unauthorized_handler
    SimpleAuth(app)

    @app.route('/protected')
    @require_api_key()
    def protected_route():
        return {'message': 'Success'}

    # Test with invalid key
    response = client.get('/protected', headers={'X-API-Key': 'invalid-key'})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'custom_error'
    assert response.get_json()['message'] == 'Custom unauthorized message'
