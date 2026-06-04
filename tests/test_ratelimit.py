import time

import flask
from flask import init_ratelimit


class TestRateLimiter:
    def test_check_initial_request(self):
        limiter = flask.RateLimiter(default_limit=5, default_window=60)
        info = limiter.check("127.0.0.1", "/test")
        assert info.count == 1
        assert info.limit == 5
        assert info.remaining == 4

    def test_check_multiple_requests(self):
        limiter = flask.RateLimiter(default_limit=5, default_window=60)
        for i in range(1, 6):
            info = limiter.check("127.0.0.1", "/test")
            assert info.count == i
            assert info.remaining == 5 - i

    def test_check_exceeds_limit(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)
        limiter.check("127.0.0.1", "/test")
        limiter.check("127.0.0.1", "/test")
        info = limiter.check("127.0.0.1", "/test")
        assert info.count == 3
        assert info.remaining == 0
        assert info.count > info.limit

    def test_check_different_ips_independent(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)
        limiter.check("127.0.0.1", "/test")
        limiter.check("127.0.0.1", "/test")
        info1 = limiter.check("127.0.0.1", "/test")
        info2 = limiter.check("192.168.1.1", "/test")
        assert info1.count == 3
        assert info2.count == 1
        assert info2.remaining == 1

    def test_check_different_routes_independent(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)
        limiter.check("127.0.0.1", "/route1")
        limiter.check("127.0.0.1", "/route1")
        info1 = limiter.check("127.0.0.1", "/route1")
        info2 = limiter.check("127.0.0.1", "/route2")
        assert info1.count == 3
        assert info2.count == 1

    def test_reset(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)
        limiter.check("127.0.0.1", "/test")
        limiter.check("127.0.0.1", "/test")
        limiter.reset("127.0.0.1", "/test")
        info = limiter.check("127.0.0.1", "/test")
        assert info.count == 1
        assert info.remaining == 1

    def test_reset_all(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)
        limiter.check("127.0.0.1", "/route1")
        limiter.check("192.168.1.1", "/route2")
        limiter.reset_all()
        info1 = limiter.check("127.0.0.1", "/route1")
        info2 = limiter.check("192.168.1.1", "/route2")
        assert info1.count == 1
        assert info2.count == 1

    def test_set_route_limit(self):
        limiter = flask.RateLimiter(default_limit=5, default_window=60)
        limiter.set_route_limit("/api/special", 10, 120)
        limit, window = limiter.get_route_limit("/api/special")
        assert limit == 10
        assert window == 120
        default_limit, default_window = limiter.get_route_limit("/other")
        assert default_limit == 5
        assert default_window == 60


class TestRateLimitMiddleware:
    def _create_app(self):
        app = flask.Flask("test_app")
        app.config["TESTING"] = True
        return app

    def test_normal_request(self):
        app = self._create_app()

        @app.route("/test")
        def test_route():
            return "OK"

        init_ratelimit(app)
        client = app.test_client()

        response = client.get("/test")
        assert response.status_code == 200
        assert response.data == b"OK"

    def test_rate_limit_exceeded(self):
        app = self._create_app()

        @app.route("/test")
        def test_route():
            return "OK"

        app.config["RATELIMIT_DEFAULT_LIMIT"] = 2
        app.config["RATELIMIT_DEFAULT_WINDOW"] = 60
        init_ratelimit(app)
        client = app.test_client()

        response1 = client.get("/test")
        assert response1.status_code == 200

        response2 = client.get("/test")
        assert response2.status_code == 200

        response3 = client.get("/test")
        assert response3.status_code == 429

        data = response3.get_json()
        assert data["error"] == "Too Many Requests"
        assert data["limit"] == 2
        assert data["remaining"] == 0

        assert response3.headers.get("X-RateLimit-Limit") == "2"
        assert response3.headers.get("X-RateLimit-Remaining") == "0"

    def test_ratelimit_disabled(self):
        app = self._create_app()

        @app.route("/test")
        def test_route():
            return "OK"

        app.config["RATELIMIT_ENABLED"] = False
        app.config["RATELIMIT_DEFAULT_LIMIT"] = 1
        init_ratelimit(app)
        client = app.test_client()

        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_exclude_routes(self):
        app = self._create_app()

        @app.route("/public")
        def public_route():
            return "Public"

        @app.route("/private")
        def private_route():
            return "Private"

        app.config["RATELIMIT_DEFAULT_LIMIT"] = 1
        app.config["RATELIMIT_EXCLUDE_ROUTES"] = ["/public"]
        init_ratelimit(app)
        client = app.test_client()

        for _ in range(3):
            response = client.get("/public")
            assert response.status_code == 200

        client.get("/private")
        response = client.get("/private")
        assert response.status_code == 429

    def test_different_ips_limited_separately(self):
        app = self._create_app()

        @app.route("/test")
        def test_route():
            return "OK"

        app.config["RATELIMIT_DEFAULT_LIMIT"] = 1
        init_ratelimit(app)

        client = app.test_client()
        environ_base1 = {"REMOTE_ADDR": "192.168.1.1"}
        environ_base2 = {"REMOTE_ADDR": "192.168.1.2"}

        response1 = client.get("/test", environ_base=environ_base1)
        assert response1.status_code == 200

        response2 = client.get("/test", environ_base=environ_base2)
        assert response2.status_code == 200

        response3 = client.get("/test", environ_base=environ_base1)
        assert response3.status_code == 429

        response4 = client.get("/test", environ_base=environ_base2)
        assert response4.status_code == 429

    def test_different_routes_limited_separately(self):
        app = self._create_app()

        @app.route("/route1")
        def route1():
            return "Route 1"

        @app.route("/route2")
        def route2():
            return "Route 2"

        app.config["RATELIMIT_DEFAULT_LIMIT"] = 1
        init_ratelimit(app)
        client = app.test_client()

        client.get("/route1")
        client.get("/route2")

        response1 = client.get("/route1")
        assert response1.status_code == 429

        response2 = client.get("/route2")
        assert response2.status_code == 429


class TestRateLimitWindowReset:
    def _create_app(self):
        app = flask.Flask("test_app")
        app.config["TESTING"] = True
        return app

    def test_window_reset(self):
        limiter = flask.RateLimiter(default_limit=2, default_window=60)

        limiter.check("127.0.0.1", "/test")
        limiter.check("127.0.0.1", "/test")
        info = limiter.check("127.0.0.1", "/test")
        assert info.count == 3
        assert info.count > info.limit

        key = limiter._get_key("127.0.0.1", "/test")
        count, reset_time = limiter._storage[key]
        limiter._storage[key] = (count, time.time() - 120)

        info_reset = limiter.check("127.0.0.1", "/test")
        assert info_reset.count == 1
        assert info_reset.remaining == 1

    def test_middleware_window_reset(self):
        app = self._create_app()

        @app.route("/test")
        def test_route():
            return "OK"

        app.config["RATELIMIT_DEFAULT_LIMIT"] = 2
        app.config["RATELIMIT_DEFAULT_WINDOW"] = 60
        init_ratelimit(app)
        client = app.test_client()

        client.get("/test")
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429

        limiter = app.extensions["ratelimit"]
        key = limiter._get_key("127.0.0.1", "/test")
        count, reset_time = limiter._storage[key]

        limiter._storage[key] = (count, time.time() - 120)

        response = client.get("/test")
        assert response.status_code == 200
