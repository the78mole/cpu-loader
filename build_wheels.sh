#!/bin/bash
# Build wheels locally for testing

set -e

echo "Building wheels locally..."

# Install build dependencies
pip install build cibuildwheel

# Build using cibuildwheel
CIBW_BUILD="cp312-*" \
CIBW_SKIP="*-musllinux_*" \
cibuildwheel --platform linux

echo "Wheels built successfully in ./wheelhouse/"
ls -lh ./wheelhouse/
