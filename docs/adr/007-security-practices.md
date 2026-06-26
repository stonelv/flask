# ADR-007: Security Best Practices and Dependency Management

## Status

Accepted

## Context

Flask is a widely-used framework with security-critical applications. Recent concerns:

- **Supply chain attacks**: Compromised dependencies
- **Vulnerability disclosure**: Delayed security patches
- **Secret management**: Hardcoded credentials in examples
- **Dependency bloat**: Unnecessary dependencies increase attack surface

## Decision

Implement comprehensive security practices:

1. **Dependency pinning**: Lock all dependency versions
2. **Vulnerability scanning**: Automated security audits
3. **Secret detection**: Prevent accidental credential commits
4. **Minimal dependencies**: Reduce attack surface
5. **Security policy**: Clear vulnerability reporting process

### Dependency Pinning Strategy

**Production dependencies**: Minimum version ranges (allow patches)
```toml
dependencies = [
    "werkzeug>=3.1.0,<4.0.0",
    "jinja2>=3.1.2,<4.0.0",
    "click>=8.1.3,<9.0.0",
]
```

**Development dependencies**: Exact versions (reproducible builds)
```toml
[dependency-groups]
dev = [
    "pytest==8.3.4",
    "ruff==0.8.6",
    "mypy==1.14.1",
]
```

**Lock file**: Commit `uv.lock` for exact reproducibility
```bash
uv lock
git add uv.lock
```

## Implementation

### Dependency Scanning

```yaml
# .github/workflows/security.yml
name: Security Audit

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          pip install -e .[dev]

      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit

      - name: Check for known vulnerabilities
        uses: pypa/gh-action-pip-audit@v1.0.8
        with:
          inputs: requirements.txt
```

### Secret Detection

Pre-commit hook with `detect-secrets`:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
```

Generate baseline:
```bash
detect-secrets scan > .secrets.baseline
git add .secrets.baseline
```

Audit detected secrets:
```bash
detect-secrets audit .secrets.baseline
```

### Dependency Review

GitHub Action to review PR dependency changes:

```yaml
# .github/workflows/dependency-review.yml
name: Dependency Review

on:
  pull_request:
    paths:
      - 'pyproject.toml'
      - 'uv.lock'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Dependency Review
        uses: actions/dependency-review-action@v3
        with:
          fail-on-severity: moderate
          deny-licenses: GPL-3.0, AGPL-3.0
```

### Security Policy

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.2.x   | :white_check_mark: |
| 3.1.x   | :white_check_mark: |
| 3.0.x   | :x:                |
| < 3.0   | :x:                |

## Reporting a Vulnerability

**DO NOT** open a public issue.

Email: security@palletsprojects.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will:
- Acknowledge within 24 hours
- Provide timeline within 72 hours
- Credit you in security advisory (unless anonymous)
- Release fix within 7 days for critical issues

## Security Best Practices

### Session Security

```python
# ✓ Good: Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
)
```

### Secret Key Management

```python
# ✗ Bad: Hardcoded secret
app.secret_key = 'super-secret-key-123'

# ✓ Good: Environment variable
import os
app.secret_key = os.environ.get('SECRET_KEY')

# ✓ Better: Generated secret
import secrets
app.secret_key = secrets.token_hex(32)
```

### Input Validation

```python
# ✗ Bad: No validation
@app.route('/user/<user_id>')
def get_user(user_id):
    user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
    return user

# ✓ Good: Type validation
@app.route('/user/<int:user_id>')
def get_user(user_id):
    user = db.get(User, user_id)
    if not user:
        abort(404)
    return user
```

### CORS Configuration

```python
# ✗ Bad: Allow all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# ✓ Good: Whitelist specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://example.com", "https://app.example.com"]
    }
})
```
```

## Dependency Minimization

### Core Dependencies

Flask maintains minimal core dependencies:

| Package | Purpose | Justification |
|---------|---------|---------------|
| werkzeug | WSGI toolkit | Essential for Flask |
| jinja2 | Templating | Core feature |
| click | CLI framework | flask CLI |
| itsdangerous | Signing | Secure cookies |
| markupsafe | HTML escaping | Security |
| blinker | Signals | Event system |

### Optional Dependencies

Features requiring additional packages:

```toml
[project.optional-dependencies]
async = ["asgiref>=3.2"]
dotenv = ["python-dotenv"]
observability = [
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
]
```

Users install only what they need:
```bash
pip install Flask              # Core only
pip install Flask[async]       # + async support
pip install Flask[observability]  # + tracing/metrics
```

## Consequences

### Positive
- **Reduced risk**: Fewer vulnerabilities in dependencies
- **Early detection**: Automated scanning catches issues
- **No secret leaks**: Pre-commit prevents accidental commits
- **Transparency**: Clear security policy builds trust
- **Minimal attack surface**: Fewer dependencies = fewer vulnerabilities

### Negative
- **Maintenance burden**: Regular security audits required
- **Update friction**: Pinned versions may lag behind
- **False positives**: Secret detection may flag valid code
- **Developer overhead**: More steps in development workflow

### Mitigations
- Automate security checks in CI
- Use Dependabot for dependency updates
- Allow baseline exceptions for false positives
- Document security practices clearly

## Security Checklist

For each release:

- [ ] Run `pip-audit` on all dependencies
- [ ] Review `uv.lock` for new dependencies
- [ ] Check for known vulnerabilities in core deps
- [ ] Verify no secrets in codebase
- [ ] Update security policy if needed
- [ ] Test security features (sessions, CSRF, etc.)
- [ ] Review security-related PRs since last release

## Incident Response Plan

### Vulnerability Reported

1. **Acknowledge**: Respond within 24 hours
2. **Assess**: Determine severity (CVSS score)
3. **Plan**: Develop fix and timeline
4. **Implement**: Create patch in private fork
5. **Test**: Verify fix doesn't break functionality
6. **Release**: Publish patch version
7. **Disclose**: Publish security advisory
8. **Credit**: Thank reporter (unless anonymous)

### Severity Levels

| Severity | CVSS | Response Time | Example |
|----------|------|---------------|---------|
| Critical | 9.0-10.0 | 24 hours | Remote code execution |
| High | 7.0-8.9 | 3 days | Authentication bypass |
| Medium | 4.0-6.9 | 7 days | Information disclosure |
| Low | 0.1-3.9 | Next release | Minor issue |

## Alternatives Considered

1. **No security policy**: Risky for production use
2. **Manual audits only**: Slow and error-prone
3. **Third-party security service**: Expensive
4. **Automatic updates**: Risk of breaking changes

## References

- Security policy: `SECURITY.md`
- CI workflow: `.github/workflows/security.yml`
- Pre-commit config: `.pre-commit-config.yaml`
- Dependabot config: `.github/dependabot.yml`
- pip-audit: https://github.com/pypa/pip-audit
