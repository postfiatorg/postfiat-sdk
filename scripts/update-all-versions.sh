#!/bin/bash
set -e

echo "🚀 Updating all package versions from centralized VERSION file..."

# Check if VERSION file exists
if [ ! -f "VERSION" ]; then
    echo "❌ VERSION file not found!"
    exit 1
fi

VERSION=$(cat VERSION)
echo "📦 Version: $VERSION"

echo ""
echo "🐍 Updating Python packages..."
cd python
python3 scripts/generate_python_types.py
echo "✅ Python versions updated"

echo ""
echo "📘 Updating TypeScript packages..."
cd ../typescript
npm run update-version
echo "✅ TypeScript versions updated"

echo ""
echo "⚡ Updating Solidity packages..."
cd ../solidity
# Update package.json version
node -e "const pkg = require('./package.json'); pkg.version = process.argv[1]; require('fs').writeFileSync('./package.json', JSON.stringify(pkg, null, 2) + '\n');" "$VERSION"
echo "✅ Solidity versions updated"

echo ""
echo "📚 Updating documentation templates..."
cd ..
# Update mkdocs.yml extra section with new version
RELEASE_TAG="release-$VERSION"
RELEASE_URL="https://github.com/postfiatorg/postfiat-sdk/releases/tag/release-$VERSION"
RELEASE_DATE=$(date +%Y-%m-%d)
DOWNLOAD_URL="https://github.com/postfiatorg/postfiat-sdk/releases/download/release-$VERSION"
REPO_URL="https://github.com/postfiatorg/postfiat-sdk"

# Use sed to update the extra section in mkdocs.yml
sed -i.bak \
  -e "s/version: .*/version: $VERSION/" \
  -e "s/release_tag: .*/release_tag: $RELEASE_TAG/" \
  -e "s|release_url: .*|release_url: \"$RELEASE_URL\"|" \
  -e "s/release_date: .*/release_date: \"$RELEASE_DATE\"/" \
  mkdocs.yml
rm mkdocs.yml.bak

# Update all placeholders in docs/index.md
sed -i.bak \
  -e "s/__VERSION_PLACEHOLDER__/$VERSION/g" \
  -e "s/__RELEASE_TAG_PLACEHOLDER__/$RELEASE_TAG/g" \
  -e "s|__DOWNLOAD_URL_PLACEHOLDER__|$DOWNLOAD_URL|g" \
  -e "s|__REPO_URL_PLACEHOLDER__|$REPO_URL|g" \
  docs/index.md
rm docs/index.md.bak

echo "✅ Documentation versions updated"

echo ""
echo "🎉 All versions updated to $VERSION!"
echo ""
echo "📋 Summary:"
echo "  - Centralized VERSION file: $VERSION"
echo "  - Python pyproject.toml: dynamic version from setup.py"
echo "  - Python __init__.py: $VERSION"
echo "  - TypeScript package.json: $VERSION"
echo "  - TypeScript index.ts: $VERSION"
echo "  - TypeScript User-Agent: $VERSION"
echo "  - Solidity package.json: $VERSION"
echo "  - Documentation mkdocs.yml: $RELEASE_TAG"