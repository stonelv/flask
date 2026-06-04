"""
Core extension class for Flask-Simple-Auth.
"""

from typing import Optional, Set, Callable, Union
from flask import Flask, request, current_app, g


class SimpleAuth:
    """Flask extension for simple API key authentication."""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize the extension.
        
        Args:
            app: Flask application instance (optional, can be initialized later)
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the extension with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # 配置默认值
        app.config.setdefault("SIMPLE_AUTH_HEADER_NAME", "X-API-Key")
        app.config.setdefault("SIMPLE_AUTH_STATIC_KEYS", set())
        app.config.setdefault("SIMPLE_AUTH_KEY_LOADER", None)
        app.config.setdefault("SIMPLE_AUTH_ERROR_MESSAGE", "Invalid or missing API key")
        app.config.setdefault("SIMPLE_AUTH_ERROR_STATUS_CODE", 401)
        
        # 存储扩展实例到app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["simple_auth"] = self
    
    def get_api_key(self) -> Optional[str]:
        """从请求中获取API key。
        
        Returns:
            获取到的API key，如果未找到则返回None
        """
        header_name = current_app.config["SIMPLE_AUTH_HEADER_NAME"]
        return request.headers.get(header_name)
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证API key是否有效。
        
        Args:
            api_key: 要验证的API key
            
        Returns:
            如果API key有效返回True，否则返回False
        """
        # 优先使用自定义key_loader
        key_loader = current_app.config["SIMPLE_AUTH_KEY_LOADER"]
        if key_loader and callable(key_loader):
            return bool(key_loader(api_key))
        
        # 使用静态keys验证
        static_keys = current_app.config["SIMPLE_AUTH_STATIC_KEYS"]
        if isinstance(static_keys, (set, list, tuple)):
            return api_key in static_keys
        
        return False
    
    def authenticate_request(self) -> bool:
        """验证当前请求的API key。
        
        Returns:
            如果验证通过返回True，否则返回False
        """
        api_key = self.get_api_key()
        if not api_key:
            return False
        
        return self.validate_api_key(api_key)