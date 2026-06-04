"""
Integration tests for Flask-Simple-Auth.
"""

import pytest
from flask import Flask, jsonify, g
from flask_simple_auth import SimpleAuth, require_api_key


class TestIntegration:
    """Integration tests for Flask-Simple-Auth."""
    
    def test_full_integration_static_keys(self):
        """Test full integration with static keys."""
        app = Flask(__name__)
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"secret-key-1", "secret-key-2"}
        
        auth = SimpleAuth(app)
        
        @app.route("/public")
        def public():
            return jsonify({"message": "This is public"})
        
        @app.route("/private")
        @require_api_key()
        def private():
            return jsonify({"message": "This is private", "authenticated": True})
        
        @app.route("/admin")
        @require_api_key()
        def admin():
            return jsonify({"message": "Admin area", "level": "admin"})
        
        client = app.test_client()
        
        # 测试公共路由
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json["message"] == "This is public"
        
        # 测试私有路由 - 无认证
        response = client.get("/private")
        assert response.status_code == 401
        
        # 测试私有路由 - 有效认证
        response = client.get("/private", headers={"X-API-Key": "secret-key-1"})
        assert response.status_code == 200
        assert response.json["message"] == "This is private"
        assert response.json["authenticated"] is True
        
        # 测试私有路由 - 无效认证
        response = client.get("/private", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        
        # 测试管理路由 - 有效认证
        response = client.get("/admin", headers={"X-API-Key": "secret-key-2"})
        assert response.status_code == 200
        assert response.json["message"] == "Admin area"
        assert response.json["level"] == "admin"
    
    def test_full_integration_key_loader(self):
        """Test full integration with key loader function."""
        app = Flask(__name__)
        
        def custom_key_loader(api_key):
            """自定义key loader：验证key格式为 'user-{username}-2024' """
            return (api_key.startswith("user-") and 
                   api_key.endswith("-2024") and 
                   len(api_key) > 12)
        
        app.config["SIMPLE_AUTH_KEY_LOADER"] = custom_key_loader
        
        auth = SimpleAuth(app)
        
        @app.route("/api/user-data")
        @require_api_key()
        def user_data():
            return jsonify({
                "message": "User data accessed",
                "api_key": g.get("api_key")
            })
        
        client = app.test_client()
        
        # 测试有效key格式
        response = client.get("/api/user-data", headers={"X-API-Key": "user-alice-2024"})
        assert response.status_code == 200
        assert response.json["message"] == "User data accessed"
        assert response.json["api_key"] == "user-alice-2024"
        
        # 测试无效key格式
        response = client.get("/api/user-data", headers={"X-API-Key": "user-bob-2023"})
        assert response.status_code == 401
        
        response = client.get("/api/user-data", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401
        
        # 测试无key
        response = client.get("/api/user-data")
        assert response.status_code == 401
    
    def test_custom_header_integration(self):
        """Test integration with custom header name."""
        app = Flask(__name__)
        app.config["SIMPLE_AUTH_HEADER_NAME"] = "X-Custom-Auth"
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"custom-key"}
        app.config["SIMPLE_AUTH_ERROR_MESSAGE"] = "Access denied: Invalid credentials"
        app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] = 403
        
        auth = SimpleAuth(app)
        
        @app.route("/secure")
        @require_api_key()
        def secure():
            return jsonify({"message": "Secure data accessed"})
        
        client = app.test_client()
        
        # 使用自定义header
        response = client.get("/secure", headers={"X-Custom-Auth": "custom-key"})
        assert response.status_code == 200
        assert response.json["message"] == "Secure data accessed"
        
        # 使用默认header应该失败
        response = client.get("/secure", headers={"X-API-Key": "custom-key"})
        assert response.status_code == 403
        assert b"Access denied: Invalid credentials" in response.data
        
        # 无header应该失败
        response = client.get("/secure")
        assert response.status_code == 403
        assert b"Access denied: Invalid credentials" in response.data
    
    def test_mixed_authentication_scenarios(self):
        """Test mixed authentication scenarios."""
        app = Flask(__name__)
        
        # 配置：静态key + key loader
        app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"static-key-1", "static-key-2"}
        
        def dynamic_key_loader(api_key):
            """动态key loader：验证特定格式的key"""
            return api_key.startswith("dynamic-") and len(api_key) > 10
        
        app.config["SIMPLE_AUTH_KEY_LOADER"] = dynamic_key_loader
        
        auth = SimpleAuth(app)
        
        @app.route("/mixed-auth")
        @require_api_key()
        def mixed_auth():
            return jsonify({"message": "Authenticated via mixed method"})
        
        client = app.test_client()
        
        # 测试静态key (应该被key loader覆盖)
        response = client.get("/mixed-auth", headers={"X-API-Key": "static-key-1"})
        assert response.status_code == 401  # 因为key loader优先
        
        # 测试动态key (应该通过)
        response = client.get("/mixed-auth", headers={"X-API-Key": "dynamic-valid"})
        assert response.status_code == 200
        assert response.json["message"] == "Authenticated via mixed method"
        
        # 测试无效key
        response = client.get("/mixed-auth", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401