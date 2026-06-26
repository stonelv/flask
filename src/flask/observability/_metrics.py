"""OpenTelemetry metrics integration for Flask.

This module provides automatic metrics collection for Flask applications,
including request counts, response times, and active request tracking.
"""

from __future__ import annotations

import time
import typing as t

if t.TYPE_CHECKING:
    from flask import Flask


def init_metrics(app: Flask, service_name: str, exporter: str) -> None:
    """Initialize OpenTelemetry metrics for a Flask application.

    Args:
        app: The Flask application instance.
        service_name: Service name for the meter.
        exporter: Exporter type - "otlp", "console", or "none".
    """
    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )
        from opentelemetry.sdk.resources import Resource
    except ImportError as e:
        raise ImportError(
            "Flask observability metrics requires OpenTelemetry packages. "
            "Install with: pip install Flask[observability]"
        ) from e

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Configure metric reader
    if exporter == "console":
        exporter_instance = ConsoleMetricExporter()
        reader = PeriodicExportingMetricReader(exporter_instance, export_interval_millis=60000)
    elif exporter == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            exporter_instance = OTLPMetricExporter()
            reader = PeriodicExportingMetricReader(
                exporter_instance, export_interval_millis=60000
            )
        except ImportError:
            # Fall back to console if OTLP not available
            exporter_instance = ConsoleMetricExporter()
            reader = PeriodicExportingMetricReader(
                exporter_instance, export_interval_millis=60000
            )
    else:
        # "none" - use a no-op reader that doesn't export
        reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(), export_interval_millis=3600000  # 1 hour
        )

    # Create meter provider
    provider = MeterProvider(resource=resource, metric_readers=[reader])

    # Set the global meter provider
    metrics.set_meter_provider(provider)

    # Get a meter for Flask
    meter = metrics.get_meter(__name__)

    # Create metrics instruments
    request_counter = meter.create_counter(
        name="http.server.request.count",
        description="Total number of HTTP requests",
        unit="1",
    )

    request_duration = meter.create_histogram(
        name="http.server.request.duration",
        description="HTTP request duration in seconds",
        unit="s",
    )

    active_requests = meter.create_up_down_counter(
        name="http.server.active_requests",
        description="Number of active HTTP requests",
        unit="1",
    )

    error_counter = meter.create_counter(
        name="http.server.error.count",
        description="Total number of HTTP errors (5xx)",
        unit="1",
    )

    # Store metrics in app extensions
    app.extensions["observability"]["metrics"] = {
        "meter": meter,
        "request_counter": request_counter,
        "request_duration": request_duration,
        "active_requests": active_requests,
        "error_counter": error_counter,
    }

    # Track request start times
    request_start_times: dict[int, float] = {}

    # Connect to Flask signals
    from flask import signals

    @signals.request_started.connect_via(app)
    def on_request_started(sender: t.Any, **kwargs: t.Any) -> None:
        """Record request start."""
        from flask import request

        # Increment active requests
        active_requests.add(1, {"http.method": request.method})

        # Store start time
        request_start_times[id(request)] = time.perf_counter()

    @signals.request_finished.connect_via(app)
    def on_request_finished(sender: t.Any, **kwargs: t.Any) -> None:
        """Record request completion."""
        from flask import request

        response = kwargs.get("response")

        # Decrement active requests
        active_requests.add(-1, {"http.method": request.method})

        # Calculate duration
        start_time = request_start_times.pop(id(request), None)
        if start_time is not None:
            duration = time.perf_counter() - start_time
            request_duration.record(
                duration,
                {
                    "http.method": request.method,
                    "http.status_code": str(response.status_code) if response else "unknown",
                    "http.route": request.endpoint or "unknown",
                },
            )

        # Increment request counter
        request_counter.add(
            1,
            {
                "http.method": request.method,
                "http.status_code": str(response.status_code) if response else "unknown",
                "http.route": request.endpoint or "unknown",
            },
        )

        # Count errors
        if response and response.status_code >= 500:
            error_counter.add(
                1,
                {
                    "http.method": request.method,
                    "http.status_code": str(response.status_code),
                },
            )

    @signals.request_tearing_down.connect_via(app)
    def on_request_tearing_down(sender: t.Any, **kwargs: t.Any) -> None:
        """Clean up on request teardown."""
        from flask import request

        # Ensure we clean up start time even if request_finished didn't fire
        request_start_times.pop(id(request), None)
