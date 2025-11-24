# GitHub Actions Workflows

This directory contains the CI/CD workflows for the cpu-loader project.

## Workflows

### ci.yml - Continuous Integration
- **Trigger**: Push to any branch, PRs
- **Tools**: Uses `uv` for fast dependency management
- **Jobs**:
  - **Lint**: Runs pre-commit hooks (black, isort, flake8, mypy) using `uvx`
  - **Build and Test**: Tests on multiple Python versions (3.8-3.12) and OS (Ubuntu, macOS) using `uv`

### build-wheels.yml - Build and Publish
- **Trigger**: Push to main, tag push (`v*`), PR, or manual workflow dispatch
- **Tools**: Uses `uv` for fast builds and `cibuildwheel` for multi-platform wheels
- **Jobs**:
  - **Version**: Determines semantic version based on commit messages
    - Patch bump: Every commit
    - Minor bump: Commits prefixed with `feat:`
    - Major bump: Commits with `major:`, `breaking:`, or `BREAKING CHANGE:`
  - **Build Wheels**: Builds binary wheels for:
    - Linux: x86_64, ARM64 (aarch64)
    - macOS: x86_64 (Intel), ARM64 (Apple Silicon)
  - **Build Source Distribution**: Creates sdist using `uvx`
  - **Publish**: Publishes to PyPI (on main branch pushes only)
  - **Create Release**: Creates GitHub Release with artifacts and auto-generated tag

## Publishing a Release

The version is **automatically determined** using semantic versioning:

1. Commit with appropriate prefix:
   ```bash
   # Patch release (0.0.X)
   git commit -m "fix: correct CPU calculation"

   # Minor release (0.X.0)
   git commit -m "feat: add WebSocket support"

   # Major release (X.0.0)
   git commit -m "major: redesign API"
   # or
   git commit -m "breaking: remove old endpoints"
   ```

2. Push to main:
   ```bash
   git push origin main
   ```

3. GitHub Actions will automatically:
   - Calculate the new version
   - Update `pyproject.toml`
   - Build wheels for all platforms
   - Create a git tag (e.g., `v0.2.0`)
   - Publish to PyPI
   - Create a GitHub Release

## Requirements

For PyPI publishing, the repository needs:
- `PYPI_API_TOKEN` secret configured (uses Trusted Publisher in workflow)
- Permissions set for `id-token: write` (for PyPI)
- Permissions set for `contents: write` (for GitHub Releases)
