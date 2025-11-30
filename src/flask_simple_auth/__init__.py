"""Flask Simple Auth Extension

Provides API key verification for Flask applications with:
- Configurable header for API key retrieval
- Support for static API keys or dynamic key loading via callback
- @require_api_key decorator for protecting routes
"""

from flask import request, current_app
from functools import wraps

__version__ = '0.1.0'
__author__ = 'Your Name'


class SimpleAuth:
    """Simple API key authentication extension for Flask

    This extension provides a decorator to protect routes with API key
    verification. It supports both static API keys configured in the app
    settings and dynamic key loading via a callback function.
    """

    def __init__(self, app=None):
        """Initialize the extension

        :param app: Flask application instance (optional)
        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the extension with a Flask application

        :param app: Flask application instance
        """
        # Configure default settings
        app.config.setdefault('SIMPLE_AUTH_API_KEY_HEADER', 'X-API-KEY')
        app.config.setdefault('SIMPLE_AUTH_API_KEYS', None)

        # Store the extension instance in the app's extensions dict
        if 'simple_auth' not in app.extensions:
            app.extensions['simple_auth'] = self

    def require_api_key(self, f=None):
        """Decorator to protect routes with API key verification

        This decorator checks for a valid API key in the configured header.
        The API key can be validated against static keys or via a custom
        key loader function.

        :param f: Route function to decorate
        :return: Decorated function
        """
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                # Get the API key from the configured header
                header_name = current_app.config.get('SIMPLE_AUTH_API_KEY_HEADER')
                api_key = request.headers.get(header_name)

                if not api_key:
                    return {'error': 'API key is missing'}, 401

                # Validate the API key
                if not self._validate_api_key(api_key):
                    return {'error': 'Invalid API key'}, 403

                # API key is valid, proceed to the route
                return func(*args, **kwargs)
            return decorated_function

        if f:
            return decorator(f)
        return decorator

    def _validate_api_key(self, api_key):
        """Validate the provided API key

        This method first checks if a key_loader function is defined on
        the current_app. If not, it falls back to checking against the
        static SIMPLE_AUTH_API_KEYS list.

        :param api_key: API key to validate
        :return: True if valid, False otherwise
        """
        # Check for custom key loader function
        if hasattr(current_app, 'key_loader') and callable(current_app.key_loader):
            return current_app.key_loader(api_key)

        # Fall back to static API keys
        api_keys = current_app.config.get('SIMPLE_AUTH_API_KEYS', [])
        return api_key in api_keys


# Create a default instance of the extension
_simple_auth = SimpleAuth()
require_api_key = _simple_auth.require_api_key
init_app = _simple_auth.init_app
