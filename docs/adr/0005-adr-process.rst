ADR 0005: The ADR process
=========================

:Date: 2026-06-26
:Status: Accepted

Context
-------

This repository records architectural decisions so future contributors
understand *why* a choice was made, not just *what* was chosen. The docs are
built with Sphinx under ``-W`` (warnings are errors), so any new page must
not introduce dangling cross-references.

Decision
--------

#. **ADRs live in ``docs/adr/`` as reStructuredText** (matching the rest of
   the docs) and are listed in ``docs/adr/index.rst``. They are wired into
   the "Additional Notes" toctree of ``docs/index.rst``.

#. **Each ADR is self-contained prose.** It uses only standard reST; it does
   not emit ``:ref:`` labels or ``:doc:`` targets that could dangle and trip
   ``sphinx-build -W``. Cross-references to other ADRs are by name in prose
   (``ADR 0001``), not by role.

#. **ADRs are append-only.** A decision that reverses an earlier one adds a
   new ADR (``0006-...``) and marks the old one ``Status: superseded``; the
   old ADR is left in place so the history of reasoning is preserved.

#. **Filename format:** ``NNNN-kebab-case-name.rst``, zero-padded, numbered
   sequentially. The title is ``ADR NNNN: <short title>``.

Consequences
------------

Positive: the reasoning behind the engineering platform is durable and
discoverable from the published docs; the append-only rule preserves the
history of reversed decisions.

Negative: a small amount of process overhead -- but the self-contained-prose
rule keeps each ADR cheap to write and safe to build.
