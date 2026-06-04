"""
Tests for Flask-Simple-Auth extension.
"""

import pytest
from flask import Flask
from flask_simple_auth import SimpleAuth, require_api_key


class TestSimpleAuth:
    """Test SimpleAuth extension."""
    
    def test_init_with_app(self, app):
        """Test initialization with app."""
        auth = SimpleAuth(app)
        assert auth.app == app
        assert "simple_auth" in app.extensions
    
    def test_init_without_app(self):
        """Test initialization without app."""
        auth = SimpleAuth()
        assert auth.app is None
    
    def test_init_app(self, app):
        """Test init_app method."""
        auth = SimpleAuth()
        auth.init_app(app)
        assert auth.app == app
        assert "simple_auth" in app.extensions
    
    def test_default_config(self, app, auth):
        """Test default configuration."""
        assert app.config["SIMPLE_AUTH_HEADER_NAME"] == "X-API-Key"
        assert app.config["SIMPLE_AUTH_STATIC_KEYS"] == set()
        assert app.config["SIMPLE_AUTH_KEY_LOADER"] is None
        assert app.config["SIMPLE_AUTH_ERROR_MESSAGE"] == "Invalid or missing API key"
        assert app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] == 401
    
    def test_custom_config(self, app):
        """Test custom configuration."""
        app.config["SIMPLE_AUTH_HEADER_NAME"] = "Authorization"
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"test-key-1", "test-key-2"}
        app.config["SIMPLE_AUTH_ERROR_MESSAGE"] = "Custom error"
        app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] = 403
        
        auth = SimpleAuth(app)
        
        assert app.config["SIMPLE_AUTH_HEADER_NAME"] == "Authorization"
        assert app.config["SIMPLE_AUTH_STATIC_KEYS"] == {"test-key-1", "test-key-2"}
        assert app.config["SIMPLE_AUTH_ERROR_MESSAGE"] == "Custom error"
        assert app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] == 403
    
    def test_get_api_key_from_header(self, app, auth, client):
        """Test getting API key from header."""
        @app.route("/test")
        def test_route():
            api_key = auth.get_api_key()
            return {"api_key": api_key}
        
        # 测试没有header的情况
        response = client.get("/test")
        assert response.json["api_key"] is None
        
        # 测试有header的情况
        response = client.get("/test", headers={"X-API-Key": "test-key"})
        assert response.json["api_key"] == "test-key"
    
    def test_validate_static_keys(self, app):
        """Test validation with static keys."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key-1", "valid-key-2"}
        auth = SimpleAuth(app)
        
        with app.app_context():
            assert auth.validate_api_key("valid-key-1") is True
            assert auth.validate_api_key("valid-key-2") is True
            assert auth.validate_api_key("invalid-key") is False
    
    def test_validate_with_key_loader(self, app):
        """Test validation with custom key loader."""
        def key_loader(api_key):
            return api_key.startswith("valid-")
        
        app.config["SIMPLE_AUTH_KEY_LOADER"] = key_loader
        auth = SimpleAuth(app)
        
        with app.app_context():
            assert auth.validate_api_key("valid-key") is True
            assert auth.validate_api_key("invalid-key") is False
    
    def test_key_loader_priority_over_static_keys(self, app):
        """Test that key loader takes priority over static keys."""
        def key_loader(api_key):
            return api_key == "loader-key"
        
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"static-key"}
        app.config["SIMPLE_AUTH_KEY_LOADER"] = key_loader
        auth = SimpleAuth(app)
        
        # key loader应该优先使用
        with app.app_context():
            assert auth.validate_api_key("loader-key") is True
            assert auth.validate_api_key("static-key") is False
    
    def test_authenticate_request_success(self, app, client):
        """Test successful request authentication."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"test-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        def protected():
            if auth.authenticate_request():
                return {"status": "authenticated"}
            return {"status": "failed"}
        
        response = client.get("/protected", headers={"X-API-Key": "test-key"})
        assert response.json["status"] == "authenticated"
    
    def test_authenticate_request_failure(self, app, client):
        """Test failed request authentication."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"test-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        def protected():
            if auth.authenticate_request():
                return {"status": "authenticated"}
            return {"status": "failed"}
        
        # 测试没有header的情况
        response = client.get("/protected")
        assert response.json["status"] == "failed"
        
        # 测试无效key的情况
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.json["status"] == "failed"
    
    def test_custom_header_name(self, app, client):
        """Test custom header name configuration."""
        app.config["SIMPLE_AUTH_HEADER_NAME"] = "Authorization"
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"test-key"}
        auth = SimpleAuth(app)
        
        @app.route("/test")
        def test_route():
            return {"api_key": auth.get_api_key()}
        
        # 使用自定义header名称
        response = client.get("/test", headers={"Authorization": "test-key"})
        assert response.json["api_key"] == "test-key"
        
        # 默认header应该无效
        response = client.get("/test", headers={"X-API-Key": "test-key"})
        assert response.json["api_key"] is None