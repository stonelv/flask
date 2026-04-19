import json
import logging
import sys
from io import StringIO

import pytest

from flask.logging import default_handler
from flask.logging import has_level_handler
from flask.logging import StructuredFormatter
from flask.logging import wsgi_errors_stream


@pytest.fixture(autouse=True)
def reset_logging(pytestconfig):
    root_handlers = logging.root.handlers[:]
    logging.root.handlers = []
    root_level = logging.root.level

    logger = logging.getLogger("flask_test")
    logger.handlers = []
    logger.setLevel(logging.NOTSET)

    logging_plugin = pytestconfig.pluginmanager.unregister(name="logging-plugin")

    yield

    logging.root.handlers[:] = root_handlers
    logging.root.setLevel(root_level)

    logger.handlers = []
    logger.setLevel(logging.NOTSET)

    if logging_plugin:
        pytestconfig.pluginmanager.register(logging_plugin, "logging-plugin")


def test_logger(app):
    assert app.logger.name == "flask_test"
    assert app.logger.level == logging.NOTSET
    assert app.logger.handlers == [default_handler]


def test_logger_debug(app):
    app.debug = True
    assert app.logger.level == logging.DEBUG
    assert app.logger.handlers == [default_handler]


def test_existing_handler(app):
    logging.root.addHandler(logging.StreamHandler())
    assert app.logger.level == logging.NOTSET
    assert not app.logger.handlers


def test_wsgi_errors_stream(app, client):
    @app.route("/")
    def index():
        app.logger.error("test")
        return ""

    stream = StringIO()
    client.get("/", errors_stream=stream)
    assert "ERROR in test_logging: test" in stream.getvalue()

    assert wsgi_errors_stream._get_current_object() is sys.stderr

    with app.test_request_context(errors_stream=stream):
        assert wsgi_errors_stream._get_current_object() is stream


def test_has_level_handler():
    logger = logging.getLogger("flask.app")
    assert not has_level_handler(logger)

    handler = logging.StreamHandler()
    logging.root.addHandler(handler)
    assert has_level_handler(logger)

    logger.propagate = False
    assert not has_level_handler(logger)
    logger.propagate = True

    handler.setLevel(logging.ERROR)
    assert not has_level_handler(logger)


def test_log_view_exception(app, client):
    @app.route("/")
    def index():
        raise Exception("test")

    app.testing = False
    stream = StringIO()
    rv = client.get("/", errors_stream=stream)
    assert rv.status_code == 500
    assert rv.data
    err = stream.getvalue()
    assert "Exception on / [GET]" in err
    assert "Exception: test" in err


def test_structured_formatter_output_structure():
    """Test that StructuredFormatter outputs JSON with correct structure."""
    formatter = StructuredFormatter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=None,
        exc_info=None,
    )
    record.funcName = "test_function"
    record.module = "test_module"
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert "timestamp" in log_data, "JSON should contain 'timestamp' field"
    assert "level" in log_data, "JSON should contain 'level' field"
    assert "message" in log_data, "JSON should contain 'message' field"
    assert "module" in log_data, "JSON should contain 'module' field"
    assert "function" in log_data, "JSON should contain 'function' field"
    assert "line" in log_data, "JSON should contain 'line' field"
    
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["module"] == "test_module"
    assert log_data["function"] == "test_function"
    assert log_data["line"] == 10


def test_structured_formatter_request_info_nested():
    """Test that request_info is kept as a nested dict, not flattened."""
    formatter = StructuredFormatter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Request completed",
        args=None,
        exc_info=None,
    )
    record.funcName = "log_request_completion"
    record.module = "app"
    
    record.request_info = {
        "method": "GET",
        "path": "/api/data",
        "status_code": 200,
        "duration_ms": 45.23,
        "request_id": "a1b2c3d4e5f67890abcdef123456789",
    }
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert "request_info" in log_data, "JSON should contain 'request_info' field"
    assert isinstance(log_data["request_info"], dict), "request_info should be a dict"
    
    assert "method" in log_data["request_info"], "request_info should contain 'method'"
    assert "path" in log_data["request_info"], "request_info should contain 'path'"
    assert "status_code" in log_data["request_info"], "request_info should contain 'status_code'"
    
    assert log_data["request_info"]["method"] == "GET"
    assert log_data["request_info"]["path"] == "/api/data"
    assert log_data["request_info"]["status_code"] == 200
    assert log_data["request_info"]["duration_ms"] == 45.23
    assert log_data["request_info"]["request_id"] == "a1b2c3d4e5f67890abcdef123456789"
    
    assert "method" not in log_data, "'method' should not be at top level"
    assert "path" not in log_data, "'path' should not be at top level"
    assert "status_code" not in log_data, "'status_code' should not be at top level"
    assert "duration_ms" not in log_data, "'duration_ms' should not be at top level"


def test_structured_formatter_with_exc_info():
    """Test that exc_info results in 'exception' field in JSON output."""
    formatter = StructuredFormatter()
    
    try:
        raise ValueError("Test exception message")
    except ValueError:
        exc_info = sys.exc_info()
    
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="An error occurred",
        args=None,
        exc_info=exc_info,
    )
    record.funcName = "test_function"
    record.module = "test_module"
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert "exception" in log_data, "JSON should contain 'exception' field when exc_info is provided"
    assert isinstance(log_data["exception"], str), "'exception' should be a string"
    
    assert "Test exception message" in log_data["exception"], "Exception message should be in exception field"
    assert "ValueError" in log_data["exception"], "Exception type should be in exception field"
    
    assert log_data["level"] == "ERROR"
    assert log_data["message"] == "An error occurred"


def test_structured_formatter_with_request_info_and_exception():
    """Test that both request_info and exception are included correctly."""
    formatter = StructuredFormatter()
    
    try:
        raise ValueError("Test exception in request")
    except ValueError:
        exc_info = sys.exc_info()
    
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="Request failed",
        args=None,
        exc_info=exc_info,
    )
    record.funcName = "log_exception"
    record.module = "app"
    
    record.request_info = {
        "method": "GET",
        "path": "/api/error",
        "request_id": "test-request-id-123",
    }
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert "timestamp" in log_data
    assert "level" in log_data
    assert "message" in log_data
    assert "request_info" in log_data
    assert "exception" in log_data
    
    assert log_data["request_info"]["method"] == "GET"
    assert log_data["request_info"]["path"] == "/api/error"
    assert log_data["request_info"]["request_id"] == "test-request-id-123"
    
    assert "Test exception in request" in log_data["exception"]
    
    assert "method" not in log_data
    assert "path" not in log_data


def test_structured_logging_in_flask_app():
    """Test structured logging in a real Flask application context."""
    from flask import Flask
    from flask.logging import get_request_id
    
    app = Flask(__name__)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(StructuredFormatter())
    
    from flask.logging import default_handler
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    @app.route("/test")
    def test_route():
        request_id = get_request_id()
        app.logger.info(f"Processing request: {request_id}")
        return "OK"
    
    client = app.test_client()
    response = client.get("/test")
    assert response.status_code == 200
    
    log_output = log_stream.getvalue()
    log_lines = [line for line in log_output.strip().split("\n") if line]
    
    assert len(log_lines) >= 2, "Should have at least 2 log entries"
    
    for line in log_lines:
        log_data = json.loads(line)
        
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "message" in log_data
        assert "request_id" in log_data
        
        if "request_info" in log_data:
            assert isinstance(log_data["request_info"], dict)
            assert "method" in log_data["request_info"]
            assert "path" in log_data["request_info"]
            assert "status_code" in log_data["request_info"]
            
            assert "method" not in log_data
            assert "path" not in log_data
            assert "status_code" not in log_data


def test_structured_logging_exception_in_flask_app():
    """Test that exceptions in Flask app are logged with correct structure."""
    from flask import Flask
    
    app = Flask(__name__)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(StructuredFormatter())
    
    from flask.logging import default_handler
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    @app.route("/error")
    def error_route():
        raise ValueError("Test exception in Flask route")
    
    client = app.test_client()
    app.testing = False
    response = client.get("/error")
    assert response.status_code == 500
    
    log_output = log_stream.getvalue()
    log_lines = [line for line in log_output.strip().split("\n") if line]
    
    found_exception_log = False
    for line in log_lines:
        log_data = json.loads(line)
        
        if log_data.get("level") == "ERROR" and "exception" in log_data:
            found_exception_log = True
            
            assert "request_id" in log_data
            assert "request_info" in log_data
            assert isinstance(log_data["request_info"], dict)
            assert "method" in log_data["request_info"]
            assert "path" in log_data["request_info"]
            
            assert "method" not in log_data
            assert "path" not in log_data
            
            assert "Test exception in Flask route" in log_data["exception"]
    
    assert found_exception_log, "Should have found an exception log entry"
