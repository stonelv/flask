"""
Decorators for Flask-Simple-Auth.
"""

from functools import wraps
from flask import current_app, abort, g
from typing import Callable, Optional
from .extension import SimpleAuth


def require_api_key(auth: Optional[SimpleAuth] = None):
    """
    装饰器：要求API key验证。
    
    Args:
        auth: SimpleAuth实例，如果不提供则从当前app的extensions中获取
        
    Returns:
        装饰器函数
        
    Example:
        @app.route('/api/data')
        @require_api_key()
        def get_data():
            return jsonify({"data": "secret"})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取auth实例
            if auth is None:
                auth_instance = current_app.extensions.get("simple_auth")
                if not auth_instance:
                    abort(500, "SimpleAuth extension not initialized")
            else:
                auth_instance = auth
            
            # 验证API key
            if not auth_instance.authenticate_request():
                error_message = current_app.config.get(
                    "SIMPLE_AUTH_ERROR_MESSAGE", 
                    "Invalid or missing API key"
                )
                error_status = current_app.config.get(
                    "SIMPLE_AUTH_ERROR_STATUS_CODE", 
                    401
                )
                abort(error_status, error_message)
            
            # 存储验证结果到g对象，方便后续使用
            g.api_key_authenticated = True
            g.api_key = auth_instance.get_api_key()
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator