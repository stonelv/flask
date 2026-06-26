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
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(\.?(a|b|rc|post)[0-9]*)?$'; then
    echo "Error: '$VERSION' is not a valid release version"
    echo "Expected: X.Y.Z or X.Y.ZaN / X.Y.ZbN / X.Y.ZrcN"
    echo "(dev versions are not releasable)"
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
    if [ "$DRY_RUN" = false ]; then
        read -r -p "Continue? [y/N] " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            exit 1
        fi
    fi
fi

echo "==> Releasing Flask $VERSION"
echo "    Branch: $BRANCH"
echo "    Dry run: $DRY_RUN"
echo ""

# Step 1: Check for changelog fragments
FRAGMENT_COUNT=$(find changelog.d -name '*.rst' ! -name '_template.rst' 2>/dev/null | wc -l)
if [ "$FRAGMENT_COUNT" -eq 0 ]; then
    echo "Warning: no changelog fragments found in changelog.d/"
    echo "         The release will have an empty changelog section."
    if [ "$DRY_RUN" = false ]; then
        read -r -p "Continue anyway? [y/N] " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            exit 1
        fi
    fi
else
    echo "  Found $FRAGMENT_COUNT changelog fragment(s)"
fi

# Step 2: Generate changelog
echo "==> Step 1/6: Generating changelog..."
if [ "$DRY_RUN" = true ]; then
    uv run towncrier build --draft --version "$VERSION" || true
else
    uv run towncrier build --yes --version "$VERSION" || true
fi

# Step 3: Update version in pyproject.toml
echo "==> Step 2/6: Updating version to $VERSION..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would update pyproject.toml: version = \"$VERSION\""
else
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
fi

# Step 4: Update lock file
echo "==> Step 3/6: Updating lock file..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would run: uv lock"
else
    uv lock 2>/dev/null || true
fi

# Step 5: Build and verify artifacts
echo "==> Step 4/6: Building distribution..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would run: uv build"
    echo "  Would verify: wheel and sdist exist in dist/"
else
    uv build
    # Verify both artifacts exist
    WHEEL_COUNT=$(find dist -name '*.whl' 2>/dev/null | wc -l)
    SDIST_COUNT=$(find dist -name '*.tar.gz' 2>/dev/null | wc -l)
    if [ "$WHEEL_COUNT" -eq 0 ] || [ "$SDIST_COUNT" -eq 0 ]; then
        echo "Error: build failed — missing wheel or sdist in dist/"
        exit 1
    fi
    echo "  ✓ wheel: $(ls dist/*.whl)"
    echo "  ✓ sdist: $(ls dist/*.tar.gz)"
    # Clean up — CI will rebuild from the tagged commit
    rm -rf dist/
fi

# Step 6: Commit
echo "==> Step 5/6: Committing release..."
if [ "$DRY_RUN" = true ]; then
    echo "  Would commit: 'Release $VERSION'"
else
    git add -A
    git commit -m "Release $VERSION"
fi

# Step 7: Tag
echo "==> Step 6/6: Creating tag..."
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
    echo "Rollback (before push):"
    echo "  git tag -d $VERSION && git reset --hard HEAD~1"
    echo ""
    echo "Rollback (after push):"
    echo "  git push origin :refs/tags/$VERSION"
    echo "  git revert HEAD && git push"
    echo "  # If published to PyPI: yank via https://pypi.org/manage/project/Flask/"
    echo ""
    echo "Post-release: bump to next dev version:"
    NEXT_DEV="${VERSION}.dev"
    echo "  sed -i 's/^version = \".*\"/version = \"$NEXT_DEV\"/' pyproject.toml"
    echo "  uv lock && git add -A && git commit -m 'Start ${VERSION}+1 development'"
fi
