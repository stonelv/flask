#!/usr/bin/env bash
# Flask release script — automates version bump, changelog, and tagging.
#
# Usage:
#   scripts/release.sh <version>          # e.g. scripts/release.sh 3.2.0
#   scripts/release.sh --dry-run <version>
#
# Prerequisites:
#   - Clean git working directory
#   - On the main or stable branch
#   - uv and towncrier installed (uv sync)
set -euo pipefail

DRY_RUN=false
VERSION=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] <version>"
            echo ""
            echo "  version    Semantic version (e.g. 3.2.0)"
            echo "  --dry-run  Show what would happen without making changes"
            exit 0
            ;;
        *) VERSION="$arg" ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "Error: version argument required"
    echo "Usage: $0 [--dry-run] <version>"
    exit 1
fi

# Validate semantic version format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(\.?(a|b|rc|dev|post)[0-9]*)?$'; then
    echo "Error: '$VERSION' is not a valid version format"
    echo "Expected: X.Y.Z or X.Y.Z.devN / X.Y.ZaN / X.Y.ZbN / X.Y.ZrcN"
    exit 1
fi

# Check for clean working directory
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: working directory is not clean"
    git status --short
    exit 1
fi

# Check branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "stable" ]; then
    echo "Warning: releasing from branch '$BRANCH' (expected main or stable)"
    read -r -p "Continue? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        exit 1
    fi
fi

echo "==> Releasing Flask $VERSION"
echo "    Branch: $BRANCH"
echo "    Dry run: $DRY_RUN"
echo ""

# Step 1: Generate changelog
echo "==> Step 1: Generating changelog..."
if [ "$DRY_RUN" = true ]; then
    uv run towncrier build --draft --version "$VERSION" 2>/dev/null || echo "  (no fragments found)"
else
    uv run towncrier build --yes --version "$VERSION" 2>/dev/null || echo "  (no fragments to process)"
fi

# Step 2: Update version in pyproject.toml
echo "==> Step 2: Updating version to $VERSION..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would update pyproject.toml: version = \"$VERSION\""
else
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
fi

# Step 3: Update lock file
echo "==> Step 3: Updating lock file..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would run: uv lock"
else
    uv lock 2>/dev/null || true
fi

# Step 4: Commit
echo "==> Step 4: Committing release..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would commit: 'Release $VERSION'"
else
    git add -A
    git commit -m "Release $VERSION"
fi

# Step 5: Tag
echo "==> Step 5: Creating tag..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would create tag: $VERSION"
else
    git tag -a "$VERSION" -m "Release $VERSION"
fi

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "==> Dry run complete. No changes were made."
else
    echo "==> Release $VERSION prepared successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Review the commit:  git log -1 --stat"
    echo "  2. Push to trigger CI: git push origin $BRANCH --follow-tags"
    echo ""
    echo "Rollback (if needed):"
    echo "  git tag -d $VERSION"
    echo "  git reset --hard HEAD~1"
    echo "  git push origin :refs/tags/$VERSION  # if already pushed"
fi
