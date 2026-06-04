"""
Flask Simple Auth
=================

一个简单的 Flask 扩展，用于 API key 验证。
"""

try:
    # 尝试使用相对导入
    from .auth import SimpleAuth, require_api_key
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from flask_simple_auth.auth import SimpleAuth, require_api_key

__version__ = "1.0.0"
__all__ = ["SimpleAuth", "require_api_key"]