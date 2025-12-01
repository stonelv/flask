# Flask Request Logger Extension

A lightweight Flask extension that provides structured JSON access logging and Request ID support.

## Features

- Generates unique Request ID (UUIDv4) for each request
- Injects Request ID into response headers
- Logs request/response data in structured JSON format
- Configurable log level, format, and output destination
- Supports application factory pattern

## Installation

The extension is included in the Flask package, so no additional installation is required.

## Usage

### Basic Usage

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)

# Initialize the extension
request_logger = RequestLogger(app)

@app.route('/')
def hello():
    return 'Hello, World!'
```

### Application Factory Pattern

```python
from flask import Flask
from flask.request_logger import RequestLogger

request_logger = RequestLogger()

def create_app():
    app = Flask(__name__)
    
    # Configure the extension
    app.config['REQUEST_LOGGER_LOG_FILE'] = '/var/log/flask/app.log'
    app.config['REQUEST_LOGGER_LOG_LEVEL'] = 'DEBUG'
    
    # Initialize the extension
    request_logger.init_app(app)
    
    @app.route('/')
    def hello():
        return 'Hello, World!'
    
    return app
```

## Configuration

The extension can be configured using Flask's app.config or by passing a config dictionary to `init_app()`.

| Configuration Key                | Default Value | Description                                                                 |
|----------------------------------|---------------|-----------------------------------------------------------------------------|
| REQUEST_LOGGER_ENABLED           | True          | Enable/disable the extension                                                |
| REQUEST_LOGGER_HEADER_NAME       | X-Request-ID  | Name of the response header that will contain the Request ID                |
| REQUEST_LOGGER_LOG_JSON          | True          | Enable/disable JSON formatting of logs                                      |
| REQUEST_LOGGER_LOG_FILE          | None          | Path to log file (None uses stdout)                                         |
| REQUEST_LOGGER_LOG_LEVEL         | INFO          | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)                       |

## Log Format

### JSON Format

When `REQUEST_LOGGER_LOG_JSON` is True, logs are formatted as JSON objects with the following fields:

```json
{
  "timestamp": "2023-10-05T14:48:00.000Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/",
  "status": 200,
  "duration_ms": 100,
  "remote_addr": "127.0.0.1"
}
```

### Plain Text Format

When `REQUEST_LOGGER_LOG_JSON` is False, logs are formatted as plain text:

```
2023-10-05 14:48:00,000 INFO 550e8400-e29b-41d4-a716-446655440000 GET / 200 100ms
```

## Accessing Request ID

The Request ID can be accessed from the `flask.g` object:

```python
from flask import g

@app.route('/')
def hello():
    request_id = g.request_id
    return f'Hello, World! Your Request ID is {request_id}'
```

## Testing

To run the tests for this extension:

```bash
pytest tests/test_request_logger.py
```
