# Flask Simple Auth Extension

A simple API key authentication extension for Flask applications.

## Features

- Configurable header for API key retrieval
- Support for static API keys or dynamic key loading via callback
- Decorator for protecting routes with API key verification
- Easy integration with existing Flask applications

## Installation

### From Source

```bash
pip install -e .
```

## Usage

### Basic Setup

```python
from flask import Flask
from flask_simple_auth import SimpleAuth, require_api_key

app = Flask(__name__)
app.config['SIMPLE_AUTH_API_KEYS'] = ['your-secret-api-key-123']

# Initialize the extension
auth = SimpleAuth(app)

# Or use init_app for application factories
# auth = SimpleAuth()
# auth.init_app(app)

# Protect a route
@app.route('/api/data')
@require_api_key
def get_data():
    return {'data': 'This is protected data'}

if __name__ == '__main__':
    app.run()
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `SIMPLE_AUTH_API_KEY_HEADER` | `X-API-KEY` | Header name to look for the API key |
| `SIMPLE_AUTH_API_KEYS` | `None` | List of valid static API keys |

### Custom Header

You can configure a custom header for API key retrieval:

```python
app.config['SIMPLE_AUTH_API_KEY_HEADER'] = 'Authorization'
app.config['SIMPLE_AUTH_API_KEYS'] = ['Bearer your-secret-token']
```

### Dynamic Key Loading

For more advanced scenarios, you can use a dynamic key loader function:

```python
def custom_key_loader(api_key):
    # Check the API key against a database or other storage
    # Example: return User.query.filter_by(api_key=api_key).first() is not None
    return api_key == 'dynamic-secret-key'

# Set the key loader on the app
app.key_loader = custom_key_loader
```

### Making Requests

To access a protected route, include the API key in the configured header:

```bash
curl -H "X-API-KEY: your-secret-api-key-123" http://localhost:5000/api/data
```

### Error Responses

- `401 Unauthorized`: When the API key is missing from the request
- `403 Forbidden`: When the API key is invalid

## Testing

Run the unit tests with pytest:

```bash
pytest tests/test_simple_auth.py -v
```

## License

This extension is released under the MIT License.
