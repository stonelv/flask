#!/bin/bash
set -e
# Install uv if the base image doesn't provide it, then bootstrap the dev
# environment via the shared script (uv sync + pre-commit install). This keeps
# the devcontainer consistent with the project's uv-based workflow and replaces
# the obsolete requirements/dev.txt + pip flow.
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
exec ./scripts/bootstrap.sh
