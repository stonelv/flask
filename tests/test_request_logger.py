from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask, g, RequestLogger, request_id
from flask.testing import FlaskClient


class TestRequestLogger(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()
        
        # 添加一个简单的路由用于测试
        @self.app.route("/")
        def index():
            return "Hello, World!"
    
    def test_request_id_injection(self):
        """测试Request ID是否正确注入到响应头中。"""
        logger = RequestLogger(self.app)
        
        # 发送请求
        response = self.client.get("/")
        
        # 验证响应头中包含Request ID
        self.assertIn("X-Request-ID", response.headers)
        self.assertTrue(len(response.headers["X-Request-ID"]) > 0)
    
    def test_custom_header_name(self):
        """测试自定义响应头名称。"""
        self.app.config["REQUEST_LOGGER_HEADER_NAME"] = "Custom-Request-ID"
        logger = RequestLogger(self.app)
        
        # 发送请求
        response = self.client.get("/")
        
        # 验证响应头使用了自定义名称
        self.assertNotIn("X-Request-ID", response.headers)
        self.assertIn("Custom-Request-ID", response.headers)
    
    def test_log_format_json(self):
        """测试JSON格式的日志输出。"""
        # 使用上下文管理器创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as temp:
            log_path = temp.name
        
        try:
            self.app.config["REQUEST_LOGGER_LOG_FILE"] = log_path
            self.app.config["REQUEST_LOGGER_LOG_JSON"] = True
            logger = RequestLogger(self.app)
            
            # 发送请求
            response = self.client.get("/")
            request_id_value = response.headers["X-Request-ID"]
            
            # 显式关闭logger处理器，确保文件写入完成
            if hasattr(logger, 'logger'):
                for handler in logger.logger.handlers:
                    try:
                        handler.flush()
                        handler.close()
                    except Exception:
                        pass
            
            # 确保日志写入
            import time
            time.sleep(0.1)  # 给一点时间让日志写入
            
            # 打开日志文件以读取内容
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read().strip()
            
            # 解析JSON并验证字段
            log_data = json.loads(log_content)
            self.assertEqual(log_data["method"], "GET")
            self.assertEqual(log_data["path"], "/")
            self.assertEqual(log_data["status"], 200)
            self.assertEqual(log_data["request_id"], request_id_value)
            self.assertIn("timestamp", log_data)
            self.assertIn("duration_ms", log_data)
            self.assertIn("remote_addr", log_data)
        finally:
            # 清理临时文件
            try:
                if os.path.exists(log_path):
                    os.unlink(log_path)
            except Exception:
                pass
    
    def test_log_format_text(self):
        """测试文本格式的日志输出。"""
        # 使用上下文管理器创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as temp:
            log_path = temp.name
        
        try:
            self.app.config["REQUEST_LOGGER_LOG_FILE"] = log_path
            self.app.config["REQUEST_LOGGER_LOG_JSON"] = False
            logger = RequestLogger(self.app)
            
            # 发送请求
            response = self.client.get("/")
            request_id_value = response.headers["X-Request-ID"]
            
            # 显式关闭logger处理器，确保文件写入完成
            if hasattr(logger, 'logger'):
                for handler in logger.logger.handlers:
                    try:
                        handler.flush()
                        handler.close()
                    except Exception:
                        pass
            
            # 确保日志写入
            import time
            time.sleep(0.1)  # 给一点时间让日志写入
            
            # 打开日志文件以读取内容
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read().strip()
            
            # 验证文本日志包含必要信息
            self.assertIn("GET", log_content)
            self.assertIn("/", log_content)
            self.assertIn("200", log_content)
            self.assertIn(request_id_value, log_content)
        finally:
            # 清理临时文件
            try:
                if os.path.exists(log_path):
                    os.unlink(log_path)
            except Exception:
                pass
    
    def test_disabled(self):
        """测试禁用日志记录功能。"""
        self.app.config["REQUEST_LOGGER_ENABLED"] = False
        
        # 模拟logger.info方法
        with patch('logging.Logger.info') as mock_info:
            logger = RequestLogger(self.app)
            
            # 发送请求
            response = self.client.get("/")
            
            # 验证没有记录日志
            mock_info.assert_not_called()
            
            # 验证没有注入请求头
            self.assertNotIn("X-Request-ID", response.headers)
    
    def test_factory_pattern(self):
        """测试工厂模式初始化。"""
        # 先创建logger实例
        logger = RequestLogger()
        
        # 后初始化app
        logger.init_app(self.app)
        
        # 发送请求
        response = self.client.get("/")
        
        # 验证功能正常
        self.assertIn("X-Request-ID", response.headers)
    
    def test_request_id_proxy(self):
        """测试request_id代理对象。"""
        logger = RequestLogger(self.app)
        
        # 在请求上下文中访问request_id
        with self.app.test_request_context("/"):
            # 模拟before_request的效果
            from flask import g
            g.request_id = "test-request-id"
            
            # 验证代理返回正确的值
            self.assertEqual(request_id, "test-request-id")
    
    def test_passing_config_dict(self):
        """测试通过init_app传递配置字典。"""
        logger = RequestLogger()
        logger.init_app(self.app, {
            "REQUEST_LOGGER_HEADER_NAME": "Test-Request-ID"
        })
        
        # 发送请求
        response = self.client.get("/")
        
        # 验证使用了传递的配置
        self.assertIn("Test-Request-ID", response.headers)
    
    def test_incoming_request_id(self):
        """测试传入请求中已有的Request ID。"""
        logger = RequestLogger(self.app)
        
        # 发送带有Request ID的请求
        incoming_request_id = "incoming-123-456"
        response = self.client.get("/", headers={
            "X-Request-ID": incoming_request_id
        })
        
        # 验证响应使用了相同的Request ID
        self.assertEqual(response.headers["X-Request-ID"], incoming_request_id)
