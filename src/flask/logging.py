from __future__ import annotations

import json
import logging
import sys
import time
import typing as t
import uuid
from datetime import datetime

from werkzeug.local import LocalProxy

from .globals import g
from .globals import request

if t.TYPE_CHECKING:  # pragma: no cover
    from .sansio.app import App


@LocalProxy
def wsgi_errors_stream() -> t.TextIO:
    """Find the most appropriate error stream for the application. If a request
    is active, log to ``wsgi.errors``, otherwise use ``sys.stderr``.

    If you configure your own :class:`logging.StreamHandler`, you may want to
    use this for the stream. If you are using file or dict configuration and
    can't import this directly, you can refer to it as
    ``ext://flask.logging.wsgi_errors_stream``.
    """
    if request:
        return request.environ["wsgi.errors"]  # type: ignore[no-any-return]

    return sys.stderr


def has_level_handler(logger: logging.Logger) -> bool:
    """Check if there is a handler in the logging chain that will handle the
    given logger's :meth:`effective level <~logging.Logger.getEffectiveLevel>`.
    """
    level = logger.getEffectiveLevel()
    current = logger

    while current:
        if any(handler.level <= level for handler in current.handlers):
            return True

        if not current.propagate:
            break

        current = current.parent  # type: ignore

    return False


#: Log messages to :func:`~flask.logging.wsgi_errors_stream` with the format
#: ``[%(asctime)s] %(levelname)s in %(module)s: %(message)s``.
default_handler = logging.StreamHandler(wsgi_errors_stream)  # type: ignore
default_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
)


def generate_request_id() -> str:
    """Generate a unique request ID using UUID4.

    :return: A unique string identifier for the request.
    """
    return uuid.uuid4().hex


def get_request_id() -> str | None:
    """Get the current request ID from the request context.

    :return: The request ID if available, otherwise None.
    """
    return g.get("request_id")


def set_request_id(request_id: str | None = None) -> str:
    """Set the request ID for the current request context.

    :param request_id: Optional request ID to use. If not provided, a new one will be generated.
    :return: The request ID that was set.
    """
    if request_id is None:
        request_id = generate_request_id()
    g.request_id = request_id
    return request_id


def set_request_start_time() -> float:
    """Set the start time for the current request.

    :return: The start time in seconds since the epoch.
    """
    start_time = time.time()
    g.request_start_time = start_time
    return start_time


def get_request_duration() -> float | None:
    """Get the duration of the current request.

    :return: The duration in seconds, or None if the start time is not set.
    """
    start_time = g.get("request_start_time")
    if start_time is None:
        return None
    return time.time() - start_time


class StructuredFormatter(logging.Formatter):
    """A structured log formatter that outputs JSON logs with request context.

    This formatter includes standard log fields along with request-specific
    information when available, such as request_id, method, path, status code,
    and duration.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string with structured fields.

        :param record: The log record to format.
        :return: A JSON string representing the structured log entry.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_info"):
            log_data["request_info"] = record.request_info

        return json.dumps(log_data, ensure_ascii=False)


def create_logger(app: App) -> logging.Logger:
    """Get the Flask app's logger and configure it if needed.

    The logger name will be the same as
    :attr:`app.import_name <flask.Flask.name>`.

    When :attr:`~flask.Flask.debug` is enabled, set the logger level to
    :data:`logging.DEBUG` if it is not set.

    If there is no handler for the logger's effective level, add a
    :class:`~logging.StreamHandler` for
    :func:`~flask.logging.wsgi_errors_stream` with a basic format.
    """
    logger = logging.getLogger(app.name)

    if app.debug and not logger.level:
        logger.setLevel(logging.DEBUG)

    if not has_level_handler(logger):
        logger.addHandler(default_handler)

    return logger
