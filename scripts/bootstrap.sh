#!/usr/bin/env bash
# Bootstrap a development environment from a fresh clone, using uv.
#
# Replaces the older pip + requirements/dev.txt flow. Idempotent: safe to run
# repeatedly. After this, `make dev` runs the full local quality gate.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
    echo "error: 'uv' is not installed." >&2
    echo "install it from https://docs.astral.sh/uv/ and re-run." >&2
    exit 1
fi

echo "==> syncing environment (uv.lock, default groups)"
uv sync --locked

echo "==> installing pre-commit hooks"
uv run --no-default-groups --group pre-commit pre-commit install --install-hooks

cat <<'EOF'

==> done.
   next steps:
     make dev      # format, lint, type-check, test with coverage
     make test     # run the test suite on the current interpreter
     make perf     # run benchmarks and compare against the baseline
     make release  # guided, dry-run-by-default release wizard
EOF
