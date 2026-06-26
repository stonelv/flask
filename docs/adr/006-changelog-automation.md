# ADR-006: Automated Changelog Generation

## Status

Accepted

## Context

Flask's changelog maintenance was manual and error-prone:
- Developers often forgot to update `CHANGES.rst`
- Inconsistent formatting across entries
- Time-consuming to compile release notes
- Missing attribution for contributors

## Decision

Implement automated changelog generation using:

1. **Conventional Commits**: Standardized commit message format
2. **PR Labels**: Categorize changes (feature, fix, breaking, etc.)
3. **Auto-generation script**: `scripts/generate_changelog.py`
4. **CI enforcement**: Require changelog entry for PRs

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `breaking`: Breaking changes

Example:
```
feat(observability): Add OpenTelemetry integration

Implement distributed tracing, metrics, and request ID tracking.
Supports OTLP, console, and none exporters.

Closes #5123
```

## Implementation

### Changelog Generator Script

```python
# scripts/generate_changelog.py
"""
Generate changelog from git history and PR labels.

Usage:
    python scripts/generate_changelog.py
    python scripts/generate_changelog.py --from v3.1.0
    python scripts/generate_changelog.py --output CHANGES.md
"""

import subprocess
import re
from datetime import datetime
from collections import defaultdict

CHANGELOG_SECTIONS = {
    'breaking': '💥 Breaking Changes',
    'feat': '✨ Features',
    'fix': '🐛 Bug Fixes',
    'perf': '⚡ Performance',
    'refactor': '♻️ Refactoring',
    'docs': '📚 Documentation',
    'test': '✅ Tests',
    'chore': '🔧 Maintenance',
}

def get_commits(from_ref='HEAD~1', to_ref='HEAD'):
    """Get commits between refs"""
    result = subprocess.run(
        ['git', 'log', f'{from_ref}..{to_ref}',
         '--pretty=format:%H|%s|%an|%ae'],
        capture_output=True, text=True, check=True
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue

        hash_, subject, author, email = line.split('|')

        # Parse conventional commit
        match = re.match(
            r'^(feat|fix|docs|style|refactor|perf|test|chore|breaking)'
            r'(?:\(([^)]+)\))?: (.+)$',
            subject
        )

        if match:
            type_, scope, description = match.groups()
            commits.append({
                'hash': hash_[:8],
                'type': type_,
                'scope': scope,
                'description': description,
                'author': author,
                'breaking': type_ == 'breaking' or 'BREAKING CHANGE' in subject
            })

    return commits

def generate_changelog(from_ref='v3.1.0', to_ref='HEAD'):
    """Generate changelog markdown"""
    commits = get_commits(from_ref, to_ref)

    # Group by type
    grouped = defaultdict(list)
    for commit in commits:
        grouped[commit['type']].append(commit)

    # Generate markdown
    lines = []
    lines.append(f"## {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    for type_, section_name in CHANGELOG_SECTIONS.items():
        if type_ not in grouped:
            continue

        lines.append(f"### {section_name}")
        lines.append("")

        for commit in grouped[type_]:
            scope = f"**{commit['scope']}:** " if commit['scope'] else ""
            lines.append(
                f"- {scope}{commit['description']} "
                f"([#{commit['hash']}](https://github.com/pallets/flask/commit/{commit['hash']}))"
            )

        lines.append("")

    return '\n'.join(lines)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='from_ref', default='v3.1.0')
    parser.add_argument('--to', dest='to_ref', default='HEAD')
    parser.add_argument('--output', default='CHANGES.md')

    args = parser.parse_args()

    changelog = generate_changelog(args.from_ref, args.to_ref)

    with open(args.output, 'w') as f:
        f.write(changelog)

    print(f"Generated changelog: {args.output}")
```

### CI Enforcement

Require changelog entry in PRs:

```yaml
# .github/workflows/changelog.yml
name: Changelog Check

on:
  pull_request:
    types: [opened, synchronize, labeled]

jobs:
  check-changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check for changelog entry
        run: |
          # Check if PR modifies CHANGES.rst
          if git diff --name-only origin/main | grep -q "CHANGES.rst"; then
            echo "✓ CHANGES.rst modified"
            exit 0
          fi

          # Check if PR has skip-changelog label
          if [[ "${{ contains(github.event.pull_request.labels.*.name, 'skip-changelog') }}" == "true" ]]; then
            echo "✓ skip-changelog label present"
            exit 0
          fi

          # Fail if no changelog entry
          echo "✗ No changelog entry found"
          echo "Please update CHANGES.rst or add 'skip-changelog' label"
          exit 1
```

### PR Template

Add changelog reminder to PR template:

```markdown
## Checklist

- [ ] I have updated `CHANGES.rst` with my changes
- [ ] I have added tests for my changes
- [ ] I have updated documentation

## Changelog Entry

<!-- Add your changelog entry here -->

```rst
- Added feature X (#1234)
```
```

## Consequences

### Positive
- **Consistent format**: All entries follow same structure
- **Time savings**: Automatic compilation of release notes
- **Complete history**: No missing changes
- **Attribution**: Automatic contributor credits
- **Categorization**: Easy to scan by type (features, fixes, etc.)

### Negative
- **Learning curve**: Developers must learn conventional commits
- **Enforcement overhead**: CI checks add friction
- **Tool dependency**: Relies on script working correctly
- **Manual review still needed**: Quality control required

### Mitigations
- Provide commit message examples
- Allow `skip-changelog` label for trivial changes
- Document conventions in CONTRIBUTING.md
- Review generated changelog before release

## Example Output

Generated `CHANGES.rst`:

```rst
Version 3.2.0
=============

Released on 2024-01-15

✨ Features
-----------

- **observability:** Add OpenTelemetry integration for distributed tracing and metrics
  (`#5150 <https://github.com/pallets/flask/commit/a1b2c3d4>`_)

- **cli:** Add `flask debug` command for quick debugging
  (`#5123 <https://github.com/pallets/flask/commit/e5f6g7h8>`_)

🐛 Bug Fixes
------------

- **sessions:** Fix session expiration in timezone-aware environments
  (`#5145 <https://github.com/pallets/flask/commit/i9j0k1l2>`_)

- **routing:** Handle trailing slashes correctly in blueprint routes
  (`#5138 <https://github.com/pallets/flask/commit/m3n4o5p6>`_)

⚡ Performance
--------------

- **routing:** Optimize URL matching for parameterized routes (15% faster)
  (`#5142 <https://github.com/pallets/flask/commit/q7r8s9t0>`_)

💥 Breaking Changes
-------------------

- **sessions:** Remove deprecated `session.permanent` setter
  (`#5100 <https://github.com/pallets/flask/commit/u1v2w3x4>`_)

  **Migration**: Use `session.permanent = True` instead of `session.permanent(True)`
```

## Workflow Integration

### Development Workflow

1. **Write code**: Implement feature/fix
2. **Commit with conventional message**:
   ```bash
   git commit -m "feat(routing): Add support for regex patterns"
   ```
3. **Create PR**: CI checks for changelog
4. **Update CHANGES.rst**: Add entry or use `skip-changelog`
5. **Merge**: Change is recorded

### Release Workflow

1. **Generate changelog**:
   ```bash
   python scripts/generate_changelog.py --from v3.1.0 --output CHANGES-new.md
   ```

2. **Review and edit**:
   ```bash
   vim CHANGES-new.md  # Polish descriptions
   ```

3. **Prepend to CHANGES.rst**:
   ```bash
   cat CHANGES-new.md CHANGES.rst > CHANGES-updated.rst
   mv CHANGES-updated.rst CHANGES.rst
   ```

4. **Commit and tag**:
   ```bash
   git add CHANGES.rst
   git commit -m "Release 3.2.0"
   git tag v3.2.0
   ```

## Alternatives Considered

1. **Manual only**: Current approach, error-prone
2. **Git log only**: No categorization or formatting
3. **Third-party tools (semantic-release)**: More features but external dependency
4. **PR-only (no commits)**: Loses information from direct commits

## References

- Script: `scripts/generate_changelog.py`
- Conventional Commits: https://www.conventionalcommits.org/
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`
- CI workflow: `.github/workflows/changelog.yml`
