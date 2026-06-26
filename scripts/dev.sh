#!/usr/bin/env bash
# Flask development helper script
# Usage: bash scripts/dev.sh <command>
set -euo pipefail

UV_RUN="uv run --locked --no-default-groups"

usage() {
    echo "Flask Development Commands"
    echo "=========================="
    echo "  setup      Install all development dependencies"
    echo "  lint       Run linting (ruff check + format)"
    echo "  type       Run type checking (mypy + pyright)"
    echo "  test       Run tests on default Python version"
    echo "  test-all   Run tests on all Python versions"
    echo "  bench      Run benchmarks"
    echo "  docs       Build documentation"
    echo "  clean      Remove build artifacts"
    echo "  changelog  Preview upcoming changelog"
}

cmd_setup() {
    echo "==> Installing dependencies..."
    uv sync
    echo "==> Installing pre-commit hooks..."
    uv run pre-commit install --install-hooks
    echo "✓ Setup complete."
}

cmd_lint() {
    $UV_RUN --group dev tox run -e style
}

cmd_type() {
    $UV_RUN --group dev tox run -e typing
}

cmd_test() {
    $UV_RUN --group dev tox run -e py -- "$@"
}

cmd_test_all() {
    $UV_RUN --group dev tox run
}

cmd_bench() {
    $UV_RUN --group dev tox run -e bench -- "$@"
}

cmd_docs() {
    $UV_RUN --group dev tox run -e docs
}

cmd_clean() {
    rm -rf dist/ build/ docs/_build/ .tox/ .mypy_cache/ .pyright/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete 2>/dev/null || true
    echo "✓ Cleaned."
}

cmd_changelog() {
    $UV_RUN --group dev towncrier build --draft --version=Unreleased
}

case "${1:-help}" in
    setup)     cmd_setup ;;
    lint)      cmd_lint ;;
    type)      cmd_type ;;
    test)      shift; cmd_test "$@" ;;
    test-all)  cmd_test_all ;;
    bench)     shift; cmd_bench "$@" ;;
    docs)      cmd_docs ;;
    clean)     cmd_clean ;;
    changelog) cmd_changelog ;;
    help|*)    usage ;;
esac
