"""单元测试速率限制装饰器"""

import time
import pytest
from flask import Flask
from flask import jsonify, request

from flaskr.rate_limit import rate_limit, _access_records


class TestRateLimit:
    """测试速率限制装饰器"""
    
    def setup_method(self):
        """在每个测试前清空访问记录"""
        _access_records.clear()
    
    def test_rate_limit_within_limit(self):
        """测试在限制范围内的请求"""
        app = Flask(__name__)
        
        @app.route("/test")
        @rate_limit(limit=5, window_seconds=60)
        def test():
            return jsonify({"status": "success"})
        
        # 模拟5次请求（应该都成功）
        with app.test_client() as client:
            for i in range(5):
                response = client.get("/test")
                assert response.status_code == 200
                assert response.json["status"] == "success"
    
    def test_rate_limit_exceeds_limit(self):
        """测试超出速率限制的情况"""
        app = Flask(__name__)
        
        @app.route("/test")
        @rate_limit(limit=3, window_seconds=60)
        def test():
            return jsonify({"status": "success"})
        
        with app.test_client() as client:
            # 前3次请求应该成功
            for i in range(3):
                response = client.get("/test")
                assert response.status_code == 200
            
            # 第4次请求应该被限制
            response = client.get("/test")
            assert response.status_code == 429
            assert response.json["error"] == "Too Many Requests"
    
    def test_rate_limit_time_window(self):
        """测试时间窗口功能"""
        app = Flask(__name__)
        
        @app.route("/test")
        @rate_limit(limit=2, window_seconds=1)  # 1秒窗口
        def test():
            return jsonify({"status": "success"})
        
        with app.test_client() as client:
            # 第一次请求
            response = client.get("/test")
            assert response.status_code == 200
            
            # 第二次请求（应该成功）
            response = client.get("/test")
            assert response.status_code == 200
            
            # 第三次请求（应该被限制）
            response = client.get("/test")
            assert response.status_code == 429
            
            # 等待时间窗口过期
            time.sleep(1)
            
            # 再次请求（应该成功）
            response = client.get("/test")
            assert response.status_code == 200
    
    def test_rate_limit_decorator_preserves_metadata(self):
        """测试装饰器是否保留函数元数据"""
        @rate_limit(limit=10, window_seconds=60)
        def my_function():
            """这是一个测试函数"""
            pass
        
        # 检查函数名是否保留
        assert my_function.__name__ == "my_function"
        
        # 检查文档字符串是否保留
        assert my_function.__doc__ == "这是一个测试函数"