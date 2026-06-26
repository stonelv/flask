#!/usr/bin/env bash
# Run the full local quality gate: format, lint, type-check, tests + coverage.
# Mirrors what CI enforces, so a green `make dev` means a green CI is likely.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> ruff format"
uv run --no-default-groups --group dev ruff format

echo "==> ruff lint (with --fix)"
uv run --no-default-groups --group dev ruff check

echo "==> type checking (mypy + pyright)"
uv run --no-default-groups --group dev tox run -e typing

echo "==> tests with coverage"
uv run --group tests coverage run -m pytest -q
uv run --group tests coverage report

echo "==> all checks passed"
