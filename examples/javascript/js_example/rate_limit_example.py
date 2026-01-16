from flask import Flask, jsonify, request
from functools import wraps
import time

app = Flask(__name__)

rate_limit_data = {}


def rate_limit(max_calls=10, period=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            current_time = time.time()
            
            if ip not in rate_limit_data:
                rate_limit_data[ip] = {"count": 1, "start_time": current_time}
            else:
                time_elapsed = current_time - rate_limit_data[ip]["start_time"]
                
                if time_elapsed >= period:
                    rate_limit_data[ip] = {"count": 1, "start_time": current_time}
                else:
                    rate_limit_data[ip]["count"] += 1
            
            if rate_limit_data[ip]["count"] > max_calls:
                return jsonify({
                    "error": "Too many requests",
                    "message": f"Rate limit exceeded. Maximum {max_calls} requests per {period} seconds."
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route("/api/test", methods=["GET"])
@rate_limit(max_calls=10, period=60)
def test_api():
    return jsonify({"message": "Hello, World!", "status": "success"})


@app.route("/api/data", methods=["GET", "POST"])
@rate_limit(max_calls=10, period=60)
def get_data():
    if request.method == "POST":
        data = request.get_json() or {}
        return jsonify({"received": data, "status": "success"})
    return jsonify({"data": [1, 2, 3, 4, 5], "status": "success"})


@app.route("/api/info", methods=["GET"])
def info():
    return jsonify({
        "message": "This endpoint has no rate limit",
        "usage": "Try accessing /api/test or /api/data with rate limiting"
    })


if __name__ == "__main__":
    app.run(debug=True, port=5002)
