import logging
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import Flask, request, g, current_app


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: Log record object.

        Returns:
            JSON formatted log string.
        """
        # Extract standard log fields
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "remote_addr"):
            log_data["remote_addr"] = record.remote_addr
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ("message", "asctime", "levelname", "levelno", "pathname",
                         "filename", "module", "lineno", "funcName", "created", "msecs",
                         "relativeCreated", "thread", "threadName", "process", "processName",
                         "args", "exc_info", "exc_text", "stack_info", "request_id",
                         "method", "path", "status", "duration_ms", "remote_addr"):
                log_data[key] = value
        
        return json.dumps(log_data)


class RequestLogger:
    """Flask extension for structured JSON access logging and Request ID support.

    This extension adds:
    1. Unique Request ID to each request (UUIDv4)
    2. Injection of Request ID into response headers
    3. Structured JSON logging of request/response data

    Configuration options:
    - REQUEST_LOGGER_ENABLED: Enable/disable the extension (default: True)
    - REQUEST_LOGGER_HEADER_NAME: Name of the response header with Request ID (default: "X-Request-ID")
    - REQUEST_LOGGER_LOG_JSON: Enable/disable JSON formatting of logs (default: True)
    - REQUEST_LOGGER_LOG_FILE: Path to log file (default: None, uses stdout)
    - REQUEST_LOGGER_LOG_LEVEL: Logging level (default: "INFO")
    """


def init_request_logger(app: Flask, config: Optional[Dict[str, Any]] = None) -> RequestLogger:
    """Initialize the RequestLogger extension with a Flask application.

    This is a convenience function that creates a RequestLogger instance
    and initializes it with the given app and config.

    Args:
        app: Flask application instance.
        config: Optional configuration dictionary to override app.config.

    Returns:
        RequestLogger instance.
    """
    logger = RequestLogger()
    logger.init_app(app, config)
    return logger


class RequestLogger:
    """Flask extension for structured JSON access logging and Request ID support.

    This extension adds:
    1. Unique Request ID to each request (UUIDv4)
    2. Injection of Request ID into response headers
    3. Structured JSON logging of request/response data

    Configuration options:
    - REQUEST_LOGGER_ENABLED: Enable/disable the extension (default: True)
    - REQUEST_LOGGER_HEADER_NAME: Name of the response header with Request ID (default: "X-Request-ID")
    - REQUEST_LOGGER_LOG_JSON: Enable/disable JSON formatting of logs (default: True)
    - REQUEST_LOGGER_LOG_FILE: Path to log file (default: None, uses stdout)
    - REQUEST_LOGGER_LOG_LEVEL: Logging level (default: "INFO")
    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        """Initialize the extension.

        Args:
            app: Flask application instance. If provided, the extension will be
                 initialized immediately. Otherwise, use init_app() later.
        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the extension with a Flask application.

        Args:
            app: Flask application instance.
            config: Optional configuration dictionary to override app.config.
        """
        # Merge configuration
        if config is None:
            config = {}
        
        # Set default configuration
        app.config.setdefault("REQUEST_LOGGER_ENABLED", True)
        app.config.setdefault("REQUEST_LOGGER_HEADER_NAME", "X-Request-ID")
        app.config.setdefault("REQUEST_LOGGER_LOG_JSON", True)
        app.config.setdefault("REQUEST_LOGGER_LOG_FILE", None)
        app.config.setdefault("REQUEST_LOGGER_LOG_LEVEL", "INFO")
        
        # Override with provided config
        for key, value in config.items():
            if key.startswith("REQUEST_LOGGER_"):
                app.config[key] = value
        
        # Check if extension is enabled
        if not app.config["REQUEST_LOGGER_ENABLED"]:
            return
        
        # Create logger
        self.logger = logging.getLogger("flask.request_logger")
        # Convert log level string to logging constant
        log_level = app.config["REQUEST_LOGGER_LOG_LEVEL"]
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Configure handler
        if app.config["REQUEST_LOGGER_LOG_FILE"]:
            handler = logging.FileHandler(app.config["REQUEST_LOGGER_LOG_FILE"])
        else:
            handler = logging.StreamHandler()
        
        # Configure formatter
        if app.config["REQUEST_LOGGER_LOG_JSON"]:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(request_id)s %(method)s %(path)s %(status)s %(duration_ms)dms"
            )
        
        handler.setFormatter(formatter)
        
        # Check if handler already exists to prevent duplicates
        handler_exists = False
        for existing_handler in self.logger.handlers:
            if isinstance(existing_handler, type(handler)):
                if app.config["REQUEST_LOGGER_LOG_FILE"]:
                    if hasattr(existing_handler, 'baseFilename') and existing_handler.baseFilename == app.config["REQUEST_LOGGER_LOG_FILE"]:
                        handler_exists = True
                        break
                else:
                    handler_exists = True
                    break
        
        if not handler_exists:
            self.logger.addHandler(handler)
        
        # Store extension in app.extensions
        if "request_logger" not in app.extensions:
            app.extensions["request_logger"] = self
        
        # Register before_request and after_request hooks
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self) -> None:
        """Before request hook to generate Request ID and start timer."""
        # Generate unique Request ID
        g.request_id = str(uuid.uuid4())
        # Start timer for duration calculation
        g.start_time = time.time()

    def _after_request(self, response) -> None:
        """After request hook to log request/response data."""
        # Calculate duration in milliseconds
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        # Get request data
        request_id = g.get("request_id", "unknown")
        method = request.method
        path = request.path
        status = response.status_code
        remote_addr = request.remote_addr or "unknown"
        
        # Prepare log data
        log_data = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
            "remote_addr": remote_addr,
        }
        
        # Log the data
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info("Request completed", extra=log_data)
        
        # Add Request ID to response header
        header_name = request.environ.get(
            "flask.request_logger.header_name",
            current_app.config["REQUEST_LOGGER_HEADER_NAME"]
        )
        response.headers[header_name] = request_id
        
        return response
