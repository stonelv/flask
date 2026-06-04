from __future__ import annotations

import time
import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from .app import Flask


@dataclass
class RateLimitInfo:
    count: int
    limit: int
    reset_time: float
    remaining: int


class RateLimiter:
    def __init__(
        self,
        default_limit: int = 60,
        default_window: int = 60,
        enabled: bool = True,
    ):
        self.default_limit = default_limit
        self.default_window = default_window
        self.enabled = enabled
        self._storage: dict[str, tuple[int, float]] = {}
        self._route_limits: dict[str, tuple[int, int]] = {}

    def set_route_limit(self, route: str, limit: int, window: int) -> None:
        self._route_limits[route] = (limit, window)

    def get_route_limit(self, route: str) -> tuple[int, int]:
        return self._route_limits.get(route, (self.default_limit, self.default_window))

    def _get_key(self, ip: str, route: str) -> str:
        return f"{ip}:{route}"

    def check(self, ip: str, route: str) -> RateLimitInfo:
        key = self._get_key(ip, route)
        limit, window = self.get_route_limit(route)
        current_time = time.time()

        if key not in self._storage:
            self._storage[key] = (1, current_time + window)
            return RateLimitInfo(
                count=1,
                limit=limit,
                reset_time=current_time + window,
                remaining=limit - 1,
            )

        count, reset_time = self._storage[key]

        if current_time > reset_time:
            self._storage[key] = (1, current_time + window)
            return RateLimitInfo(
                count=1,
                limit=limit,
                reset_time=current_time + window,
                remaining=limit - 1,
            )

        new_count = count + 1
        self._storage[key] = (new_count, reset_time)

        return RateLimitInfo(
            count=new_count,
            limit=limit,
            reset_time=reset_time,
            remaining=max(0, limit - new_count),
        )

    def reset(self, ip: str, route: str) -> None:
        key = self._get_key(ip, route)
        if key in self._storage:
            del self._storage[key]

    def reset_all(self) -> None:
        self._storage.clear()


def init_app(app: Flask) -> None:
    app.config.setdefault("RATELIMIT_ENABLED", True)
    app.config.setdefault("RATELIMIT_DEFAULT_LIMIT", 60)
    app.config.setdefault("RATELIMIT_DEFAULT_WINDOW", 60)
    app.config.setdefault("RATELIMIT_STORAGE", None)
    app.config.setdefault("RATELIMIT_KEY_FUNC", None)
    app.config.setdefault("RATELIMIT_EXCLUDE_ROUTES", [])

    if not hasattr(app, "extensions"):
        app.extensions = {}

    limiter = RateLimiter(
        default_limit=app.config["RATELIMIT_DEFAULT_LIMIT"],
        default_window=app.config["RATELIMIT_DEFAULT_WINDOW"],
        enabled=app.config["RATELIMIT_ENABLED"],
    )

    app.extensions["ratelimit"] = limiter

    @app.before_request
    def check_rate_limit() -> t.Optional[t.Any]:
        from flask import request, jsonify, current_app

        limiter = current_app.extensions.get("ratelimit")

        if not limiter or not limiter.enabled:
            return None

        exclude_routes = current_app.config.get("RATELIMIT_EXCLUDE_ROUTES", [])
        if request.path in exclude_routes:
            return None

        key_func = current_app.config.get("RATELIMIT_KEY_FUNC")
        if key_func:
            ip = key_func()
        else:
            ip = request.remote_addr or "unknown"

        route = request.path

        info = limiter.check(ip, route)

        if info.count > info.limit:
            response = jsonify(
                {
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Limit: {info.limit} requests per window.",
                    "limit": info.limit,
                    "remaining": 0,
                    "reset": int(info.reset_time),
                }
            )
            response.status_code = 429
            response.headers["X-RateLimit-Limit"] = str(info.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(info.reset_time))
            return response

        return None
