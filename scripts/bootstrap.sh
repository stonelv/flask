#!/usr/bin/env bash
# Flask bootstrap script — from a fresh clone to passing tests.
#
# Usage: bash scripts/bootstrap.sh
set -euo pipefail

echo "==> Flask Development Setup"
echo ""

# Step 1: Ensure uv is available
if ! command -v uv &>/dev/null; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> uv version: $(uv --version)"

# Step 2: Install dependencies
echo "==> Installing dependencies..."
uv sync

# Step 3: Install pre-commit hooks
echo "==> Installing pre-commit hooks..."
uv run pre-commit install --install-hooks

# Step 4: Run smoke tests
echo "==> Running smoke tests..."
uv run pytest tests/test_basic.py -x -q --tb=short 2>&1 | tail -5

echo ""
echo "✓ Setup complete!"
echo ""
echo "Available commands:"
echo "  make help          Show all development commands"
echo "  make lint          Run linting"
echo "  make type          Run type checking"
echo "  make test          Run tests"
echo "  make bench         Run benchmarks"
echo "  make docs          Build documentation"
echo ""
echo "Or use: bash scripts/dev.sh <command>"
