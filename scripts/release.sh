#!/usr/bin/env bash
# Guided, SemVer-aware release wizard. Dry-run by default: it validates and
# *suggests*, and only creates a tag when given --execute.
#
# Usage:
#   scripts/release.sh                # dry-run: validate + suggest next version
#   scripts/release.sh --execute      # create the annotated tag for pyproject version
#
# Checks performed:
#   1. working tree is clean
#   2. version in pyproject.toml is valid SemVer (no .dev suffix)
#   3. CHANGES.rst has a section for that version
#   4. suggests a SemVer bump from commit messages since the last tag
set -euo pipefail

cd "$(dirname "$0")/.."

EXECUTE=0
[[ "${1:-}" == "--execute" ]] && EXECUTE=1

fail() { echo "error: $*" >&2; exit 1; }

# 1. clean tree
if [[ -n "$(git status --porcelain)" ]]; then
    fail "working tree is not clean; commit or stash first"
fi

# 2. read + validate version
VERSION="$(uv run --no-default-groups python -c '
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["project"]["version"])
')"
echo "==> pyproject version: ${VERSION}"

if [[ "$VERSION" == *dev* ]]; then
    fail "version '${VERSION}' is a .dev version; set a final version before releasing"
fi
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-].+)?$ ]]; then
    fail "version '${VERSION}' is not valid SemVer (expected MAJOR.MINOR.PATCH)"
fi

# 3. changelog section present
if ! grep -qE "^Version ${VERSION//./\\.}\b" CHANGES.rst; then
    fail "CHANGES.rst has no 'Version ${VERSION}' section"
fi
echo "==> CHANGES.rst has a section for ${VERSION}"

# 4. suggest a bump from commits since the last tag
LAST_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
RANGE="${LAST_TAG:+${LAST_TAG}..}HEAD"
LOG="$(git log --format=%s%x00%b "$RANGE" 2>/dev/null || true)"
TIER="patch"
if grep -qiE 'breaking|BREAKING CHANGE|! ?:' <<<"$LOG"; then
    TIER="major"
elif grep -qiE '^(feat|feature)(\(|:)|\bfeature\b' <<<"$LOG"; then
    TIER="minor"
fi
echo "==> commits since ${LAST_TAG:-<start>} suggest a '${TIER}' release"

TAG="${VERSION}"
if [[ "$EXECUTE" -eq 1 ]]; then
    echo "==> creating annotated tag ${TAG}"
    git tag -a "$TAG" -m "Release ${VERSION}"
    echo "==> tag created. push it to trigger publish.yaml:"
    echo "       git push origin ${TAG}"
else
    echo
    echo "==> dry-run only. all checks passed. to tag and release:"
    echo "       scripts/release.sh --execute && git push origin ${TAG}"
fi
