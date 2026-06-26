# 0005 — Semantic-versioned release governance and rollback

- Status: Accepted
- Date: 2026-06-23

## Context

Releases already flow through `publish.yaml`: a tag push triggers a reproducible
`uv build`, a **draft** GitHub release, and PyPI publication via OIDC trusted
publishing. What was missing was *governance around* that pipeline:

- No mechanical link between a version bump and a changelog entry.
- No documented mapping from change type to a SemVer increment.
- No written rollback procedure when a bad release reaches PyPI.

Flask maintains `CHANGES.rst` **by hand** using Sphinx roles (`:pr:`,
`:issue:`). Auto-generating and overwriting it would break that long-standing
convention and lose the human-curated narrative.

## Decision

We add a governance layer *around* the existing pipeline, without replacing it:

- **Change tiering**: PR labels map to SemVer — `breaking` → major,
  `feature` → minor, `fix` → patch. `scripts/release.sh` reads commit history to
  *suggest* the next version (advisory, never enforced).
- **Changelog guard** (`release-guard` job in `ci-fast.yaml`): if the version in
  `pyproject.toml` changed but `CHANGES.rst` did not, fail; lint that new
  entries carry the expected role formatting. This validates the hand-written
  changelog rather than generating it.
- **Release wizard** (`scripts/release.sh`): verifies a clean working tree, a
  valid SemVer version, and a matching `CHANGES.rst` section, then creates an
  annotated tag. Defaults to `--dry-run`.
- **Rollback runbook** (`docs/release-process.rst`): PyPI versions are
  immutable, so recovery is `pip`-yank the bad version, publish a fixed patch,
  and (if needed) revert the tag. The draft-release step is the pre-publish
  safety net — a human confirms before anything goes public.

## Consequences

- Good: version/changelog stay in lockstep; contributors share one definition of
  "what bumps what"; on-call has a written path out of a bad release.
- Cost: the guard can block a PR that legitimately changes the version without a
  user-facing note (rare; resolved by adding the note).

## Alternatives considered

- **Conventional Commits + fully automated changelog** (e.g.
  semantic-release): powerful, but overwrites the curated `CHANGES.rst` and
  imposes commit-message rules the project does not use. Rejected in favour of
  validate-don't-generate.
- **No guard, rely on review**: human reviewers routinely miss a missing
  changelog entry; a cheap mechanical check is worth it.
