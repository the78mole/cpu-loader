#!/bin/bash
# Create Release files for APT repository
# Usage: ./create-release-files.sh REPO_DIR

set -e

REPO_DIR="${1:-apt-repo}"

echo "Creating Release files in $REPO_DIR"

cd "$REPO_DIR"

for distro in debian ubuntu; do
  if [ ! -d "$distro" ]; then
    continue
  fi

  for codename in $(ls "$distro" 2>/dev/null || true); do
    if [ -d "$distro/$codename" ]; then
      echo "Creating Release file for $distro/$codename"
      cd "$distro/$codename"
      cat > Release << EOF
Origin: cpu-loader
Label: cpu-loader
Suite: $codename
Codename: $codename
Architectures: amd64 arm64 armhf
Components: main
Description: CPU Loader APT Repository for $distro $codename
EOF
      cd - >/dev/null
    fi
  done
done

echo "✓ Release files created"
