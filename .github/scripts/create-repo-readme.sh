#!/bin/bash
# Create README for APT repository
# Usage: ./create-repo-readme.sh VERSION VERSION_TAG OUTPUT_FILE

set -e

VERSION="$1"
VERSION_TAG="$2"
OUTPUT_FILE="${3:-apt-repo/README.md}"

if [ -z "$VERSION" ] || [ -z "$VERSION_TAG" ]; then
  echo "Usage: $0 VERSION VERSION_TAG [OUTPUT_FILE]"
  exit 1
fi

echo "Creating repository README at $OUTPUT_FILE"

cat > "$OUTPUT_FILE" << EOF
# CPU Loader APT Repository

## Installation Instructions

### Debian 12 (Bookworm)
\`\`\`bash
# Download the package for your architecture
wget https://github.com/the78mole/cpu-loader/releases/download/$VERSION_TAG/cpu-loader_${VERSION}-1_amd64.deb
sudo dpkg -i cpu-loader_${VERSION}-1_amd64.deb
sudo apt-get install -f  # Install dependencies
\`\`\`

### Debian 13 (Trixie)
\`\`\`bash
# Download the package for your architecture
wget https://github.com/the78mole/cpu-loader/releases/download/$VERSION_TAG/cpu-loader_${VERSION}-1_amd64.deb
sudo dpkg -i cpu-loader_${VERSION}-1_amd64.deb
sudo apt-get install -f  # Install dependencies
\`\`\`

### Ubuntu 22.04 (Jammy)
\`\`\`bash
# Download the package for your architecture
wget https://github.com/the78mole/cpu-loader/releases/download/$VERSION_TAG/cpu-loader_${VERSION}-1_amd64.deb
sudo dpkg -i cpu-loader_${VERSION}-1_amd64.deb
sudo apt-get install -f  # Install dependencies
\`\`\`

### Ubuntu 24.04 (Noble)
\`\`\`bash
# Download the package for your architecture
wget https://github.com/the78mole/cpu-loader/releases/download/$VERSION_TAG/cpu-loader_${VERSION}-1_amd64.deb
sudo dpkg -i cpu-loader_${VERSION}-1_amd64.deb
sudo apt-get install -f  # Install dependencies
\`\`\`

## Available Architectures

- amd64 (x86_64)
- arm64 (aarch64)
- armhf (32-bit ARM)

## Usage

After installation, run:
\`\`\`bash
cpu-loader
\`\`\`
EOF

echo "✓ README created at $OUTPUT_FILE"
