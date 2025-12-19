# GitHub Actions Workflows

This directory contains the CI/CD workflows for the cpu-loader project.

## Workflow Architecture

The workflow structure uses a **main orchestrator workflow** that calls two specialized **reusable workflows** for building different package types.

### Main Workflow: build-all.yml

Central workflow that orchestrates all build processes.

**Trigger**: Push to main, PRs, or manual dispatch

**Jobs**:
1. **Version Generation**: Determines semantic version once (no duplication)
2. **Build Wheels**: Calls `build-wheels.yml` with version
3. **Build DEB**: Calls `build-deb.yml` with version

**Benefits**:
- Version generated once, used everywhere
- Parallel execution of wheel and DEB builds
- Single point of configuration
- Easy maintenance

## Workflows

### ci.yml - Continuous Integration
- **Trigger**: Push to any branch, PRs
- **Tools**: Uses `uv` for fast dependency management
- **Jobs**:
  - **Lint**: Runs pre-commit hooks (black, isort, flake8, mypy) using `uvx`
  - **Build and Test**: Tests on multiple Python versions (3.8-3.12) and OS (Ubuntu, macOS) using `uv`

### build-wheels.yml - Build Python Wheels (Reusable)
- **Trigger**: Called by `build-all.yml` or manual dispatch with version inputs
- **Inputs**:
  - `version`: Version to build (e.g., "1.2.3")
  - `version_tag`: Git tag (e.g., "v1.2.3")
- **Tools**: Uses `cibuildwheel` for multi-platform wheels
- **Jobs**:
  - **Update Version**: Updates pyproject.toml with provided version
  - **Build Wheels**: Builds binary wheels for:
    - Linux: x86_64, ARM64 (aarch64)
    - macOS: x86_64 (Intel), ARM64 (Apple Silicon)
    - Python: 3.9, 3.10, 3.11, 3.12
  - **Build Source Distribution**: Creates sdist
  - **Publish**: Publishes to PyPI (on main branch pushes only)
  - **Create Release**: Creates/updates GitHub Release with wheels

### build-deb.yml - Build DEB Packages (Reusable)
- **Trigger**: Called by `build-all.yml` or manual dispatch with version inputs
- **Inputs**:
  - `version`: Version to build (e.g., "1.2.3")
  - `version_tag`: Git tag (e.g., "v1.2.3")
- **Tools**: Docker + QEMU for cross-compilation
- **Configuration**: [`distros.yaml`](../../distros.yaml) defines distributions
- **Jobs**:
  - **Generate Matrix**: Reads distros.yaml, creates build matrix
  - **Build DEB**: Builds packages for:
    - Debian 12 (Bookworm): amd64, arm64, armhf
    - Debian 13 (Trixie): amd64, arm64, armhf, riscv64
    - Ubuntu 22.04 (Jammy): amd64, arm64, armhf
    - Ubuntu 24.04 (Noble): amd64, arm64, armhf, riscv64
  - **Create APT Repository**: Generates Packages and Release files
  - **Publish**: Adds DEB packages to GitHub Release

## Versioning Strategy

Versions are **automatically determined** using semantic versioning based on commit messages:

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
