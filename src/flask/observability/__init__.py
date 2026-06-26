"""Flask Observability Module.

This module provides OpenTelemetry-based observability for Flask applications,
including distributed tracing, metrics collection, request ID propagation,
and structured logging.

All functionality is opt-in and requires installing the observability extras:

    pip install Flask[observability]

Example usage:

    from flask import Flask
    from flask.observability import init_observability

    app = Flask(__name__)
    init_observability(app)
"""

from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from flask import Flask


def init_observability(
    app: Flask,
    *,
    tracing: bool = True,
    metrics: bool = True,
    request_id: bool = True,
    structured_logging: bool = False,
    service_name: str | None = None,
    exporter: str = "otlp",
) -> None:
    """Initialize observability for a Flask application.

    This function enables OpenTelemetry-based observability features for the
    given Flask application. All features are opt-in and can be enabled or
    disabled independently.

    Args:
        app: The Flask application instance.
        tracing: Enable distributed tracing (default: True).
        metrics: Enable metrics collection (default: True).
        request_id: Enable X-Request-ID header generation (default: True).
        structured_logging: Enable structured JSON logging (default: False).
        service_name: Service name for traces and metrics. Defaults to app.name.
        exporter: Exporter type - "otlp", "console", or "none" (default: "otlp").

    Note:
        This function requires the OpenTelemetry packages to be installed:
            pip install Flask[observability]

    Example:
        >>> from flask import Flask
        >>> from flask.observability import init_observability
        >>> app = Flask(__name__)
        >>> init_observability(app, exporter="console")
    """
    # Store configuration in app extensions
    app.extensions["observability"] = {
        "tracing": tracing,
        "metrics": metrics,
        "request_id": request_id,
        "structured_logging": structured_logging,
        "service_name": service_name or app.name,
        "exporter": exporter,
    }

    # Initialize each component if enabled
    if tracing:
        from ._tracing import init_tracing

        init_tracing(app, service_name or app.name, exporter)

    if metrics:
        from ._metrics import init_metrics

        init_metrics(app, service_name or app.name, exporter)

    if request_id:
        from ._request_id import init_request_id

        init_request_id(app)

    if structured_logging:
        from ._logging import init_structured_logging

        init_structured_logging(app, tracing)


__all__ = ["init_observability"]
