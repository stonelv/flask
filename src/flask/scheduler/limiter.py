import time
from datetime import datetime, timezone
from flask import request, jsonify
from flask.scheduler.metrics import Metrics

class RateLimiter:
    """Rate limiter for scheduler endpoints."""
    
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}  # ip -> list of timestamps
        self.metrics = Metrics()
    
    def __call__(self, f):
        """Decorator to apply rate limiting."""
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()
            
            # Clean up old requests
            if client_ip in self.requests:
                self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window_seconds]
            else:
                self.requests[client_ip] = []
            
            # Check if client has exceeded rate limit
            if len(self.requests[client_ip]) >= self.max_requests:
                self.metrics.rate_limited_count += 1
                return jsonify({"error": "rate_limited", "retry_after": self.window_seconds - (now - self.requests[client_ip][0])}), 429
            
            # Add current request time
            self.requests[client_ip].append(now)
            
            return f(*args, **kwargs)
        return decorated
