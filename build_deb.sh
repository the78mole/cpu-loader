#!/bin/bash
set -e

# Build script for creating DEB packages locally for testing
# Usage: ./build_deb.sh [distro] [version] [arch]
# Example: ./build_deb.sh debian 12 amd64

DISTRO=${1:-debian}
VERSION=${2:-12}
ARCH=${3:-amd64}

# Map version to codename
case "$DISTRO-$VERSION" in
    debian-12) CODENAME="bookworm" ;;
    debian-13) CODENAME="trixie" ;;
    ubuntu-22.04) CODENAME="jammy" ;;
    ubuntu-24.04) CODENAME="noble" ;;
    *) echo "Unknown distro-version: $DISTRO-$VERSION"; exit 1 ;;
esac

echo "Building DEB package for $DISTRO $VERSION ($CODENAME) on $ARCH"

# Get the current version from pyproject.toml
PACKAGE_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo "Package version: $PACKAGE_VERSION"

# Update debian/changelog
TIMESTAMP=$(date -R)
cat > debian/changelog << EOF
cpu-loader ($PACKAGE_VERSION-1) $CODENAME; urgency=medium

  * Build for $DISTRO $VERSION ($CODENAME)

 -- the78mole <the78mole@users.noreply.github.com>  $TIMESTAMP
EOF

echo "Updated debian/changelog"

# Create output directory
OUTPUT_DIR="deb-output/$DISTRO-$VERSION-$ARCH"
mkdir -p "$OUTPUT_DIR"

# Build using Docker
echo "Building package in Docker container..."
docker run --rm --privileged \
    --platform linux/$ARCH \
    -v "$(pwd):/workspace" \
    -w /workspace \
    "$DISTRO:$CODENAME" \
    bash -c "
        set -e
        export DEBIAN_FRONTEND=noninteractive

        echo '=== Installing build dependencies ==='
        apt-get update
        apt-get install -y \
            debhelper \
            dh-python \
            python3-all-dev \
            python3-setuptools \
            python3-wheel \
            python3-pip \
            build-essential \
            devscripts \
            equivs

        echo '=== Installing runtime dependencies (if available) ==='
        apt-get install -y \
            python3-fastapi \
            python3-uvicorn \
            python3-pydantic \
            python3-requests \
            python3-psutil \
            python3-websockets \
            python3-paho-mqtt || echo 'Some Python packages not available in repos'

        echo '=== Building package ==='
        dpkg-buildpackage -us -uc -b -a$ARCH

        echo '=== Moving built packages ==='
        mkdir -p /workspace/$OUTPUT_DIR
        mv ../*.deb /workspace/$OUTPUT_DIR/ || true
        mv ../*.buildinfo /workspace/$OUTPUT_DIR/ || true
        mv ../*.changes /workspace/$OUTPUT_DIR/ || true

        echo '=== Listing built packages ==='
        ls -lah /workspace/$OUTPUT_DIR/
    "

echo ""
echo "======================================"
echo "Build complete! Packages are in:"
echo "  $OUTPUT_DIR/"
echo ""
echo "To install locally:"
echo "  sudo dpkg -i $OUTPUT_DIR/*.deb"
echo "  sudo apt-get install -f"
echo "======================================"
