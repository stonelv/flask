"""Flask Simple Auth Extension

Provides API key verification for Flask applications with:
- Configurable header for API key retrieval
- Support for static API keys or dynamic key loading via callback
- @require_api_key decorator for protecting routes
- Integration with Flask's before_request for global verification
- Customizable unauthorized response handling
"""

from flask import request, current_app, g
from functools import wraps
from typing import Iterable, Callable, Optional, Dict, Any


class Unauthorized(Exception):
    """Exception raised when API key authentication fails"""
    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        super().__init__(message)

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
        self._key_loader: Optional[Callable[[str], bool | Dict[str, Any]]] = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the extension with a Flask application

        :param app: Flask application instance
        """
        # Configure default settings with new key names
        app.config.setdefault('SIMPLE_AUTH_HEADER_NAME', 'X-API-Key')
        app.config.setdefault('SIMPLE_AUTH_KEYS', None)
        app.config.setdefault('SIMPLE_AUTH_KEY_LOADER', None)
        app.config.setdefault('SIMPLE_AUTH_UNAUTHORIZED_HANDLER', None)

        # Store the extension instance in the app's extensions dict
        if 'simple_auth' not in app.extensions:
            app.extensions['simple_auth'] = self

        # Register before_request handler
        @app.before_request
        def before_request():
            self._authenticate_request()

        # Register error handler for Unauthorized exceptions
        @app.errorhandler(Unauthorized)
        def handle_unauthorized(exc: Unauthorized) -> tuple[dict, int]:
            handler = app.config.get('SIMPLE_AUTH_UNAUTHORIZED_HANDLER')
            if handler and callable(handler):
                return handler(exc)
            return {'error': 'unauthorized', 'message': str(exc)}, 401

    def require_api_key(self, allow_none: bool = False):
        """Decorator to protect routes with API key verification

        This decorator checks for a valid API key in the configured header.
        If allow_none is True, the route will be accessible even if no API
        key is provided (but invalid keys will still be rejected).

        :param allow_none: Whether to allow requests without API key (default: False)
        :return: Decorated function
        """
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                # Check if API key is required
                if not allow_none and not hasattr(g, 'current_api_key'):
                    # If we get here, before_request didn't find a valid key
                    raise Unauthorized("API key is missing or invalid")
                return func(*args, **kwargs)
            return decorated_function
        return decorator

    def _authenticate_request(self) -> None:
        """Authenticate the request by checking the API key

        This method is called before each request. It retrieves the API
        key from the configured header, validates it, and stores the
        result in flask.g.
        """
        header_name = current_app.config.get('SIMPLE_AUTH_HEADER_NAME', 'X-API-Key')
        api_key = request.headers.get(header_name)

        if not api_key:
            return  # No API key provided, let decorators handle it

        # Get key loader from config or use static keys
        key_loader = current_app.config.get('SIMPLE_AUTH_KEY_LOADER')
        static_keys = current_app.config.get('SIMPLE_AUTH_KEYS') or []

        # Validate the API key
        try:
            if key_loader and callable(key_loader):
                result = key_loader(api_key)
                if isinstance(result, dict):
                    # Store both key and metadata
                    g.current_api_key = api_key
                    g.current_api_key_meta = result
                elif result is True:
                    # Store only the key
                    g.current_api_key = api_key
                else:
                    # Invalid key
                    raise Unauthorized("Invalid API key")
            else:
                # Check against static keys
                if api_key in static_keys:
                    g.current_api_key = api_key
                else:
                    raise Unauthorized("Invalid API key")
        except Exception as e:
            # Any exception during validation is treated as unauthorized
            raise Unauthorized(str(e)) from e


# Create a default instance of the extension
_simple_auth = SimpleAuth()
require_api_key = _simple_auth.require_api_key
init_app = _simple_auth.init_app
