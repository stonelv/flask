.. _benchmarks:

Performance Benchmarks
======================

Flask includes a comprehensive benchmark suite to track performance across releases and detect regressions.

Running Benchmarks
------------------

Install benchmark dependencies::

    pip install Flask[benchmarks]

Or install manually::

    pip install pytest-benchmark

Run all benchmarks::

    pytest benchmarks/ --benchmark-only

Run specific benchmark files::

    pytest benchmarks/test_routing.py --benchmark-only
    pytest benchmarks/test_request_cycle.py --benchmark-only

Generate JSON report::

    pytest benchmarks/ --benchmark-only --benchmark-json=report.json

Generate HTML report::

    pytest benchmarks/ --benchmark-only --benchmark-histogram

Benchmark Categories
--------------------

App Creation (``test_app_creation.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures Flask application instantiation time:

- Minimal app creation
- App with blueprints
- App with extensions

Routing (``test_routing.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures URL matching performance:

- Simple routes: ``/users``
- Parameterized routes: ``/users/<int:id>``
- Complex patterns: ``/api/v2/users/<int:id>/posts/<slug>``
- Blueprint routes

Request Cycle (``test_request_cycle.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures full request lifecycle:

- Request with no hooks
- Request with ``before_request``/``after_request``
- Request with error handling
- Request with multiple hooks

Templating (``test_templating.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures Jinja2 rendering performance:

- Simple template rendering
- Template with loops
- Template with conditionals
- Template inheritance

JSON (``test_json.py``)
~~~~~~~~~~~~~~~~~~~~~~~

Measures JSON serialization/deserialization:

- Small JSON responses
- Large JSON responses
- JSON request parsing
- Custom JSON encoding

Session (``test_session.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures session operations:

- Session creation
- Session read
- Session write
- Session with multiple keys

Signals (``test_signals.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures signal dispatch overhead:

- Signal emission with no subscribers
- Signal with one subscriber
- Signal with multiple subscribers

Observability (``test_overhead.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measures observability overhead:

- Baseline request (no observability)
- Request with tracing enabled
- Request with metrics enabled
- Request with full observability

Understanding Results
---------------------

Benchmark output includes:

- **ops/sec**: Operations per second (higher is better)
- **mean**: Average time per operation
- **stddev**: Standard deviation
- **median**: Median time
- **min/max**: Minimum and maximum times

Example output:

.. code-block:: text

    ---------------------------------------------------------------------------
    Name                          Mean        StdDev      Ops/sec    Rounds
    ---------------------------------------------------------------------------
    test_simple_route          45.2μs       2.1μs      22,124      100
    test_parameterized_route   52.3μs       2.5μs      19,120      100
    test_complex_route         68.7μs       3.2μs      14,556      100

Comparing Releases
------------------

Compare performance between versions:

.. code-block:: bash

    # Run benchmarks on current branch
    pytest benchmarks/ --benchmark-only --benchmark-save=current

    # Switch to another branch/tag
    git checkout v3.1.0

    # Run benchmarks and compare
    pytest benchmarks/ --benchmark-only --benchmark-compare=current

This shows performance differences:

.. code-block:: text

    Name                          Mean (v3.1.0)  Mean (current)  Change
    ---------------------------------------------------------------------------
    test_simple_route             48.2μs         45.2μs         -6.2%
    test_parameterized_route      55.1μs         52.3μs         -5.1%

Performance Targets
-------------------

Flask aims for these performance targets (on modern hardware):

- **App creation**: < 1ms
- **Simple route matching**: < 50μs
- **Request cycle**: < 100μs (excluding view function)
- **Template rendering**: < 1ms (simple templates)
- **JSON serialization**: < 100μs (small payloads)

These targets are validated in CI to prevent regressions.

CI Integration
--------------

Benchmarks run automatically in CI:

1. **Pull requests**: Benchmarks compare against baseline
2. **Main branch**: Results saved as new baseline
3. **Releases**: Full benchmark suite runs before release

If a PR introduces >10% regression, CI warns (but doesn't block):

.. code-block:: text

    ⚠️ Performance regression detected:
    - test_complex_route: 68.7μs → 78.9μs (+14.8%)

Review the changes to ensure the regression is acceptable.

Writing Benchmarks
------------------

Add new benchmarks using ``pytest-benchmark``:

.. code-block:: python

    import pytest
    from flask import Flask

    def test_my_feature(benchmark):
        app = Flask(__name__)

        @app.route('/my-endpoint')
        def my_endpoint():
            return "Hello"

        client = app.test_client()

        # Benchmark the request
        result = benchmark(client.get, '/my-endpoint')

        # Assert correctness
        assert result.status_code == 200

Use fixtures for common setup:

.. code-block:: python

    @pytest.fixture
    def app_with_blueprint():
        app = Flask(__name__)
        bp = Blueprint('api', __name__)
        # ... setup blueprint
        app.register_blueprint(bp)
        return app

    def test_blueprint_routing(benchmark, app_with_blueprint):
        client = app_with_blueprint.test_client()
        benchmark(client.get, '/api/endpoint')

Optimization Tips
-----------------

If benchmarks reveal performance issues:

1. **Profile first**: Use ``pytest --benchmark-cprofile`` to identify bottlenecks
2. **Avoid premature optimization**: Only optimize hot paths
3. **Measure impact**: Always benchmark before and after changes
4. **Consider trade-offs**: Readability vs. performance

Common optimizations:

- Use ``__slots__`` for frequently instantiated classes
- Cache expensive computations with ``@lru_cache``
- Avoid unnecessary imports in hot paths
- Use list comprehensions instead of loops
- Precompile regex patterns

Baseline Management
-------------------

The baseline file (``benchmarks/baseline.json``) tracks performance over time:

- Updated automatically on main branch merges
- Used for PR comparisons
- Committed to repository for historical tracking

To manually update baseline:

.. code-block:: bash

    pytest benchmarks/ --benchmark-only --benchmark-save=baseline
    git add benchmarks/baseline.json
    git commit -m "Update performance baseline"

Troubleshooting
---------------

**Benchmarks are slow**

- Use ``--benchmark-min-rounds=5`` to reduce iterations
- Run specific benchmark files instead of full suite
- Use ``--benchmark-disable`` to skip benchmarks in regular tests

**Results vary widely**

- Increase rounds: ``--benchmark-min-rounds=20``
- Run on quiet system (no other processes)
- Use ``--benchmark-warmup=on`` to warm up JIT
- Pin CPU frequency (disable turbo boost)

**CI benchmarks fail**

- Check if changes affect benchmarked code paths
- Review benchmark warnings in CI logs
- Update baseline if regression is acceptable
- Add ``[skip benchmarks]`` to commit message to skip

See Also
--------

- :doc:`/observability` - Observability overhead benchmarks
- pytest-benchmark: https://pytest-benchmark.readthedocs.io/
