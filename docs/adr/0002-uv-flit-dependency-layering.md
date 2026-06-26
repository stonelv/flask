# 0002 — uv + flit toolchain and dependency layering

- Status: Accepted
- Date: 2026-06-23

## Context

Flask is a widely-depended-on library, so its dependency story must be both
reproducible for contributors and minimal for downstream users. The repository
already standardises on:

- **flit** (`flit_core`) as the build backend — pure-Python, declarative,
  no `setup.py`.
- **uv** for environment management and a committed `uv.lock`.
- **ruff** (format + lint), **mypy --strict** + **pyright**, **codespell** for
  quality gates, orchestrated by **tox** and **pre-commit**.

This record documents the *existing* dependency-layering strategy so it is not
accidentally undone, and explains why we did not "refactor" it.

## Decision

Dependencies are layered into three concentric rings:

1. **Runtime** (`[project.dependencies]` + `[project.optional-dependencies]`
   `async`, `dotenv`): the only thing downstream users install. Kept minimal;
   specified with lower bounds (`>=`).
2. **Development groups** (`[dependency-groups]`: `dev`, `docs`, `docs-auto`,
   `pre-commit`, `tests`, `typing`, `gha-update`): never shipped to users,
   selected per task. `tool.uv.default-groups` installs the common set.
3. **Locking / compatibility envelope**: `uv.lock` pins exact dev versions for
   reproducibility, while tox proves the runtime envelope holds at both ends —
   `tests-min` installs the lowest supported dependency versions and `tests-dev`
   installs upstream `main` of each Pallets dependency.

New tooling adds a *new group* (e.g. `benchmarks`) rather than widening runtime
deps or the default install. The OpenTelemetry example ships its own
`pyproject.toml` so its heavy deps never touch this lock (see ADR 0004).

## Consequences

- Good: downstream install stays tiny; contributors get a reproducible env via
  `uv sync`; the min/dev tox envs catch both "we used a too-new API" and "an
  upstream change broke us" before release.
- Cost: contributors must learn `uv` + dependency groups; adding a tool means
  choosing the right ring.

## Alternatives considered

- **requirements/*.txt + pip** (the older devcontainer flow): superseded by uv;
  the stale `requirements/dev.txt` reference is removed by the new
  `scripts/bootstrap.sh`.
- **Poetry / PDM**: capable, but uv is already adopted and faster; no reason to
  churn.
- **Pinning runtime deps with `==`**: would break downstream resolution; lower
  bounds + the min/dev tox matrix is the correct tool for a library.
