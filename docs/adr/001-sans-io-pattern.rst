ADR-001: Sans-IO Architecture Pattern
=====================================

Status
------

Accepted (existing architecture, documented retroactively).

Context
-------

Flask's routing, configuration, and handler registration logic was
originally coupled to the WSGI implementation. The Quart project
(async Flask) duplicated much of this code to provide an ASGI
alternative, leading to divergence and maintenance burden.

Decision
--------

Introduce a ``sansio/`` package inside Flask that contains protocol-
agnostic base classes:

- ``sansio.scaffold.Scaffold`` — shared routing and decorator logic
- ``sansio.app.App`` — configuration, URL map, error handlers
- ``sansio.blueprints.Blueprint`` — modular app components

The concrete ``Flask`` class in ``app.py`` inherits from ``App`` and
adds only WSGI-specific behavior: ``wsgi_app()``, context pushing,
and the development server.

The sans-IO layer uses no I/O and makes no assumptions about the
transport (WSGI vs ASGI).

Consequences
------------

**Positive:**

- Quart can inherit from the same base classes, eliminating code
  duplication.
- Testing the routing/config layer no longer requires a WSGI
  environment.
- Clear separation between "what Flask decides" and "how Flask
  talks to the server."

**Negative:**

- Two levels of indirection for contributors to understand.
- Changes to the base classes affect both Flask and Quart — more
  careful review is needed.
- ``sansio/`` modules must not import anything WSGI-specific, which
  limits what can live there.
