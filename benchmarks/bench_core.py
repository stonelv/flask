"""Timing helpers shared by the benchmark modules.

``measure`` runs a callable many times with GC disabled and returns a stats
dict keyed for ``baseline.json`` (median/min/stdev in microseconds). Using the
median and disabling GC keeps the numbers reproducible enough to gate CI.
"""

from __future__ import annotations

import gc
import statistics
import time


def measure(fn, *, warmup: int = 50, iterations: int = 200) -> dict[str, float]:
    """Return ``{median_us, min_us, stdev_us}`` for ``iterations`` calls.

    A fixed warmup primes caches; GC is disabled only around the measured
    loop so import-time allocations are unaffected. Stdev is the sample
    standard deviation of the per-call latencies.
    """
    for _ in range(warmup):
        fn()

    samples: list[float] = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            samples.append((time.perf_counter() - start) * 1_000_000)
    finally:
        if gc_was_enabled:
            gc.enable()

    samples.sort()
    return {
        "median_us": statistics.median(samples),
        "min_us": samples[0],
        "stdev_us": statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "iterations": float(iterations),
    }


def bench_core() -> dict[str, float]:
    """Full request round-trip on a hello-world app via the test client."""
    from benchmarks.conftest import make_app

    hello_app, _api_app, _template_app = make_app()
    client = hello_app.test_client()
    # sanity check the route once
    assert client.get("/").status_code == 200
    return measure(lambda: client.get("/"))


def bench_routing() -> dict[str, float]:
    """URL-rule match only, bypassing full dispatch."""
    from benchmarks.conftest import make_routing_app

    app = make_routing_app()
    adapter = app.url_map.bind("localhost")

    def match() -> None:
        adapter.match("/posts/42/comments/7")

    return measure(match)


def bench_templating() -> dict[str, float]:
    """Render a small Jinja template."""
    from benchmarks.conftest import make_app

    _hello_app, _api_app, template_app = make_app()
    app_ctx = template_app.app_context()
    app_ctx.push()
    try:
        return measure(lambda: template_app.jinja_env.from_string(
            "{% for i in range(10) %}{{ i }}{% endfor %}"
        ).render())
    finally:
        app_ctx.pop()


# Registry consumed by perf_check.py. Key = canonical metric name that must
# match the keys in baseline.json.
BENCHMARKS = {
    "core_request_roundtrip": bench_core,
    "routing_match": bench_routing,
    "template_render": bench_templating,
}
