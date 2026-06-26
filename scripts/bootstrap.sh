#!/usr/bin/env bash
#
# Clone-to-release one-click helper for the Flask repo.
#
# Wraps the existing toolchain (uv + tox + pre-commit) into named modes so a
# fresh contributor can go from `git clone` to a verified build without
# memorizing the exact `uv run --locked --no-default-groups --group <g> tox ...`
# incantations. Everything this script does is also exposed as plain `make`
# targets (see the top-level Makefile).
#
# Usage:
#   ./scripts/bootstrap.sh check        # default: verify env + smoke + style (fast)
#   ./scripts/bootstrap.sh full         # check + full test matrix + typing + docs
#   ./scripts/bootstrap.sh perf         # run perf benchmarks vs baseline
#   ./scripts/bootstrap.sh release      # dry-run the release pipeline (no tag, no PyPI)
#
# Exit non-zero if any required tool is missing or a gated step fails.

set -euo pipefail

MODE="${1:-check}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m!!\033[0m %s\n' "$*" >&2; }

require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "required tool '$1' not found on PATH."
        err "install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
}

check_prereqs() {
    local missing=0
    for tool in git uv; do
        require "$tool" || missing=1
    done
    # tox / pre-commit are provided by the uv dev group; they are not required
    # to exist globally -- `uv run` resolves them from the lock.
    return "$missing"
}

sync_env() {
    log "uv sync --frozen (dev + tests + typing + pre-commit groups)"
    uv sync --frozen
}

run_check() {
    check_prereqs
    sync_env
    log "smoke gate: tox run -e smoke"
    uv run --locked --no-default-groups --group dev tox run -e smoke
    log "style gate: tox run -e style (pre-commit on all files)"
    uv run --locked --no-default-groups --group dev tox run -e style
    log "build verification: uv build"
    uv build --quiet
    log "check mode complete. Next: ./scripts/bootstrap.sh full"
}

run_full() {
    run_check
    log "full test matrix: tox run"
    uv run --locked --no-default-groups --group dev tox run
    log "typing: tox run -e typing"
    uv run --locked --no-default-groups --group dev tox run -e typing
    log "docs build (-W): tox run -e docs"
    uv run --locked --no-default-groups --group dev tox run -e docs
    log "full mode complete."
}

run_perf() {
    check_prereqs
    sync_env
    log "perf benchmarks vs baseline (advisory)"
    uv run --locked --no-default-groups --group dev tox run -e perf
}

run_release() {
    check_prereqs
    sync_env
    log "release dry-run (no tags, no PyPI): changes.py bump --level auto --dry-run"
    python scripts/changes.py bump --level auto --dry-run
    log "to actually release, run: python scripts/changes.py bump --level <auto|major|minor|patch> --apply"
    log "or trigger the Release workflow (workflow_dispatch, dry_run=true by default)."
}

case "$MODE" in
    check) run_check ;;
    full) run_full ;;
    perf) run_perf ;;
    release) run_release ;;
    *)
        err "unknown mode '$MODE'. Use: check | full | perf | release"
        exit 2
        ;;
esac
