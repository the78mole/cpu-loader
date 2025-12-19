#!/bin/bash
# Update version in project files
# Usage: ./update-version.sh VERSION CODENAME

set -e

VERSION="$1"
CODENAME="$2"

if [ -z "$VERSION" ] || [ -z "$CODENAME" ]; then
  echo "Usage: $0 VERSION CODENAME"
  exit 1
fi

echo "Updating version to $VERSION for $CODENAME"

# Update pyproject.toml
sed -i "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
echo "✓ Updated pyproject.toml"

# Update debian/changelog
TIMESTAMP=$(date -R)
cat > debian/changelog << EOF
cpu-loader ($VERSION-1) $CODENAME; urgency=medium

  * Release version $VERSION

 -- the78mole <the78mole@users.noreply.github.com>  $TIMESTAMP
EOF

echo "✓ Updated debian/changelog"
cat debian/changelog
