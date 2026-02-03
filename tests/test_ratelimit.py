"""Tests for Flask rate limiting functionality."""

import time

import pytest

from flask import Flask
from flask import jsonify
from flask import rate_limit
from flask.ratelimit import _request_records
from flask.ratelimit import clear_rate_limit


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.testing = True
    
    # Clear rate limit records before each test
    clear_rate_limit()
    
    @app.route('/no-limit')
    def no_limit():
        return jsonify({'status': 'ok'})
    
    @app.route('/limited')
    @rate_limit(max_requests=3, window_seconds=60)
    def limited():
        return jsonify({'status': 'ok', 'data': 'value'})
    
    @app.route('/strict')
    @rate_limit(max_requests=2, window_seconds=10)
    def strict_limit():
        return jsonify({'status': 'ok'})
    
    @app.route('/custom-message')
    @rate_limit(max_requests=1, window_seconds=60, error_message="Custom error message")
    def custom_message():
        return jsonify({'status': 'ok'})
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestRateLimit:
    """Test rate limiting functionality."""
    
    def test_no_limit_route(self, client):
        """Routes without rate_limit decorator should work normally."""
        for _ in range(10):
            response = client.get('/no-limit')
            assert response.status_code == 200
            assert response.get_json() == {'status': 'ok'}
    
    def test_rate_limit_allows_requests_within_limit(self, client):
        """Requests within the limit should succeed."""
        for i in range(3):
            response = client.get('/limited')
            assert response.status_code == 200
            assert response.get_json()['status'] == 'ok'
            
            # Check rate limit headers
            assert 'X-RateLimit-Limit' in response.headers
            assert 'X-RateLimit-Remaining' in response.headers
            assert 'X-RateLimit-Reset' in response.headers
            assert response.headers['X-RateLimit-Limit'] == '3'
            assert response.headers['X-RateLimit-Remaining'] == str(3 - i - 1)
    
    def test_rate_limit_blocks_excess_requests(self, client):
        """Requests exceeding the limit should be blocked with 429."""
        # Make 3 successful requests
        for _ in range(3):
            response = client.get('/limited')
            assert response.status_code == 200
        
        # 4th request should be blocked
        response = client.get('/limited')
        assert response.status_code == 429
        
        data = response.get_json()
        assert data['error'] == 'Too Many Requests'
        assert 'Rate limit exceeded' in data['message']
        assert data['limit'] == 3
        assert data['window'] == 60
        assert data['remaining'] == 0
    
    def test_rate_limit_headers_on_blocked_request(self, client):
        """Blocked requests should include rate limit headers."""
        # Exhaust the limit
        for _ in range(3):
            client.get('/limited')
        
        response = client.get('/limited')
        assert response.status_code == 429
        
        assert response.headers['X-RateLimit-Limit'] == '3'
        assert response.headers['X-RateLimit-Remaining'] == '0'
        assert 'X-RateLimit-Reset' in response.headers
        assert 'Retry-After' in response.headers
    
    def test_custom_error_message(self, client):
        """Custom error messages should be used."""
        # Use up the limit
        client.get('/custom-message')
        
        # Next request should show custom message
        response = client.get('/custom-message')
        assert response.status_code == 429
        assert response.get_json()['message'] == 'Custom error message'
    
    def test_rate_limit_resets_after_window(self, client):
        """Rate limit should reset after the time window."""
        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()
        
        @app.route('/test')
        @rate_limit(max_requests=2, window_seconds=1)
        def test_route():
            return jsonify({'status': 'ok'})
        
        test_client = app.test_client()
        
        # Exhaust the limit
        for _ in range(2):
            response = test_client.get('/test')
            assert response.status_code == 200
        
        # Should be blocked
        response = test_client.get('/test')
        assert response.status_code == 429
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should work again
        response = test_client.get('/test')
        assert response.status_code == 200
    
    def test_different_routes_have_separate_limits(self, client):
        """Different routes should have independent rate limits."""
        # Exhaust /strict limit (2 requests)
        for _ in range(2):
            response = client.get('/strict')
            assert response.status_code == 200
        
        # /strict should be blocked
        response = client.get('/strict')
        assert response.status_code == 429
        
        # /limited should still work (separate limit)
        for _ in range(3):
            response = client.get('/limited')
            assert response.status_code == 200
    
    def test_clear_rate_limit(self, client):
        """Clearing rate limit should reset counts."""
        # Exhaust the limit
        for _ in range(3):
            client.get('/limited')
        
        # Should be blocked
        response = client.get('/limited')
        assert response.status_code == 429
        
        # Clear rate limits
        clear_rate_limit()
        
        # Should work again
        response = client.get('/limited')
        assert response.status_code == 200


class TestRateLimitWithKeyFunc:
    """Test rate limiting with custom key function."""
    
    def test_custom_key_function(self):
        """Rate limiting with custom key function."""
        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()
        
        # Use a simple counter as key for testing
        counter = {'value': 0}
        
        def key_func():
            # Alternate between two keys
            counter['value'] += 1
            return 'user1' if counter['value'] % 2 == 1 else 'user2'
        
        @app.route('/keyed')
        @rate_limit(max_requests=2, window_seconds=60, key_func=key_func)
        def keyed_route():
            return jsonify({'status': 'ok'})
        
        client = app.test_client()
        
        # Requests alternate between user1 and user2, so each can make 2 requests
        # First 4 requests should succeed (2 per user)
        for _ in range(4):
            response = client.get('/keyed')
            assert response.status_code == 200
        
        # 5th request (user1's 3rd) should be blocked
        response = client.get('/keyed')
        assert response.status_code == 429


class TestRateLimitWithBlueprint:
    """Test rate limiting with Flask Blueprints."""

    def test_blueprint_routes_have_independent_limits(self):
        """Same function name in different blueprints should have independent limits."""
        from flask import Blueprint

        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()

        # Create two blueprints with same function name
        bp1 = Blueprint('bp1', __name__)
        bp2 = Blueprint('bp2', __name__)

        @bp1.route('/list')
        @rate_limit(max_requests=2, window_seconds=60)
        def list_items_bp1():
            return jsonify({'from': 'bp1', 'items': []})

        @bp2.route('/list')
        @rate_limit(max_requests=2, window_seconds=60)
        def list_items_bp2():
            return jsonify({'from': 'bp2', 'items': []})

        app.register_blueprint(bp1, url_prefix='/api1')
        app.register_blueprint(bp2, url_prefix='/api2')

        client = app.test_client()

        # Exhaust bp1's limit
        for _ in range(2):
            response = client.get('/api1/list')
            assert response.status_code == 200
            assert response.get_json()['from'] == 'bp1'

        # bp1 should be blocked
        response = client.get('/api1/list')
        assert response.status_code == 429

        # bp2 should still work (independent limit)
        for _ in range(2):
            response = client.get('/api2/list')
            assert response.status_code == 200
            assert response.get_json()['from'] == 'bp2'

    def test_per_route_false_shares_limit(self):
        """When per_route=False, same function name should share limit."""
        from flask import Blueprint

        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()

        bp1 = Blueprint('bp3', __name__)
        bp2 = Blueprint('bp4', __name__)

        @bp1.route('/shared')
        @rate_limit(max_requests=2, window_seconds=60, per_route=False)
        def shared_endpoint_bp1():
            return jsonify({'from': 'bp1'})

        @bp2.route('/shared')
        @rate_limit(max_requests=2, window_seconds=60, per_route=False)
        def shared_endpoint_bp2():
            return jsonify({'from': 'bp2'})

        app.register_blueprint(bp1, url_prefix='/api3')
        app.register_blueprint(bp2, url_prefix='/api4')

        client = app.test_client()

        # Use up limit on bp3 (counts against shared IP-based limit)
        for _ in range(2):
            response = client.get('/api3/shared')
            assert response.status_code == 200

        # bp4 should also be blocked (shares the same limit)
        response = client.get('/api4/shared')
        assert response.status_code == 429


class TestRateLimitEdgeCases:
    """Test edge cases and error handling."""

    def test_rate_limit_with_different_http_methods(self):
        """Rate limit should work with different HTTP methods."""
        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()
        
        @app.route('/resource', methods=['GET', 'POST', 'PUT', 'DELETE'])
        @rate_limit(max_requests=2, window_seconds=60)
        def resource():
            return jsonify({'status': 'ok'})
        
        client = app.test_client()
        
        # Different methods share the same limit
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        for i, method in enumerate(methods):
            response = client.open('/resource', method=method)
            if i < 2:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
    
    def test_rate_limit_preserves_response_type(self):
        """Rate limit should preserve the original response type."""
        app = Flask(__name__)
        app.testing = True
        clear_rate_limit()
        
        @app.route('/text')
        @rate_limit(max_requests=5, window_seconds=60)
        def text_response():
            return 'Plain text response'
        
        client = app.test_client()
        
        response = client.get('/text')
        assert response.status_code == 200
        assert response.data.decode() == 'Plain text response'
        assert 'X-RateLimit-Limit' in response.headers
