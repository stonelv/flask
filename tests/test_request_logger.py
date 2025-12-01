import logging
import json
from unittest.mock import patch, MagicMock
import pytest
from flask import Flask
from flask.request_logger import RequestLogger, JSONFormatter


@pytest.fixture
def app():
    """Create a Flask app fixture."""
    app = Flask(__name__)
    app.testing = True
    return app


@pytest.fixture
def client(app):
    """Create a test client fixture."""
    return app.test_client()


def test_extension_disabled(app, client):
    """Test that the extension is disabled when REQUEST_LOGGER_ENABLED is False."""
    app.config["REQUEST_LOGGER_ENABLED"] = False
    RequestLogger(app)
    
    response = client.get("/")
    
    # Check that X-Request-ID header is not present
    assert "X-Request-ID" not in response.headers


def test_request_id_header(app, client):
    """Test that X-Request-ID header is injected into responses."""
    RequestLogger(app)
    
    response = client.get("/")
    
    # Check that X-Request-ID header is present
    assert "X-Request-ID" in response.headers
    
    # Check that Request ID is a valid UUIDv4
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36
    assert request_id.count("-") == 4


def test_custom_header_name(app, client):
    """Test that custom header name is respected."""
    app.config["REQUEST_LOGGER_HEADER_NAME"] = "X-Correlation-ID"
    RequestLogger(app)
    
    response = client.get("/")
    
    # Check that custom header is present
    assert "X-Correlation-ID" in response.headers
    assert "X-Request-ID" not in response.headers


def test_json_logging(app, client):
    """Test that JSON logs are generated correctly."""
    app.config["REQUEST_LOGGER_LOG_JSON"] = True
    
    # Patch the JSONFormatter to capture JSON output
    with patch.object(JSONFormatter, "format") as mock_format:
        mock_format.return_value = '{"request_id": "test-id", "method": "GET", "path": "/", "status": 404, "duration_ms": 100, "remote_addr": "127.0.0.1"}'
        
        # Create logger instance
        logger = RequestLogger(app)
        
        # Make a request
        response = client.get("/")
        
        # Check that format was called
        assert mock_format.called
        
        # Check that the formatter received a log record with the correct fields
        log_record = mock_format.call_args[0][0]
        assert hasattr(log_record, "request_id")
        assert hasattr(log_record, "method")
        assert hasattr(log_record, "path")
        assert hasattr(log_record, "status")
        assert hasattr(log_record, "duration_ms")
        assert hasattr(log_record, "remote_addr")
        assert log_record.method == "GET"
        assert log_record.path == "/"
        assert log_record.status == 404  # Default Flask 404 for root


def test_plain_text_logging(app, client):
    """Test that plain text logs are generated correctly when JSON is disabled."""
    app.config["REQUEST_LOGGER_LOG_JSON"] = False
    
    # Patch the logging.Formatter to capture plain text output
    with patch.object(logging.Formatter, "format") as mock_format:
        mock_format.return_value = "2023-01-01 12:00:00,000 INFO test-id GET / 404 100ms"
        
        # Create logger instance
        logger = RequestLogger(app)
        
        # Make a request
        response = client.get("/")
        
        # Check that format was called
        assert mock_format.called
        
        # Check that the formatter received a log record with the correct fields
        log_record = mock_format.call_args[0][0]
        assert hasattr(log_record, "request_id")
        assert hasattr(log_record, "method")
        assert hasattr(log_record, "path")
        assert hasattr(log_record, "status")
        assert hasattr(log_record, "duration_ms")
        assert hasattr(log_record, "remote_addr")
        assert log_record.method == "GET"
        assert log_record.path == "/"
        assert log_record.status == 404  # Default Flask 404 for root


def test_log_level_config(app, client):
    """Test that log level configuration is respected."""
    app.config["REQUEST_LOGGER_LOG_LEVEL"] = "DEBUG"
    
    # Patch the logger to check level
    with patch.object(logging.Logger, "setLevel") as mock_set_level:
        RequestLogger(app)
        
        # Check that logger level was set to DEBUG
        mock_set_level.assert_called_once_with(logging.DEBUG)


def test_log_file_config(app, client):
    """Test that log file configuration is respected."""
    # Use a temporary file path that will work on Windows and Unix
    import tempfile
    import os
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file_path = os.path.join(temp_dir, "test_request_logger.log")
        
        app.config["REQUEST_LOGGER_LOG_FILE"] = log_file_path

        # Create logger instance
        logger = RequestLogger(app)

        # Check that logger has a FileHandler
        has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in logger.logger.handlers)
        assert has_file_handler, "Logger should have a FileHandler when REQUEST_LOGGER_LOG_FILE is set"

        # Check that FileHandler has the correct path
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                assert handler.baseFilename == log_file_path, f"FileHandler should use path {log_file_path}, but got {handler.baseFilename}"
        
        # Close the FileHandler to release the file lock
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                logger.logger.removeHandler(handler)


def test_request_id_consistency(app, client):
    """Test that request_id in flask.g matches the one in response headers."""
    # Add a route that returns the request_id from flask.g
    @app.route('/test_request_id')
    def test_request_id_route():
        from flask import g
        return {'request_id': g.request_id}
    
    # Initialize the logger
    RequestLogger(app)
    
    # Make a request
    response = client.get('/test_request_id')
    
    # Check that response is successful
    assert response.status_code == 200
    
    # Get request_id from response header and body
    header_request_id = response.headers['X-Request-ID']
    body_request_id = response.json['request_id']
    
    # Check that they are equal
    assert header_request_id == body_request_id


def test_json_log_fields(app, client, caplog):
    """Test that JSON logs contain all required fields with correct types."""
    # Configure to use JSON logging
    app.config['REQUEST_LOGGER_LOG_JSON'] = True
    app.config['REQUEST_LOGGER_LOG_LEVEL'] = 'INFO'  # Ensure INFO level is enabled
    
    # Clear existing handlers and add JSON formatter to caplog
    logger = logging.getLogger("flask.request_logger")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    
    # Initialize the RequestLogger extension
    request_logger = RequestLogger(app)
    
    # Make a request
    with caplog.at_level(logging.INFO):
        response = client.get('/')
    
    # Get the log output
    assert len(caplog.records) > 0, "No log records captured"
    log_record = caplog.records[0]
    
    # Format the log record using the JSON formatter
    formatter = JSONFormatter()
    log_output = formatter.format(log_record)
    
    # Parse JSON log
    log_json = json.loads(log_output.strip())
    
    # Check that all required fields are present and have correct types
    required_fields = [
        ('timestamp', str),
        ('level', str),
        ('message', str),
        ('request_id', str),
        ('method', str),
        ('path', str),
        ('status', int),
        ('duration_ms', int),
        ('remote_addr', str)
    ]
    
    for field_name, field_type in required_fields:
        assert field_name in log_json, f"Missing required field: {field_name}"
        assert isinstance(log_json[field_name], field_type), f"Field {field_name} should be of type {field_type}, got {type(log_json[field_name])}"
    
    # Check specific field values
    assert log_json['method'] == 'GET'
    assert log_json['path'] == '/'
    assert log_json['status'] == 404
    assert log_json['remote_addr'] == '127.0.0.1' or log_json['remote_addr'] == '::1'  # IPv4 or IPv6 loopback
