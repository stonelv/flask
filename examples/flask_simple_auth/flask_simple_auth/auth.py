"""
Flask Simple Auth 核心模块
提供 API key 验证功能
"""

from functools import wraps
from typing import Callable, List, Optional, Union, Dict, Any

from flask import current_app, request, jsonify, make_response


class SimpleAuth:
    """SimpleAuth 扩展类，处理 API key 验证"""
    
    def __init__(self, app=None):
        """初始化 SimpleAuth 扩展
        
        Args:
            app: Flask 应用实例，可选
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化 Flask 应用
        
        Args:
            app: Flask 应用实例
        """
        # 设置默认配置
        app.config.setdefault('SIMPLE_AUTH_HEADER_NAME', 'X-API-Key')
        app.config.setdefault('SIMPLE_AUTH_KEYS', [])
        app.config.setdefault('SIMPLE_AUTH_REALM', 'Protected Area')
        app.config.setdefault('SIMPLE_AUTH_ERROR_MESSAGE', 'Invalid or missing API key')
        
        # 注册扩展到应用
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['simple_auth'] = self
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证 API key 是否有效
        
        Args:
            api_key: 要验证的 API key
            
        Returns:
            bool: API key 是否有效
        """
        # 如果配置了 key_loader 函数，使用它进行验证
        key_loader = current_app.config.get('SIMPLE_AUTH_KEY_LOADER')
        if key_loader and callable(key_loader):
            return key_loader(api_key)
        
        # 否则使用静态 keys 列表进行验证
        valid_keys = current_app.config.get('SIMPLE_AUTH_KEYS', [])
        return api_key in valid_keys
    
    def get_api_key_from_request(self) -> Optional[str]:
        """从请求中提取 API key
        
        Returns:
            Optional[str]: 提取到的 API key，如果没有则返回 None
        """
        # 从指定的 header 中获取 API key
        header_name = current_app.config.get('SIMPLE_AUTH_HEADER_NAME', 'X-API-Key')
        api_key = request.headers.get(header_name)
        
        if api_key:
            return api_key
        
        # 也可以从查询参数中获取 API key
        api_key = request.args.get('api_key')
        if api_key:
            return api_key
            
        return None
    
    def unauthorized(self) -> Any:
        """返回未授权响应
        
        Returns:
            Any: 未授权响应
        """
        error_message = current_app.config.get('SIMPLE_AUTH_ERROR_MESSAGE', 'Invalid or missing API key')
        response = make_response(jsonify({'error': error_message}), 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{current_app.config.get("SIMPLE_AUTH_REALM", "Protected Area")}"'
        return response


def require_api_key(f: Callable = None, *, optional: bool = False) -> Callable:
    """API key 验证装饰器
    
    Args:
        f: 要装饰的函数
        optional: 是否为可选验证，如果为 True，则 API key 不存在时也会继续执行
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def decorated_function(*args, **kwargs):
            # 获取 SimpleAuth 扩展实例
            simple_auth = current_app.extensions.get('simple_auth')
            if not simple_auth:
                # 如果扩展未初始化，直接执行函数
                return func(*args, **kwargs)
            
            # 从请求中提取 API key
            api_key = simple_auth.get_api_key_from_request()
            
            # 如果没有提供 API key
            if not api_key:
                if optional:
                    # 如果是可选验证，则继续执行函数
                    return func(*args, **kwargs)
                else:
                    # 否则返回未授权响应
                    return simple_auth.unauthorized()
            
            # 验证 API key
            if simple_auth.verify_api_key(api_key):
                # 验证通过，执行函数
                return func(*args, **kwargs)
            else:
                # 验证失败，返回未授权响应
                return simple_auth.unauthorized()
        
        return decorated_function
    
    # 支持带参数和不带参数的装饰器调用方式
    if f is None:
        return decorator
    else:
        return decorator(f)