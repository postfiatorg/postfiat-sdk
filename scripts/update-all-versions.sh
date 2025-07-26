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
echo "📚 Updating documentation banner..."
cd ..
# Update mkdocs.yml extra section for announcement banner
RELEASE_TAG="v$VERSION"
RELEASE_URL="https://github.com/postfiatorg/postfiat-sdk/releases/tag/v$VERSION"

# Update only the banner-required fields in mkdocs.yml
sed -i.bak \
  -e "/^extra:/,/^[a-z]/ { s/  version: .*/  version: $VERSION/; s/  release_tag: .*/  release_tag: $RELEASE_TAG/; s|  release_url: .*|  release_url: \"$RELEASE_URL\"|; }" \
  mkdocs.yml
rm mkdocs.yml.bak

echo "✅ Documentation banner updated"

echo ""
echo "🎉 All versions updated to $VERSION!"
echo ""
echo "📋 Summary:"
echo "  - Centralized VERSION file: $VERSION"
echo "  - Python packages: $VERSION"
echo "  - TypeScript packages: $VERSION"  
echo "  - Solidity packages: $VERSION"
echo "  - Documentation banner: $RELEASE_TAG"