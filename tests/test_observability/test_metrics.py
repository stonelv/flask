"""Test OpenTelemetry metrics integration."""

import pytest

pytest.importorskip("opentelemetry")

from flask import Flask
from flask.observability import init_observability


@pytest.fixture
def instrumented_app():
    """Create a Flask app with metrics enabled."""
    app = Flask(__name__)
    init_observability(app, exporter="none", tracing=False, metrics=True, request_id=False)

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    @app.route("/error")
    def error():
        raise ValueError("Test error")

    @app.route("/status/<int:code>")
    def status(code):
        from flask import abort

        abort(code)

    yield app


def test_metrics_instruments_created(instrumented_app):
    """Test that metric instruments are created."""
    obs_config = instrumented_app.extensions.get("observability", {})
    metrics_config = obs_config.get("metrics", {})
    assert "meter" in metrics_config
    assert "request_counter" in metrics_config
    assert "request_duration" in metrics_config
    assert "active_requests" in metrics_config
    assert "error_counter" in metrics_config


def test_metrics_disabled():
    """Test that no metrics are created when metrics is disabled."""
    app = Flask(__name__)
    init_observability(app, exporter="none", tracing=False, metrics=False, request_id=False)

    obs_config = app.extensions.get("observability", {})
    # When metrics is disabled, it should be False or not have the metrics dict
    assert obs_config.get("metrics") is False


def test_metrics_request_counting(instrumented_app):
    """Test that requests are counted without errors."""
    client = instrumented_app.test_client()

    for _ in range(3):
        response = client.get("/hello")
        assert response.status_code == 200


def test_metrics_error_counting(instrumented_app):
    """Test that errors are counted without errors."""
    client = instrumented_app.test_client()

    response = client.get("/status/500")
    assert response.status_code == 500


def test_metrics_with_different_status_codes(instrumented_app):
    """Test that metrics track different status codes without errors."""
    client = instrumented_app.test_client()

    # 200 OK
    response = client.get("/hello")
    assert response.status_code == 200

    # 404 Not Found
    response = client.get("/nonexistent")
    assert response.status_code == 404

    # 500 Internal Server Error
    response = client.get("/status/500")
    assert response.status_code == 500
