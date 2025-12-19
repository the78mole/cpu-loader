#!/bin/bash
# Create Packages and Packages.gz files for APT repository
# Usage: ./create-packages-files.sh REPO_DIR

set -e

REPO_DIR="${1:-apt-repo}"

echo "Creating Packages files in $REPO_DIR"

cd "$REPO_DIR"

for distro in debian ubuntu; do
  if [ ! -d "$distro" ]; then
    continue
  fi

  for codename in $(ls "$distro" 2>/dev/null || true); do
    for arch_dir in "$distro/$codename"/binary-*; do
      if [ -d "$arch_dir" ] && [ -n "$(ls -A "$arch_dir"/*.deb 2>/dev/null)" ]; then
        echo "Creating Packages file for $arch_dir"
        cd "$arch_dir"
        dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz
        dpkg-scanpackages . /dev/null > Packages
        cd - >/dev/null
      fi
    done
  done
done

echo "✓ Packages files created"
