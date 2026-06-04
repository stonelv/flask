"""
Flask-Simple-Auth: A simple API key authentication extension for Flask.

This extension provides easy-to-use API key authentication for Flask applications
with configurable header names, static keys, or custom key loaders.
"""

from .extension import SimpleAuth
from .decorators import require_api_key

__version__ = "1.0.0"
__all__ = ["SimpleAuth", "require_api_key"]