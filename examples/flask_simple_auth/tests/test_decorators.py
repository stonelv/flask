"""
Tests for Flask-Simple-Auth decorators.
"""

import pytest
from flask import Flask, g
from flask_simple_auth import SimpleAuth, require_api_key


class TestRequireApiKeyDecorator:
    """Test @require_api_key decorator."""
    
    def test_require_api_key_success(self, app, client):
        """Test successful API key authentication."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {"status": "success", "authenticated": g.get("api_key_authenticated")}
        
        response = client.get("/protected", headers={"X-API-Key": "valid-key"})
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["authenticated"] is True
    
    def test_require_api_key_failure_no_header(self, app, client):
        """Test authentication failure without API key header."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {"status": "should not reach here"}
        
        response = client.get("/protected")
        assert response.status_code == 401
        assert b"Invalid or missing API key" in response.data
    
    def test_require_api_key_failure_invalid_key(self, app, client):
        """Test authentication failure with invalid API key."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {"status": "should not reach here"}
        
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401
        assert b"Invalid or missing API key" in response.data
    
    def test_require_api_key_custom_error_message(self, app, client):
        """Test custom error message configuration."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        app.config["SIMPLE_AUTH_ERROR_MESSAGE"] = "Custom authentication error"
        app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] = 403
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {"status": "should not reach here"}
        
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 403
        assert b"Custom authentication error" in response.data
    
    def test_require_api_key_with_explicit_auth_instance(self, app, client):
        """Test decorator with explicit auth instance."""
        auth = SimpleAuth(app)
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        
        @app.route("/protected")
        @require_api_key(auth=auth)
        def protected():
            return {"status": "success"}
        
        response = client.get("/protected", headers={"X-API-Key": "valid-key"})
        assert response.status_code == 200
        assert response.json["status"] == "success"
    
    def test_require_api_key_no_auth_extension(self, app, client):
        """Test decorator when auth extension is not initialized."""
        # 不初始化SimpleAuth扩展
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {"status": "should not reach here"}
        
        response = client.get("/protected", headers={"X-API-Key": "any-key"})
        assert response.status_code == 500
        assert b"SimpleAuth extension not initialized" in response.data
    
    def test_api_key_stored_in_g_object(self, app, client):
        """Test that API key is stored in g object after successful authentication."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"valid-key"}
        auth = SimpleAuth(app)
        
        @app.route("/protected")
        @require_api_key()
        def protected():
            return {
                "authenticated": g.get("api_key_authenticated"),
                "api_key": g.get("api_key")
            }
        
        response = client.get("/protected", headers={"X-API-Key": "valid-key"})
        assert response.status_code == 200
        assert response.json["authenticated"] is True
        assert response.json["api_key"] == "valid-key"
    
    def test_multiple_protected_routes(self, app, client):
        """Test multiple protected routes with different keys."""
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"key1", "key2"}
        auth = SimpleAuth(app)
        
        @app.route("/route1")
        @require_api_key()
        def route1():
            return {"route": "1"}
        
        @app.route("/route2")
        @require_api_key()
        def route2():
            return {"route": "2"}
        
        # 测试第一个路由
        response = client.get("/route1", headers={"X-API-Key": "key1"})
        assert response.status_code == 200
        assert response.json["route"] == "1"
        
        # 测试第二个路由
        response = client.get("/route2", headers={"X-API-Key": "key2"})
        assert response.status_code == 200
        assert response.json["route"] == "2"
        
        # 测试无效key
        response = client.get("/route1", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401