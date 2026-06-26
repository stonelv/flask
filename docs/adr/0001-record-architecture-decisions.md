# 0001 — Record architecture decisions

- Status: Accepted
- Date: 2026-06-23

## Context

This repository already carries a mature toolchain (uv, flit, ruff, mypy,
pyright, tox, pre-commit, trusted PyPI publishing). As we layer additional
engineering capability on top — observability examples, a performance gate,
release governance, one-click automation — the *reasons* for each choice need a
durable home. Reasons buried in PR descriptions are quickly lost; the next
contributor re-litigates settled trade-offs.

## Decision

We keep Architecture Decision Records under `docs/adr/`, one Markdown file per
decision, numbered sequentially, in MADR-lite form. A decision is immutable once
accepted; changing course means writing a new record that supersedes the old
one.

## Consequences

- Good: rationale is versioned alongside the code it justifies; onboarding and
  review get faster; superseded decisions stay visible as history.
- Good: forces us to state trade-offs explicitly before merging structural
  change.
- Cost: a small per-decision authoring overhead, and the discipline to actually
  write the record rather than skip it.

## Alternatives considered

- **Wiki / external doc**: drifts from the code, not reviewed in PRs.
- **Only CHANGES.rst**: captures *what* changed for users, not *why* we chose an
  architecture. The two serve different audiences and coexist.
