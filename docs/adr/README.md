# Architecture Decision Records (ADR)

This directory captures the *why* behind significant engineering decisions for
this repository. Each record is immutable once accepted: instead of editing a
past decision, add a new record that supersedes it.

We use a lightweight [MADR](https://adr.github.io/madr/)-style format. Records
are numbered sequentially and never reused.

## Index

| ID | Title | Status |
|----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-uv-flit-dependency-layering.md) | uv + flit toolchain and dependency layering | Accepted |
| [0003](0003-layered-ci-and-perf-gate.md) | Layered CI with a performance regression gate | Accepted |
| [0004](0004-observability-as-optional-extension.md) | Observability as an opt-in extension, never in core | Accepted |
| [0005](0005-semver-release-and-rollback.md) | Semantic-versioned release governance and rollback | Accepted |

## Writing a new ADR

1. Copy the structure of an existing record.
2. Use the next free number.
3. Set `Status` to `Proposed`, open a PR, and move to `Accepted` once merged.
4. If it replaces an earlier decision, set the old record's status to
   `Superseded by NNNN` and link both ways.

Sections: **Context** (forces at play) → **Decision** (what we chose) →
**Consequences** (trade-offs, good and bad) → **Alternatives considered**.
