from flask import request, current_app, abort
from functools import wraps
from typing import Callable, Optional, List

class FlaskSimpleAuth:
    """Flask 简单 API Key 验证扩展"""

    def __init__(self, app=None):
        """初始化扩展"""
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """延迟初始化应用"""
        # 默认配置
        app.config.setdefault('SIMPLE_AUTH_API_KEY_HEADER', 'X-API-Key')
        app.config.setdefault('SIMPLE_AUTH_API_KEYS', [])
        app.config.setdefault('SIMPLE_AUTH_API_KEY_LOADER', None)

        # 将扩展实例保存到 app 中
        app.extensions['simple_auth'] = self

    def require_api_key(self, f: Callable) -> Callable:
        """API Key 验证装饰器"""
        @wraps(f)
        def decorated(*args, **kwargs):
            # 获取配置
            header_name = current_app.config.get('SIMPLE_AUTH_API_KEY_HEADER', 'X-API-Key')
            static_keys = current_app.config.get('SIMPLE_AUTH_API_KEYS', [])
            key_loader = current_app.config.get('SIMPLE_AUTH_API_KEY_LOADER')

            # 确保 header_name 是字符串类型
            if not isinstance(header_name, str):
                header_name = 'X-API-Key'

            # 从请求头中获取 API Key
            api_key = request.headers.get(header_name)
            if not api_key:
                abort(401, description='Missing API Key')

            # 验证 API Key
            is_valid = False

            # 检查静态 Key
            if api_key in static_keys:
                is_valid = True

            # 检查 Key Loader（如果配置了）
            if not is_valid and key_loader is not None:
                try:
                    is_valid = key_loader(api_key)
                except Exception as e:
                    current_app.logger.error(f'API Key loader error: {e}')
                    abort(500, description='Internal Server Error')

            if not is_valid:
                abort(403, description='Invalid API Key')

            # 验证通过，继续执行视图函数
            return f(*args, **kwargs)

        return decorated

# 创建扩展实例
simple_auth = FlaskSimpleAuth()
