"""In-process Flask micro-benchmarks and the performance-regression gate.

These benchmarks measure Flask's *framework* request-dispatch overhead using
the in-process test client (no network, no real WSGI server). That keeps the
numbers deterministic enough to use as a CI gate: ``gc.disable()`` around each
measurement, a fixed warmup/measurement count, and the median (not the mean)
are reported. For real-world load testing see ``benchmarks/README.rst``.

Run::

    tox run -e perf                 # run + compare against baseline.json (advisory)
    python benchmarks/perf_check.py --update-baseline   # manual recalibration
"""
