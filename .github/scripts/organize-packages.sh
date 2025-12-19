#!/bin/bash
# Organize DEB packages by distribution
# Usage: ./organize-packages.sh INPUT_DIR OUTPUT_DIR

set -e

INPUT_DIR="${1:-all-debs}"
OUTPUT_DIR="${2:-apt-repo}"

echo "Organizing packages from $INPUT_DIR to $OUTPUT_DIR"

# Create directory structure
mkdir -p "$OUTPUT_DIR"/{debian/{bookworm,trixie},ubuntu/{jammy,noble}}/binary-{amd64,arm64,armhf,riscv64}

# Copy packages to appropriate directories
for dir in "$INPUT_DIR"/deb-*; do
  if [ -d "$dir" ]; then
    pkg=$(basename "$dir")
    echo "Processing $pkg"

    # Extract distro, version, and arch
    distro=$(echo "$pkg" | cut -d'-' -f2)
    version=$(echo "$pkg" | cut -d'-' -f3)
    arch=$(echo "$pkg" | cut -d'-' -f4)

    # Map version to codename
    case "$distro-$version" in
      debian-12) codename="bookworm" ;;
      debian-13) codename="trixie" ;;
      ubuntu-22.04) codename="jammy" ;;
      ubuntu-24.04) codename="noble" ;;
      *) echo "Unknown distro-version: $distro-$version"; continue ;;
    esac

    echo "  → Copying to $OUTPUT_DIR/$distro/$codename/binary-$arch/"
    cp "$dir"/*.deb "$OUTPUT_DIR/$distro/$codename/binary-$arch/" || true
  fi
done

echo "✓ Package organization completed"
