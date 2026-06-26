# ADR-002: OpenTelemetry as Opt-in Observability Standard

## Status

Accepted

## Context

Modern applications require observability for:
- Distributed tracing in microservices
- Performance monitoring
- Error tracking
- Request correlation

Options considered:
1. Custom Flask-specific instrumentation
2. OpenTelemetry (OTel) standard
3. No built-in observability (status quo)

## Decision

Implement OpenTelemetry-based observability as an **opt-in** feature:

- Distributed tracing with automatic span creation
- Metrics collection (requests, duration, errors)
- Request ID tracking and propagation
- Structured logging with trace context

### Why OpenTelemetry?

1. **Industry standard**: CNCF project, vendor-neutral
2. **Rich ecosystem**: Jaeger, Zipkin, Prometheus, Grafana
3. **Automatic instrumentation**: Minimal code changes
4. **Future-proof**: Evolving standard with broad adoption

### Why Opt-in?

1. **Minimal overhead**: Zero cost when not used
2. **No forced dependencies**: Users choose their observability stack
3. **Backward compatible**: Existing apps work unchanged
4. **Explicit configuration**: Clear intent to enable observability

## Implementation

### Installation

```bash
pip install Flask[observability]
```

Installs:
- `opentelemetry-api`
- `opentelemetry-sdk`

### Usage

```python
from flask import Flask
from flask.observability import init_observability

app = Flask(__name__)
init_observability(app)
```

### Architecture

```
src/flask/observability/
├── __init__.py          # Public API: init_observability()
├── _tracing.py          # Span creation, context propagation
├── _metrics.py          # Counters, histograms, gauges
├── _request_id.py       # X-Request-ID generation
└── _logging.py          # JSON formatter with trace context
```

### Key Design Decisions

1. **Signal-based hooks**: Use Flask's existing signals (request_started, etc.)
2. **Lazy imports**: OTel packages only imported when enabled
3. **Configurable exporters**: OTLP, console, or none
4. **Selective features**: Enable/disable tracing, metrics, logging independently

### Performance

Benchmarked overhead (see `benchmarks/test_overhead.py`):

| Feature | Overhead | Notes |
|---------|----------|-------|
| Tracing | < 5% | Automatic span creation |
| Metrics | < 2% | Counter/histogram updates |
| Request ID | Negligible | UUID generation |
| Structured logging | ~10% | JSON serialization |

**Total with all features**: < 15% overhead

## Consequences

### Positive
- **Production-ready observability**: Users get tracing/metrics out of the box
- **Standard-based**: Easy migration to/from other frameworks
- **Flexible**: Works with any OTel-compatible backend
- **Minimal impact**: Zero overhead when disabled

### Negative
- **New dependencies**: OTel packages (~5MB)
- **Learning curve**: Users must understand OTel concepts
- **Maintenance burden**: Keep up with OTel API changes
- **Documentation**: Need comprehensive guides

### Mitigations
- Make observability truly optional (no import if not installed)
- Provide clear examples for common backends (Jaeger, Prometheus)
- Pin OTel versions to avoid breaking changes
- Extensive documentation with troubleshooting guide

## Alternatives Considered

1. **Custom instrumentation API**: More control but reinventing the wheel
2. **Mandatory observability**: Simpler but forces overhead on all users
3. **Third-party extensions**: Less maintenance but fragmented ecosystem
4. **Logging-only**: Simpler but missing tracing/metrics

## References

- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- PR #5150: Implement observability module
- Benchmarks: `benchmarks/test_overhead.py`
- Documentation: `docs/observability.rst`
