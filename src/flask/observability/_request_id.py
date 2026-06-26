"""Request ID generation and propagation for Flask.

This module provides automatic X-Request-ID header generation for request
correlation across distributed systems.
"""

from __future__ import annotations

import contextvars
import typing as t
import uuid

if t.TYPE_CHECKING:
    from flask import Flask

# Context variable to store the current request ID
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Get the current request ID from the context.

    Returns:
        The current request ID string, or None if not in a request context.

    Example:
        >>> from flask.observability import get_request_id
        >>> request_id = get_request_id()
        >>> print(request_id)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    return _request_id_var.get()


def init_request_id(app: Flask) -> None:
    """Initialize request ID generation for a Flask application.

    Args:
        app: The Flask application instance.
    """
    # Connect to Flask signals
    from flask import signals

    @signals.request_started.connect_via(app)
    def on_request_started(sender: t.Any, **kwargs: t.Any) -> None:
        """Generate or extract request ID at request start."""
        from flask import request

        # Check for incoming X-Request-ID header (from upstream service)
        incoming_id = request.headers.get("X-Request-ID")

        if incoming_id:
            # Use the incoming ID for distributed tracing correlation
            request_id = incoming_id
        else:
            # Generate a new UUID4 request ID
            request_id = str(uuid.uuid4())

        # Store in context variable
        _request_id_var.set(request_id)

        # Also store on the request object for easy access
        request._request_id = request_id  # type: ignore[attr-defined]

    @signals.request_finished.connect_via(app)
    def on_request_finished(sender: t.Any, **kwargs: t.Any) -> None:
        """Add X-Request-ID header to response."""
        from flask import request

        response = kwargs.get("response")
        request_id = getattr(request, "_request_id", None)

        if response and request_id:
            # Add X-Request-ID header to response
            response.headers["X-Request-ID"] = request_id

    @signals.request_tearing_down.connect_via(app)
    def on_request_tearing_down(sender: t.Any, **kwargs: t.Any) -> None:
        """Clean up request ID context."""
        # Reset the context variable
        _request_id_var.set(None)
