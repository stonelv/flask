"""OpenTelemetry tracing integration for Flask.

This module connects Flask's blinker signals to OpenTelemetry spans,
providing distributed tracing for HTTP requests.
"""

from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from flask import Flask


def init_tracing(app: Flask, service_name: str, exporter: str) -> None:
    """Initialize OpenTelemetry tracing for a Flask application.

    Args:
        app: The Flask application instance.
        service_name: Service name for the tracer.
        exporter: Exporter type - "otlp", "console", or "none".
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )
        from opentelemetry.trace import StatusCode
        from opentelemetry.trace.status import Status
    except ImportError as e:
        raise ImportError(
            "Flask observability tracing requires OpenTelemetry packages. "
            "Install with: pip install Flask[observability]"
        ) from e

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter
    if exporter == "console":
        exporter_instance = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter_instance))
    elif exporter == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter_instance = OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter_instance))
        except ImportError:
            # Fall back to console if OTLP not available
            exporter_instance = ConsoleSpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(exporter_instance))
    # else: "none" - no exporter, spans are created but not exported

    # Set the global tracer provider (only if not already set)
    try:
        trace.set_tracer_provider(provider)
    except Exception:
        # Provider already set, use the existing one
        pass

    # Get a tracer for Flask
    tracer = trace.get_tracer(__name__)

    # Store tracer in app extensions
    app.extensions["observability"]["tracer"] = tracer
    app.extensions["observability"]["trace"] = trace

    # Connect to Flask signals
    from flask import signals

    @signals.request_started.connect_via(app)
    def on_request_started(sender: t.Any, **kwargs: t.Any) -> None:
        """Start a span when a request begins."""
        from flask import request

        # Extract span context from incoming request headers (for distributed tracing)
        ctx = trace.get_current_span().get_span_context()

        # Create a new span for this request
        span = tracer.start_span(
            name=f"{request.method} {request.path}",
            kind=trace.SpanKind.SERVER,
        )

        # Set HTTP attributes on the span
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("http.target", request.path)
        span.set_attribute("http.scheme", request.scheme)
        span.set_attribute("http.host", request.host)

        if request.query_string:
            span.set_attribute("http.query", request.query_string.decode("utf-8"))

        # Store span in request context
        if not hasattr(request, "_otel_span"):
            request._otel_span = span  # type: ignore[attr-defined]

    @signals.request_finished.connect_via(app)
    def on_request_finished(sender: t.Any, **kwargs: t.Any) -> None:
        """End the span when a request finishes."""
        from flask import request

        response = kwargs.get("response")
        span = getattr(request, "_otel_span", None)

        if span and response:
            # Set response attributes
            span.set_attribute("http.status_code", response.status_code)

            # Set span status based on HTTP status code
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            elif response.status_code >= 400:
                span.set_status(Status(StatusCode.UNSET))
            else:
                span.set_status(Status(StatusCode.OK))

            # End the span
            span.end()

    @signals.got_request_exception.connect_via(app)
    def on_request_exception(sender: t.Any, **kwargs: t.Any) -> None:
        """Record exception on the span."""
        from flask import request

        exception = kwargs.get("exception")
        span = getattr(request, "_otel_span", None)

        if span and exception:
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))

    @signals.request_tearing_down.connect_via(app)
    def on_request_tearing_down(sender: t.Any, **kwargs: t.Any) -> None:
        """Clean up span when request tears down."""
        from flask import request

        span = getattr(request, "_otel_span", None)
        if span and span.is_recording():
            # Ensure span is ended even if request_finished didn't fire
            span.end()
