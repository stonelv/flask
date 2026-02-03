"""
Flask Rate Limit Module

Provides a simple in-memory rate limiting decorator for Flask routes.
No external dependencies required.

Example usage::

    from flask import Flask
    from flask import rate_limit

    app = Flask(__name__)

    @app.route('/api/data')
    @rate_limit(max_requests=10, window_seconds=60)
    def get_data():
        return {'data': 'value'}
"""

from __future__ import annotations

import time
import typing as t
from functools import wraps
from threading import Lock

from .globals import request
from .json import jsonify

if t.TYPE_CHECKING:  # pragma: no cover
    from .wrappers import Response


# Storage for rate limit records: {ip: [timestamp1, timestamp2, ...]}
_request_records: dict[str, list[float]] = {}
_records_lock = Lock()


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int = 0,
        window: int = 0,
        retry_after: int = 0,
    ):
        super().__init__(message)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


def _get_client_ip() -> str:
    """Get the client IP address from the request.
    
    Checks X-Forwarded-For header if behind a proxy.
    """
    ip = request.remote_addr or "127.0.0.1"
    
    # If behind a proxy, try to get the real client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    
    return ip


def _cleanup_expired_records(
    records: list[float], current_time: float, window_seconds: float
) -> list[float]:
    """Remove expired request records outside the time window."""
    return [ts for ts in records if current_time - ts < window_seconds]


def rate_limit(
    max_requests: int = 10,
    window_seconds: float = 60,
    key_func: t.Callable[[], str] | None = None,
    per_route: bool = True,
    error_message: str | None = None,
) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
    """Decorator to limit the rate of requests to a route.

    Uses an in-memory sliding window to track requests per IP address.
    Thread-safe for concurrent requests.

    :param max_requests: Maximum number of requests allowed in the time window.
        Default is 10.
    :param window_seconds: Time window in seconds. Default is 60 (1 minute).
    :param key_func: Optional function to generate a custom key for rate limiting.
        By default, uses the client IP address. The function should return a string.
    :param per_route: If True (default), rate limits are applied per route.
        If False, the limit is shared across all routes using the same key.
    :param error_message: Custom error message when rate limit is exceeded.
        Default is "Rate limit exceeded. Try again in {retry_after} seconds."

    :return: Decorator function that wraps the route handler.

    Example::

        @app.route('/api/data')
        @rate_limit(max_requests=10, window_seconds=60)
        def get_data():
            return jsonify({'data': 'value'})

    When the limit is exceeded, returns a 429 response with JSON body::

        {
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Try again in 45 seconds.",
            "limit": 10,
            "window": 60,
            "remaining": 0
        }

    Response headers include rate limit information::

        X-RateLimit-Limit: 10
        X-RateLimit-Remaining: 5
        X-RateLimit-Reset: 1234567890
        Retry-After: 45
    """
    def decorator(f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        @wraps(f)
        def decorated_function(*args: t.Any, **kwargs: t.Any) -> t.Any:
            # Get the key for this request
            base_key = key_func() if key_func else _get_client_ip()

            # Include route identifier in key if per_route is True
            # Use request.endpoint which includes blueprint name (e.g., "blueprint.view_func")
            # This is more reliable than f.__name__ which can have collisions
            if per_route:
                # request.endpoint is set after routing, use it if available
                # Otherwise fall back to f.__name__ (should not happen in normal Flask flow)
                route_id = request.endpoint or f.__name__
                key = f"{base_key}:{route_id}"
            else:
                key = base_key

            current_time = time.time()

            with _records_lock:
                # Initialize records for this key
                if key not in _request_records:
                    _request_records[key] = []

                # Clean up expired records
                _request_records[key] = _cleanup_expired_records(
                    _request_records[key], current_time, window_seconds
                )

                # Check if limit exceeded
                if len(_request_records[key]) >= max_requests:
                    oldest_request = min(_request_records[key])
                    reset_time = int(oldest_request + window_seconds)
                    retry_after = max(1, reset_time - int(current_time))

                    msg = error_message or f"Rate limit exceeded. Try again in {retry_after} seconds."

                    response = jsonify({
                        "error": "Too Many Requests",
                        "message": msg,
                        "limit": max_requests,
                        "window": window_seconds,
                        "remaining": 0,
                    })
                    response.status_code = 429

                    # Add standard rate limit headers
                    response.headers["X-RateLimit-Limit"] = str(max_requests)
                    response.headers["X-RateLimit-Remaining"] = "0"
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
                    response.headers["Retry-After"] = str(retry_after)

                    return response

                # Record this request
                _request_records[key].append(current_time)
                remaining = max_requests - len(_request_records[key])

            # Execute the route function
            response = f(*args, **kwargs)

            # Add rate limit headers to successful responses
            # Convert to Response if needed (e.g., for plain strings)
            if not hasattr(response, "headers"):
                from .wrappers import Response
                if isinstance(response, str):
                    response = Response(response, content_type="text/html; charset=utf-8")
                elif isinstance(response, dict):
                    response = jsonify(response)
                else:
                    response = Response(str(response), content_type="text/html; charset=utf-8")

            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(
                int(current_time + window_seconds)
            )

            return response

        return decorated_function
    return decorator


def get_rate_limit_info(key: str | None = None) -> dict[str, t.Any] | None:
    """Get current rate limit information for a key.
    
    :param key: The rate limit key (default: current request's IP)
    :return: Dictionary with rate limit info, or None if no records exist.
    
    Example return value::
    
        {
            "limit": 10,
            "used": 5,
            "remaining": 5,
            "reset_time": 1234567890.0
        }
    """
    if key is None:
        key = _get_client_ip()
    
    with _records_lock:
        if key not in _request_records or not _request_records[key]:
            return None
        
        records = _request_records[key]
        return {
            "used": len(records),
            "oldest_request": min(records),
            "newest_request": max(records),
        }


def clear_rate_limit(key: str | None = None) -> None:
    """Clear rate limit records.
    
    :param key: Specific key to clear, or None to clear all records.
    """
    with _records_lock:
        if key is None:
            _request_records.clear()
        elif key in _request_records:
            del _request_records[key]
