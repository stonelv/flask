"""Flask Simple Auth Extension for API Key Verification"""

from typing import Callable, List, Optional, Union
from flask import Flask, request, abort


class SimpleAuth:
    """Simple API Key authentication extension for Flask."""

    def __init__(self, app: Optional[Flask] = None):
        """Initialize the SimpleAuth extension.

        Args:
            app: The Flask application instance. If not provided,
                 you can initialize it later with init_app().
        """
        self.app = app
        self.key_loader: Optional[Callable[[str], bool]] = None
        self.api_keys: List[str] = []
        self.api_key_header: str = "X-API-Key"

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize the extension with a Flask application.

        Args:
            app: The Flask application instance.
        """
        # Set default configuration
        app.config.setdefault("SIMPLE_AUTH_API_KEYS", [])
        app.config.setdefault("SIMPLE_AUTH_API_KEY_HEADER", "X-API-Key")

        # Store the extension in the app's extensions
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["simple_auth"] = self

        # Load configuration
        self.api_keys = app.config.get("SIMPLE_AUTH_API_KEYS", [])
        self.api_key_header = app.config.get("SIMPLE_AUTH_API_KEY_HEADER", "X-API-Key")

    def key_loader_callback(self, func: Callable[[str], bool]):
        """Decorator to register a custom API key loader function.

        The loader function should take an API key string and return
        True if the key is valid, otherwise False.

        Args:
            func: The custom key loader function.

        Returns:
            The decorated function.
        """
        self.key_loader = func
        return func

    def require_api_key(self, func: Callable):
        """Decorator to protect a route with API key authentication.

        Args:
            func: The route function to protect.

        Returns:
            The decorated function.
        """
        def wrapper(*args, **kwargs):
            # Get the API key from the request header
            api_key = request.headers.get(self.api_key_header)

            if not api_key:
                abort(401, description="API key is missing")

            # Validate the API key
            if not self._validate_api_key(api_key):
                abort(403, description="Invalid API key")

            # Call the original function
            return func(*args, **kwargs)

        # Preserve the original function's name and docstring
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__

        return wrapper

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate the provided API key.

        Args:
            api_key: The API key to validate.

        Returns:
            True if the key is valid, otherwise False.
        """
        # Check if a custom key loader is registered
        if self.key_loader:
            return self.key_loader(api_key)

        # Check against static API keys
        return api_key in self.api_keys


# Create a default instance for the extension
simple_auth = SimpleAuth()


# Export the main classes and functions
__all__ = ["SimpleAuth", "simple_auth"]