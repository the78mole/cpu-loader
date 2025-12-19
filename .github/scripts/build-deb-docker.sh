#!/bin/bash
# Build DEB package in Docker container
# Usage: ./build-deb-docker.sh DISTRO CODENAME ARCH

set -e

DISTRO="$1"
CODENAME="$2"
ARCH="$3"

if [ -z "$DISTRO" ] || [ -z "$CODENAME" ] || [ -z "$ARCH" ]; then
  echo "Usage: $0 DISTRO CODENAME ARCH"
  exit 1
fi

echo "Building DEB package for $DISTRO:$CODENAME on $ARCH"

docker run --rm --privileged \
  --platform linux/$ARCH \
  -v "$(pwd):/workspace" \
  -w /workspace \
  "$DISTRO:$CODENAME" \
  bash -c "
    set -e
    export DEBIAN_FRONTEND=noninteractive

    echo '=== Updating package lists ==='
    apt-get update

    echo '=== Installing build dependencies ==='
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
    mkdir -p /workspace/deb-packages
    mv ../*.deb /workspace/deb-packages/ || true
    mv ../*.buildinfo /workspace/deb-packages/ || true
    mv ../*.changes /workspace/deb-packages/ || true

    echo '=== Listing built packages ==='
    ls -lah /workspace/deb-packages/
  "

echo "✓ Build completed successfully"
