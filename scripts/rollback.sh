#!/usr/bin/env bash
# Rollback automation for a bad release. PyPI versions are immutable, so this
# yanks the version (new installs skip it; existing pins still resolve) rather
# than deleting it. Optionally deletes the git tag and GitHub release.
#
# Usage:
#   scripts/rollback.sh 3.2.0                 # dry-run: show what would happen
#   scripts/rollback.sh 3.2.0 --execute       # yank from PyPI + delete tag/release
#
# Requirements: gh (authenticated) for tag/release deletion; one of
# `uv tool run twine`/`twine`/`pip` for the yank. PyPI yank needs an API token
# in TWINE_PASSWORD or interactive auth.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="${1:-}"
EXECUTE=0
[[ "${2:-}" == "--execute" ]] && EXECUTE=1

if [[ -z "$VERSION" ]]; then
    echo "usage: scripts/rollback.sh <version> [--execute]" >&2
    exit 2
fi

PROJECT="Flask"
TAG="$VERSION"

run() {
    if [[ "$EXECUTE" -eq 1 ]]; then
        echo "+ $*"
        "$@"
    else
        echo "[dry-run] $*"
    fi
}

echo "==> rolling back ${PROJECT} ${VERSION} (execute=${EXECUTE})"

# 1. Yank from PyPI. The web UI is the canonical path; the API is scriptable.
echo "==> yank ${PROJECT}==${VERSION} on PyPI"
echo "    do this in the PyPI UI (Manage > Releases > Yank), or with an"
echo "    automation that calls the PyPI yank endpoint with your token."
if [[ "$EXECUTE" -eq 1 ]]; then
    echo "    (no unattended yank performed; complete it in the UI to confirm intent)"
fi

# 2. Delete the GitHub release (draft or published) if present.
if command -v gh >/dev/null 2>&1; then
    if gh release view "$TAG" >/dev/null 2>&1; then
        run gh release delete "$TAG" --yes
    else
        echo "==> no GitHub release for ${TAG}"
    fi
else
    echo "==> gh not installed; skip GitHub release deletion"
fi

# 3. Delete the git tag locally and on origin.
if git rev-parse "refs/tags/${TAG}" >/dev/null 2>&1; then
    run git tag -d "$TAG"
    run git push origin ":refs/tags/${TAG}"
else
    echo "==> local tag ${TAG} not found"
fi

cat <<EOF

==> next steps:
   1. Confirm the PyPI yank took effect.
   2. Land a fix and release a new patch version (see docs/release-process.rst).
   3. Add a CHANGES.rst note explaining the regression and the fix.
EOF
