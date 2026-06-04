"""
Flask Rate Limit Example

This example demonstrates the integrated rate_limit decorator.

Usage:
    python rate_limit_example.py
    
    Then visit http://127.0.0.1:5001/ in your browser
"""

import time

from flask import Flask
from flask import jsonify
from flask import rate_limit

app = Flask(__name__)


@app.route('/')
def index():
    """Home page - no rate limit."""
    return jsonify({
        "message": "Welcome to Flask Rate Limit Example",
        "endpoints": {
            "/api/data": "GET - Rate limit: 10 requests per minute",
            "/api/login": "POST - Rate limit: 5 requests per minute",
            "/api/public": "GET - Rate limit: 100 requests per minute"
        }
    })


@app.route('/api/data', methods=['GET'])
@rate_limit(max_requests=10, window_seconds=60)
def get_data():
    """
    Get data endpoint - Rate limit: 10 requests per minute.
    """
    return jsonify({
        "status": "success",
        "data": {
            "items": ["item1", "item2", "item3"],
            "timestamp": time.time()
        }
    })


@app.route('/api/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def login():
    """
    Login endpoint - Rate limit: 5 requests per minute (stricter limit).
    """
    return jsonify({
        "status": "success",
        "message": "Login endpoint (simulated)"
    })


@app.route('/api/public', methods=['GET'])
@rate_limit(max_requests=100, window_seconds=60)
def public_data():
    """
    Public data endpoint - Rate limit: 100 requests per minute (more lenient).
    """
    return jsonify({
        "status": "success",
        "data": "This is public data with higher rate limit"
    })


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle 429 errors."""
    return jsonify({
        "error": "Too Many Requests",
        "message": "Rate limit exceeded. Please try again later."
    }), 429


if __name__ == '__main__':
    print("=" * 60)
    print("Flask Rate Limit Example Server")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /           - Home (no limit)")
    print("  GET  /api/data   - Data endpoint (10 req/min)")
    print("  POST /api/login  - Login endpoint (5 req/min)")
    print("  GET  /api/public - Public data (100 req/min)")
    print("\nTest command:")
    print('  for i in {1..12}; do curl -s http://127.0.0.1:5001/api/data | jq; done')
    print("\n" + "=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5001)
