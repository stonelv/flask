from functools import wraps
from time import time
from flask import Flask, request, jsonify

app = Flask(__name__)

rate_limit_storage = {}

def rate_limit(per_minute=10, window_seconds=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            endpoint = request.endpoint
            key = f"{ip}:{endpoint}"
            
            now = time()
            if key not in rate_limit_storage:
                rate_limit_storage[key] = []
            
            requests = rate_limit_storage[key]
            requests = [t for t in requests if now - t < window_seconds]
            rate_limit_storage[key] = requests
            
            if len(requests) >= per_minute:
                return (
                    jsonify({
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Maximum {per_minute} requests per {window_seconds} seconds allowed."
                    }),
                    429
                )
            
            requests.append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route('/api/public')
@rate_limit(per_minute=10, window_seconds=60)
def public_api():
    return jsonify({
        "message": "Hello from rate-limited API!",
        "status": "success"
    })

@app.route('/api/users')
@rate_limit(per_minute=5, window_seconds=60)
def get_users():
    return jsonify({
        "users": ["Alice", "Bob", "Charlie"],
        "status": "success"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
