"""Structured logging integration for Flask.

This module provides structured JSON logging with automatic injection of
trace context (trace_id, span_id) and request_id for log correlation.
"""

from __future__ import annotations

import json
import logging
import typing as t
from datetime import datetime
from datetime import timezone

if t.TYPE_CHECKING:
    from flask import Flask


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter with trace context injection.

    Outputs logs in JSON format with the following fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name
    - message: Log message
    - trace_id: OpenTelemetry trace ID (if tracing is enabled)
    - span_id: OpenTelemetry span ID (if tracing is enabled)
    - request_id: X-Request-ID (if request_id is enabled)
    - exception: Exception info (if present)
    """

    def __init__(self, tracing_enabled: bool = True) -> None:
        """Initialize the structured formatter.

        Args:
            tracing_enabled: Whether to inject trace context fields.
        """
        super().__init__()
        self.tracing_enabled = tracing_enabled

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON string with structured log fields.
        """
        log_entry: dict[str, t.Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add trace context if tracing is enabled
        if self.tracing_enabled:
            try:
                from opentelemetry import trace

                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    ctx = span.get_span_context()
                    log_entry["trace_id"] = format(ctx.trace_id, "032x")
                    log_entry["span_id"] = format(ctx.span_id, "016x")
            except ImportError:
                pass

        # Add request ID if available
        try:
            from ._request_id import get_request_id

            request_id = get_request_id()
            if request_id:
                log_entry["request_id"] = request_id
        except (ImportError, RuntimeError):
            pass

        # Add any extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def init_structured_logging(app: Flask, tracing_enabled: bool) -> None:
    """Initialize structured JSON logging for a Flask application.

    Args:
        app: The Flask application instance.
        tracing_enabled: Whether tracing is enabled (for trace context injection).
    """
    # Create structured formatter
    formatter = StructuredFormatter(tracing_enabled=tracing_enabled)

    # Configure the app's logger
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Remove existing handlers and add the structured handler
    app.logger.handlers.clear()
    app.logger.addHandler(handler)

    # Store in app extensions
    app.extensions["observability"]["structured_logger"] = {
        "formatter": formatter,
        "handler": handler,
    }
