from __future__ import annotations

import json
import logging
import time
import uuid
import typing as t
from datetime import datetime, UTC

from werkzeug.local import LocalProxy

from . import g
from . import request
from . import current_app

if t.TYPE_CHECKING:
    from .sansio.app import App


class RequestLogger:
    """Flask扩展，提供结构化JSON访问日志和Request ID支持。
    
    功能特性：
    - 为每个请求生成唯一的request_id
    - 将request_id注入到响应头
    - 记录结构化的JSON访问日志
    - 支持多种配置选项
    
    使用示例：
    ```python
    from flask import Flask
    from flask.request_logger import RequestLogger
    
    app = Flask(__name__)
    logger = RequestLogger(app)
    
    # 或使用工厂模式
    logger = RequestLogger()
    
    def create_app():
        app = Flask(__name__)
        logger.init_app(app)
        return app
    ```
    
    配置选项：
    - REQUEST_LOGGER_ENABLED: 是否启用日志记录，默认为True
    - REQUEST_LOGGER_HEADER_NAME: 响应头名称，默认为"X-Request-ID"
    - REQUEST_LOGGER_LOG_JSON: 是否记录为JSON格式，默认为True
    - REQUEST_LOGGER_LOG_FILE: 日志文件路径，默认为None（使用标准输出）
    - REQUEST_LOGGER_LOG_LEVEL: 日志级别，默认为"INFO"
    """
    
    def __init__(self, app: App | None = None):
        """初始化扩展。
        
        Args:
            app: Flask应用实例，如果为None，则需要稍后调用init_app方法
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: App, config: dict[str, t.Any] | None = None) -> None:
        """初始化Flask应用。
        
        Args:
            app: Flask应用实例
            config: 配置字典，可覆盖app.config中的设置
        """
        # 设置默认配置
        app.config.setdefault("REQUEST_LOGGER_ENABLED", True)
        app.config.setdefault("REQUEST_LOGGER_HEADER_NAME", "X-Request-ID")
        app.config.setdefault("REQUEST_LOGGER_LOG_JSON", True)
        app.config.setdefault("REQUEST_LOGGER_LOG_FILE", None)
        app.config.setdefault("REQUEST_LOGGER_LOG_LEVEL", "INFO")
        
        # 应用自定义配置
        if config:
            for key, value in config.items():
                if key.startswith("REQUEST_LOGGER_"):
                    app.config[key] = value
        
        # 存储扩展实例到app.extensions
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["request_logger"] = self
        
        # 只有在启用时才注册钩子函数
        if app.config["REQUEST_LOGGER_ENABLED"]:
            self._setup_logger(app)
            app.before_request(self._before_request)
            app.after_request(self._after_request)
    
    def _setup_logger(self, app: App) -> None:
        """设置日志记录器。
        
        Args:
            app: Flask应用实例
        """
        self.logger = logging.getLogger(f"{app.name}.request_logger")
        log_level = getattr(logging, app.config["REQUEST_LOGGER_LOG_LEVEL"], logging.INFO)
        self.logger.setLevel(log_level)
        self.logger.propagate = False  # 防止日志重复传播
        
        # 清除已有的处理器，避免重复
        self.logger.handlers.clear()
        
        # 确保logger存在
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger('flask.request_logger')
        
        # 清理现有的处理器
        for handler in self.logger.handlers[:]:
            try:
                handler.close()
            except Exception:
                pass
            self.logger.removeHandler(handler)
        
        # 设置日志级别和禁止传播
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        # 创建新的处理器
        log_file = app.config["REQUEST_LOGGER_LOG_FILE"]
        if log_file:
            try:
                handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            except Exception:
                # 如果文件创建失败，回退到StreamHandler
                handler = logging.StreamHandler()
        else:
            handler = logging.StreamHandler()
        
        # 设置格式化器
        formatter = logging.Formatter('%(message)s' if app.config["REQUEST_LOGGER_LOG_JSON"] else 
                                      "[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        
        # 添加处理器
        self.logger.addHandler(handler)
    
    def _generate_request_id(self) -> str:
        """生成唯一的请求ID。
        
        Returns:
            str: UUIDv4格式的请求ID
        """
        return str(uuid.uuid4())
    
    def _before_request(self) -> None:
        """请求前钩子，生成request_id并记录开始时间。"""
        # 从请求头获取request_id（如果存在），否则生成新的
        header_name = current_app.config["REQUEST_LOGGER_HEADER_NAME"]
        request_id = request.headers.get(header_name)
        if not request_id:
            request_id = self._generate_request_id()
        
        # 存储request_id和开始时间到g对象
        g.request_id = request_id
        g.request_start_time = time.time()
    
    def _after_request(self, response: t.Any) -> t.Any:
        """请求后钩子，记录访问日志并注入response header。
        
        Args:
            response: Flask响应对象
            
        Returns:
            Flask响应对象
        """
        # 获取request_id和计算请求持续时间
        request_id = getattr(g, "request_id", "unknown")
        start_time = getattr(g, "request_start_time", time.time())
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 注入response header
        header_name = current_app.config["REQUEST_LOGGER_HEADER_NAME"]
        response.headers[header_name] = request_id
        
        # 构建日志记录
        log_data = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "remote_addr": request.remote_addr or "unknown"
        }
        
        # 构建日志消息
        if current_app.config["REQUEST_LOGGER_LOG_JSON"]:
            log_message = json.dumps(log_data)
        else:
            log_message = f"{request.method} {request.path} {response.status_code} {duration_ms}ms {request_id} {request.remote_addr}"
        
        # 确保日志写入文件
        for handler in self.logger.handlers:
            handler.flush()
        
        self.logger.info(log_message)
        
        return response
    
    def __del__(self):
        # 清理日志处理器
        if hasattr(self, 'logger'):
            for handler in self.logger.handlers:
                try:
                    handler.close()
                except Exception:
                    pass
            self.logger.handlers.clear()


# 提供全局访问的request_id代理
def _get_request_id() -> str:
    """获取当前请求的request_id。"""
    return getattr(g, "request_id", "unknown")


request_id: t.Final = LocalProxy(_get_request_id)
"""当前请求的request_id代理对象。"""
