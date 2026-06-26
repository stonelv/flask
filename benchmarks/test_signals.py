"""Benchmark blinker signal emission overhead."""

from __future__ import annotations

import flask
from pytest_benchmark.fixture import BenchmarkFixture


def test_signal_request_started(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure overhead of request_started signal firing."""
    received: list[object] = []

    @flask.signals.request_started.connect_via(app)
    def on_request_started(sender: object, **kwargs: object) -> None:
        received.append(sender)

    @app.route("/signal-test")
    def signal_test() -> str:
        return "ok"

    result = benchmark(client.get, "/signal-test")
    assert result.status_code == 200


def test_signal_request_finished(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure overhead of request_finished signal firing."""
    received: list[object] = []

    @flask.signals.request_finished.connect_via(app)
    def on_request_finished(sender: object, **kwargs: object) -> None:
        received.append(sender)

    @app.route("/signal-test")
    def signal_test() -> str:
        return "ok"

    result = benchmark(client.get, "/signal-test")
    assert result.status_code == 200


def test_signal_multiple_listeners(
    benchmark: BenchmarkFixture, app: flask.Flask, client: flask.testing.FlaskClient
) -> None:
    """Measure overhead with multiple signal listeners."""
    for _i in range(5):

        @flask.signals.request_started.connect_via(app)
        def listener(sender: object, **kwargs: object) -> None:
            pass

        @flask.signals.request_finished.connect_via(app)
        def listener2(sender: object, **kwargs: object) -> None:
            pass

    @app.route("/multi-signal")
    def multi_signal() -> str:
        return "ok"

    result = benchmark(client.get, "/multi-signal")
    assert result.status_code == 200
