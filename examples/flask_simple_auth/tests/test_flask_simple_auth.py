"""
Flask Simple Auth 测试
"""

import pytest
from flask import Flask, jsonify

from flask_simple_auth import SimpleAuth, require_api_key


@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__)
    
    # 配置静态 API keys
    app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']
    
    # 初始化扩展
    SimpleAuth(app)
    
    @app.route('/protected')
    @require_api_key
    def protected():
        return jsonify({'message': 'This is a protected endpoint'})
    
    @app.route('/optional')
    @require_api_key(optional=True)
    def optional():
        return jsonify({'message': 'This is an optional protected endpoint'})
    
    @app.route('/public')
    def public():
        return jsonify({'message': 'This is a public endpoint'})
    
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestSimpleAuth:
    """SimpleAuth 扩展测试"""
    
    def test_init_app(self, app):
        """测试应用初始化"""
        assert 'simple_auth' in app.extensions
        assert isinstance(app.extensions['simple_auth'], SimpleAuth)
        assert app.config['SIMPLE_AUTH_HEADER_NAME'] == 'X-API-Key'
        assert app.config['SIMPLE_AUTH_KEYS'] == ['key1', 'key2', 'key3']
    
    def test_verify_api_key_with_static_keys(self, app):
        """测试使用静态 keys 验证 API key"""
        with app.app_context():
            simple_auth = app.extensions['simple_auth']
            
            # 有效的 key
            assert simple_auth.verify_api_key('key1') is True
            assert simple_auth.verify_api_key('key2') is True
            assert simple_auth.verify_api_key('key3') is True
            
            # 无效的 key
            assert simple_auth.verify_api_key('invalid_key') is False
            assert simple_auth.verify_api_key('') is False
            assert simple_auth.verify_api_key(None) is False
    
    def test_verify_api_key_with_key_loader(self, app):
        """测试使用 key_loader 验证 API key"""
        # 设置 key_loader
        def custom_key_loader(api_key):
            return api_key.startswith('custom_')
        
        with app.app_context():
            app.config['SIMPLE_AUTH_KEY_LOADER'] = custom_key_loader
            simple_auth = app.extensions['simple_auth']
            
            # 有效的 key
            assert simple_auth.verify_api_key('custom_valid') is True
            
            # 无效的 key
            assert simple_auth.verify_api_key('invalid_key') is False
            assert simple_auth.verify_api_key('key1') is False
    
    def test_get_api_key_from_header(self, app):
        """测试从 header 中获取 API key"""
        with app.test_request_context(headers={'X-API-Key': 'test_key'}):
            simple_auth = app.extensions['simple_auth']
            assert simple_auth.get_api_key_from_request() == 'test_key'
    
    def test_get_api_key_from_query(self, app):
        """测试从查询参数中获取 API key"""
        with app.test_request_context('/?api_key=test_key'):
            simple_auth = app.extensions['simple_auth']
            assert simple_auth.get_api_key_from_request() == 'test_key'
    
    def test_get_api_key_from_custom_header(self, app):
        """测试从自定义 header 中获取 API key"""
        app.config['SIMPLE_AUTH_HEADER_NAME'] = 'Authorization'
        
        with app.test_request_context(headers={'Authorization': 'Bearer test_key'}):
            simple_auth = app.extensions['simple_auth']
            assert simple_auth.get_api_key_from_request() == 'Bearer test_key'
    
    def test_get_api_key_not_found(self, app):
        """测试没有找到 API key 的情况"""
        with app.test_request_context():
            simple_auth = app.extensions['simple_auth']
            assert simple_auth.get_api_key_from_request() is None


class TestRequireApiKeyDecorator:
    """@require_api_key 装饰器测试"""
    
    def test_protected_endpoint_with_valid_key(self, client):
        """测试受保护端点使用有效 key 访问"""
        response = client.get('/protected', headers={'X-API-Key': 'key1'})
        assert response.status_code == 200
        assert response.json == {'message': 'This is a protected endpoint'}
    
    def test_protected_endpoint_with_invalid_key(self, client):
        """测试受保护端点使用无效 key 访问"""
        response = client.get('/protected', headers={'X-API-Key': 'invalid_key'})
        assert response.status_code == 401
        assert 'error' in response.json
    
    def test_protected_endpoint_without_key(self, client):
        """测试受保护端点没有 key 访问"""
        response = client.get('/protected')
        assert response.status_code == 401
        assert 'error' in response.json
    
    def test_optional_endpoint_with_key(self, client):
        """测试可选保护端点使用 key 访问"""
        response = client.get('/optional', headers={'X-API-Key': 'key1'})
        assert response.status_code == 200
        assert response.json == {'message': 'This is an optional protected endpoint'}
    
    def test_optional_endpoint_without_key(self, client):
        """测试可选保护端点没有 key 访问"""
        response = client.get('/optional')
        assert response.status_code == 200
        assert response.json == {'message': 'This is an optional protected endpoint'}
    
    def test_optional_endpoint_with_invalid_key(self, client):
        """测试可选保护端点使用无效 key 访问"""
        response = client.get('/optional', headers={'X-API-Key': 'invalid_key'})
        assert response.status_code == 401
        assert 'error' in response.json
    
    def test_public_endpoint(self, client):
        """测试公共端点访问"""
        response = client.get('/public')
        assert response.status_code == 200
        assert response.json == {'message': 'This is a public endpoint'}


class TestCustomConfiguration:
    """自定义配置测试"""
    
    @pytest.fixture
    def custom_app(self):
        """创建自定义配置的测试应用"""
        app = Flask(__name__)
        
        # 自定义配置
        app.config['SIMPLE_AUTH_HEADER_NAME'] = 'Authorization'
        app.config['SIMPLE_AUTH_KEYS'] = ['custom_key1', 'custom_key2']
        app.config['SIMPLE_AUTH_REALM'] = 'Custom Realm'
        app.config['SIMPLE_AUTH_ERROR_MESSAGE'] = 'Custom error message'
        
        # 初始化扩展
        SimpleAuth(app)
        
        @app.route('/custom')
        @require_api_key
        def custom():
            return jsonify({'message': 'Custom protected endpoint'})
        
        return app
    
    @pytest.fixture
    def custom_client(self, custom_app):
        """创建自定义配置的测试客户端"""
        return custom_app.test_client()
    
    def test_custom_header_name(self, custom_client):
        """测试自定义 header 名称"""
        # 使用自定义 header
        response = custom_client.get('/custom', headers={'Authorization': 'custom_key1'})
        assert response.status_code == 200
        
        # 使用默认 header 应该失败
        response = custom_client.get('/custom', headers={'X-API-Key': 'custom_key1'})
        assert response.status_code == 401
    
    def test_custom_error_message(self, custom_client):
        """测试自定义错误消息"""
        response = custom_client.get('/custom')
        assert response.status_code == 401
        assert response.json['error'] == 'Custom error message'
    
    def test_custom_realm(self, custom_client):
        """测试自定义 realm"""
        response = custom_client.get('/custom')
        assert response.status_code == 401
        assert 'Custom Realm' in response.headers.get('WWW-Authenticate', '')


class TestKeyLoader:
    """Key Loader 测试"""
    
    @pytest.fixture
    def key_loader_app(self):
        """创建使用 key_loader 的测试应用"""
        app = Flask(__name__)
        
        # 定义 key_loader 函数
        def key_loader(api_key):
            # 模拟从数据库验证 API key
            valid_keys = {
                'user1_key': {'user_id': 1, 'permissions': ['read', 'write']},
                'user2_key': {'user_id': 2, 'permissions': ['read']},
            }
            return api_key in valid_keys
        
        app.config['SIMPLE_AUTH_KEY_LOADER'] = key_loader
        
        # 初始化扩展
        SimpleAuth(app)
        
        @app.route('/loader')
        @require_api_key
        def loader():
            return jsonify({'message': 'Key loader protected endpoint'})
        
        return app
    
    @pytest.fixture
    def key_loader_client(self, key_loader_app):
        """创建使用 key_loader 的测试客户端"""
        return key_loader_app.test_client()
    
    def test_key_loader_valid_key(self, key_loader_client):
        """测试 key_loader 验证有效 key"""
        response = key_loader_client.get('/loader', headers={'X-API-Key': 'user1_key'})
        assert response.status_code == 200
    
    def test_key_loader_invalid_key(self, key_loader_client):
        """测试 key_loader 验证无效 key"""
        response = key_loader_client.get('/loader', headers={'X-API-Key': 'invalid_key'})
        assert response.status_code == 401