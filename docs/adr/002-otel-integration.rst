ADR-002: OpenTelemetry as a Contrib Extension
=============================================

Status
------

Accepted.

Context
-------

Production Flask deployments need observability (traces, metrics, logs)
but the core framework should remain lightweight. Third-party OTel
instrumentors exist but require separate installation and lack
Flask-specific semantic information (route names, blueprint context).

We needed to decide between:

1. Adding OTel to Flask's core (always available).
2. A bundled-but-optional ``contrib`` extension.
3. Leaving it entirely to third parties.

Decision
--------

Provide ``flask.contrib.otel.FlaskOTel`` as an optional extension,
installed via ``pip install flask[otel]``.

Design choices:

- **Extension pattern**: Uses ``init_app()`` and stores state in
  ``app.extensions["otel"]`` — no ``self.app`` reference, compatible
  with app factories.
- **Signal-based hooks**: Subscribes to ``request_started``,
  ``request_finished``, and ``got_request_exception`` signals plus
  ``before_request``/``after_request`` for metrics.
- **WSGI middleware wrapping**: Uses ``OpenTelemetryMiddleware`` on
  ``app.wsgi_app`` for transport-level tracing.
- **Import guards**: All ``opentelemetry.*`` imports are in a
  ``try/except ImportError`` block with a clear error message.

Consequences
------------

**Positive:**

- Zero runtime cost when not installed/initialized.
- Flask-specific span attributes (route, blueprint, endpoint) that
  generic WSGI instrumentors cannot provide.
- Ships with Flask — no separate package to discover or maintain.
- Does not change any public API.

**Negative:**

- Another package to keep compatible with OTel SDK releases.
- Contributors need to understand the OTel API to modify it.
- The ``contrib/`` directory is a new pattern for Flask that may
  invite requests for more bundled integrations.
