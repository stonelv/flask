import pytest
from flask import Flask, jsonify
from flask_simple_auth import simple_auth, FlaskSimpleAuth


def create_app_with_static_keys():
    """创建配置了静态 API Key 的 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SIMPLE_AUTH_API_KEYS'] = ['test_key_123', 'another_key_456']
    simple_auth.init_app(app)

    # 测试视图函数
    @app.route('/protected')
    @simple_auth.require_api_key
    def protected_route():
        return jsonify({'message': 'Access granted'}), 200

    return app


def create_app_with_custom_header():
    """创建配置了自定义请求头的 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SIMPLE_AUTH_API_KEY_HEADER'] = 'Authorization'
    app.config['SIMPLE_AUTH_API_KEYS'] = ['test_key_123']
    simple_auth.init_app(app)

    # 测试视图函数
    @app.route('/protected_custom_header')
    @simple_auth.require_api_key
    def protected_custom_header_route():
        return jsonify({'message': 'Access granted with custom header'}), 200

    return app


def create_app_with_key_loader():
    """创建配置了自定义 Key Loader 的 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # 自定义 Key Loader 函数
    def key_loader(api_key):
        return api_key == 'dynamic_key_789'

    app.config['SIMPLE_AUTH_API_KEY_LOADER'] = key_loader
    simple_auth.init_app(app)

    # 测试视图函数
    @app.route('/protected_loader')
    @simple_auth.require_api_key
    def protected_loader_route():
        return jsonify({'message': 'Access granted with key loader'}), 200

    return app


def create_app_with_both_static_and_loader():
    """创建同时配置了静态 Key 和 Key Loader 的 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SIMPLE_AUTH_API_KEYS'] = ['static_key_123']

    # 自定义 Key Loader 函数
    def key_loader(api_key):
        return api_key == 'dynamic_key_456'

    app.config['SIMPLE_AUTH_API_KEY_LOADER'] = key_loader
    simple_auth.init_app(app)

    # 测试视图函数
    @app.route('/protected_both')
    @simple_auth.require_api_key
    def protected_both_route():
        return jsonify({'message': 'Access granted with either static or dynamic key'}), 200

    return app


@pytest.fixture
def app_with_static_keys():
    """创建配置了静态 API Key 的 Flask 应用"""
    return create_app_with_static_keys()


@pytest.fixture
def app_with_custom_header():
    """创建配置了自定义请求头的 Flask 应用"""
    return create_app_with_custom_header()


@pytest.fixture
def app_with_key_loader():
    """创建配置了自定义 Key Loader 的 Flask 应用"""
    return create_app_with_key_loader()


@pytest.fixture
def app_with_both_static_and_loader():
    """创建同时配置了静态 Key 和 Key Loader 的 Flask 应用"""
    return create_app_with_both_static_and_loader()


@pytest.fixture
def client(app_with_static_keys):
    """创建测试客户端"""
    return app_with_static_keys.test_client()


def test_missing_api_key(client):
    """测试缺少 API Key 的情况"""
    response = client.get('/protected')
    assert response.status_code == 401
    assert b'Missing API Key' in response.data

def test_invalid_api_key(client):
    """测试无效 API Key 的情况"""
    response = client.get('/protected', headers={'X-API-Key': 'invalid_key'})
    assert response.status_code == 403
    assert b'Invalid API Key' in response.data

def test_valid_api_key(client):
    """测试有效 API Key 的情况"""
    response = client.get('/protected', headers={'X-API-Key': 'test_key_123'})
    assert response.status_code == 200
    assert b'Access granted' in response.data

def test_another_valid_api_key(client):
    """测试另一个有效 API Key 的情况"""
    response = client.get('/protected', headers={'X-API-Key': 'another_key_456'})
    assert response.status_code == 200
    assert b'Access granted' in response.data

def test_custom_header():
    """测试自定义请求头的情况"""
    app = create_app_with_custom_header()
    client = app.test_client()
    response = client.get('/protected_custom_header', headers={'Authorization': 'test_key_123'})
    assert response.status_code == 200
    assert b'Access granted with custom header' in response.data

def test_key_loader_valid():
    """测试有效的动态 Key"""
    app = create_app_with_key_loader()
    client = app.test_client()
    response = client.get('/protected_loader', headers={'X-API-Key': 'dynamic_key_789'})
    assert response.status_code == 200
    assert b'Access granted with key loader' in response.data

def test_key_loader_invalid():
    """测试无效的动态 Key"""
    app = create_app_with_key_loader()
    client = app.test_client()
    response = client.get('/protected_loader', headers={'X-API-Key': 'invalid_dynamic_key'})
    assert response.status_code == 403
    assert b'Invalid API Key' in response.data

def test_both_static_key_valid():
    """测试静态 Key 有效"""
    app = create_app_with_both_static_and_loader()
    client = app.test_client()
    response = client.get('/protected_both', headers={'X-API-Key': 'static_key_123'})
    assert response.status_code == 200

def test_both_dynamic_key_valid():
    """测试动态 Key 有效"""
    app = create_app_with_both_static_and_loader()
    client = app.test_client()
    response = client.get('/protected_both', headers={'X-API-Key': 'dynamic_key_456'})
    assert response.status_code == 200

def test_both_key_invalid():
    """测试静态和动态 Key 都无效"""
    app = create_app_with_both_static_and_loader()
    client = app.test_client()
    response = client.get('/protected_both', headers={'X-API-Key': 'invalid_key'})
    assert response.status_code == 403

def test_extension_initialization():
    """测试扩展初始化"""
    app = Flask(__name__)
    auth = FlaskSimpleAuth(app)
    assert 'simple_auth' in app.extensions
    assert app.extensions['simple_auth'] == auth

def test_delayed_initialization():
    """测试延迟初始化"""
    app = Flask(__name__)
    auth = FlaskSimpleAuth()
    assert 'simple_auth' not in app.extensions
    auth.init_app(app)
    assert 'simple_auth' in app.extensions
    assert app.extensions['simple_auth'] == auth
