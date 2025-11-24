# Commit Message Format

This project uses semantic versioning based on commit messages.

## Format

```
<type>: <subject>

<body>

<footer>
```

## Types

- **fix**: Bug fix (patch version bump: 0.0.X)
- **feat**: New feature (minor version bump: 0.X.0)
- **major**: Breaking change (major version bump: X.0.0)
- **breaking**: Breaking change (major version bump: X.0.0)
- **docs**: Documentation only changes (patch bump)
- **style**: Code style changes (formatting, etc.) (patch bump)
- **refactor**: Code refactoring (patch bump)
- **perf**: Performance improvements (patch bump)
- **test**: Adding or updating tests (patch bump)
- **chore**: Maintenance tasks (patch bump)

## Examples

### Patch Release (0.0.X)
```
fix: correct CPU percentage calculation

The calculation was off by a factor of 10 when using more than 4 threads.
```

### Minor Release (0.X.0)
```
feat: add WebSocket support for real-time CPU metrics

- Implement WebSocket endpoint /ws/cpu-metrics
- Add background task for CPU monitoring
- Update UI to use WebSocket instead of polling

Closes #42
```

### Major Release (X.0.0)
```
breaking: redesign REST API endpoints

BREAKING CHANGE: All API endpoints now use /v2/ prefix.
The old /api/ endpoints have been removed.

Migration guide:
- /api/threads -> /v2/threads
- /api/cpu-metrics -> /v2/metrics

Closes #123
```

## Tips

- Use imperative mood ("add feature" not "added feature")
- Keep the subject line under 50 characters
- Reference issues and PRs in the footer
- Explain the "why" not the "what" in the body
