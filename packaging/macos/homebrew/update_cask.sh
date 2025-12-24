#!/bin/bash
# Update Homebrew Cask formula with new version and SHA256
#
# Usage:
#   ./update_cask.sh <version> <sha256>
#
# Example:
#   ./update_cask.sh 0.3.1 abc123def456...

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASK_FILE="${SCRIPT_DIR}/video-converter.rb"

VERSION="$1"
SHA256="$2"

if [ -z "$VERSION" ] || [ -z "$SHA256" ]; then
    echo "Usage: $0 <version> <sha256>"
    echo "Example: $0 0.3.1 abc123def456789..."
    exit 1
fi

echo "Updating Homebrew Cask formula..."
echo "  Version: $VERSION"
echo "  SHA256:  $SHA256"

# Update version
sed -i.bak "s/version \".*\"/version \"${VERSION}\"/" "$CASK_FILE"

# Update SHA256 (replace :no_check or existing hash)
if grep -q "sha256 :no_check" "$CASK_FILE"; then
    sed -i.bak "s/sha256 :no_check.*/sha256 \"${SHA256}\"/" "$CASK_FILE"
else
    sed -i.bak "s/sha256 \".*\"/sha256 \"${SHA256}\"/" "$CASK_FILE"
fi

# Clean up backup files
rm -f "${CASK_FILE}.bak"

echo "Updated Homebrew Cask formula:"
grep -E "version|sha256" "$CASK_FILE" | head -2

echo "Done!"
