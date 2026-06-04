import logging
import time
import uuid
from typing import Optional, Dict, Any
from flask import Flask, g, request, Response


class RequestLogger:
    """Flask请求日志扩展，提供结构化JSON日志和Request ID支持。

    功能特性：
    - 为每个请求生成唯一的Request ID
    - 在响应头中注入Request ID
    - 记录结构化JSON访问日志
    - 支持多种配置选项

    配置参数：
    - ENABLED: 是否启用日志记录 (默认: True)
    - HEADER_NAME: 响应头中Request ID的名称 (默认: "X-Request-ID")
    - LOG_JSON: 是否以JSON格式记录日志 (默认: True)
    - LOG_FILE: 日志文件路径 (默认: None，使用标准输出)
    - LOG_LEVEL: 日志级别 (默认: "INFO")
    """

    def __init__(self, app: Optional[Flask] = None, config: Optional[Dict[str, Any]] = None):
        """初始化RequestLogger扩展。

        Args:
            app: Flask应用实例
            config: 配置字典，覆盖app.config中的设置
        """
        self.app = app
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        if app is not None:
            self.init_app(app, config)

    def init_app(self, app: Flask, config: Optional[Dict[str, Any]] = None):
        """初始化Flask应用。

        Args:
            app: Flask应用实例
            config: 配置字典，覆盖app.config中的设置
        """
        # 合并配置
        final_config = {
            **app.config.get_namespace("REQUEST_LOGGER_"),
            **(config or {}),
            **self.config,
        }

        # 配置默认值
        self.enabled = final_config.get("ENABLED", True)
        self.header_name = final_config.get("HEADER_NAME", "X-Request-ID")
        self.log_json = final_config.get("LOG_JSON", True)
        self.log_file = final_config.get("LOG_FILE")
        self.log_level = final_config.get("LOG_LEVEL", "INFO")

        if not self.enabled:
            return

        # 配置日志
        self._configure_logger()

        # 注册请求钩子
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _configure_logger(self):
        """配置日志记录器。"""
        # 设置日志级别
        self.logger.setLevel(getattr(logging, self.log_level.upper(), logging.INFO))

        # 清除现有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 创建处理器
        if self.log_file:
            handler = logging.FileHandler(self.log_file)
        else:
            handler = logging.StreamHandler()

        # 设置格式化器
        if self.log_json:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(request_id)s - %(method)s %(path)s - %(status)s - %(duration_ms)dms'
            )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _before_request(self):
        """请求前钩子：生成Request ID并记录请求开始时间。"""
        # 生成Request ID
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.request_start_time = time.time()

    def _after_request(self, response: Response) -> Response:
        """请求后钩子：注入Request ID到响应头并记录访问日志。"""
        # 注入Request ID到响应头
        if hasattr(g, 'request_id'):
            response.headers[self.header_name] = g.request_id

        # 记录访问日志
        if hasattr(g, 'request_start_time'):
            duration_ms = int((time.time() - g.request_start_time) * 1000)
            self._log_request(response.status_code, duration_ms)

        return response

    def _log_request(self, status: int, duration_ms: int):
        """记录访问日志。

        Args:
            status: 响应状态码
            duration_ms: 请求处理时长（毫秒）
        """
        log_data = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime()),
            'method': request.method,
            'path': request.path,
            'status': status,
            'duration_ms': duration_ms,
            'request_id': getattr(g, 'request_id', 'N/A'),
            'remote_addr': request.remote_addr or 'N/A',
        }

        if self.log_json:
            import json
            self.logger.info(json.dumps(log_data))
        else:
            # 手动构建非JSON格式的日志消息
            log_message = f'{log_data["method"]} {log_data["path"]} - {log_data["status"]} - {log_data["duration_ms"]}ms - {log_data["request_id"]} - {log_data["remote_addr"]}'
            self.logger.info(log_message)


# 导出扩展实例
request_logger = RequestLogger()
