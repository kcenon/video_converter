# Release Process

This guide documents the complete release process for Video Converter, including macOS app signing, notarization, and distribution.

## Overview

Video Converter uses automated GitHub Actions workflows for releases:

1. **Python Package**: Published to PyPI on version tag push
2. **macOS App**: Built, signed, notarized, and distributed as DMG
3. **Homebrew Cask**: Updated automatically after release

## Prerequisites

### For Maintainers

Before creating a release, ensure:

1. All tests pass on `main` branch
2. CHANGELOG.md is updated with release notes
3. Version is updated in `pyproject.toml`

### GitHub Secrets (for macOS signing)

The following secrets must be configured in the repository:

| Secret | Description |
|--------|-------------|
| `MACOS_SIGNING_IDENTITY` | Developer ID Application certificate identity (e.g., "Developer ID Application: Your Name (TEAM_ID)") |
| `MACOS_CERTIFICATE` | Base64-encoded .p12 certificate file |
| `MACOS_CERTIFICATE_PWD` | Password for the .p12 certificate |
| `APPLE_ID` | Apple ID email for notarization |
| `APPLE_PASSWORD` | App-specific password for notarization |
| `TEAM_ID` | Apple Developer Team ID |

## Release Steps

### 1. Prepare the Release

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Update version in pyproject.toml
# Edit pyproject.toml: version = "X.Y.Z"

# Update CHANGELOG.md with release notes
# Add a new section: ## [X.Y.Z] - YYYY-MM-DD

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: prepare release vX.Y.Z"
git push origin main
```

### 2. Create and Push Tag

```bash
# Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# Push the tag to trigger release workflows
git push origin vX.Y.Z
```

### 3. Monitor Workflows

After pushing the tag, the following workflows will run:

1. **Release** (`.github/workflows/release.yml`)
   - Builds Python package
   - Creates GitHub release with package

2. **Release macOS** (`.github/workflows/release-macos.yml`)
   - Builds macOS .app bundle
   - Signs and notarizes (if secrets configured)
   - Creates DMG installer
   - Uploads to GitHub release
   - Updates Homebrew Cask formula

### 4. Verify Release

After workflows complete:

1. Check the [Releases page](https://github.com/kcenon/video_converter/releases)
2. Download and test the DMG installer
3. Verify the app opens without Gatekeeper warnings
4. Test core functionality

## Manual macOS Build

For local testing without signing:

```bash
cd packaging/macos

# Build without signing
./build_app.sh --clean

# Create DMG
./create_dmg.sh
```

For signed builds (requires certificates):

```bash
# Set environment variables
export SIGNING_IDENTITY="Developer ID Application: ..."
export APPLE_ID="your@email.com"
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # App-specific password
export TEAM_ID="XXXXXXXXXX"

# Build with signing and notarization
./build_app.sh --clean --sign --notarize

# Create signed DMG
./create_dmg.sh
```

## Setting Up Code Signing

### 1. Apple Developer Account

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/)
2. Create a "Developer ID Application" certificate in Xcode or developer portal

### 2. Export Certificate

```bash
# Export from Keychain Access as .p12 file
# Then encode as base64 for GitHub secret
base64 -i certificate.p12 | pbcopy
```

### 3. Create App-Specific Password

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in and go to "App-Specific Passwords"
3. Generate a new password for "Video Converter CI"

### 4. Configure GitHub Secrets

In your repository settings, add the secrets listed in the Prerequisites section.

## Homebrew Distribution

### Installing via Homebrew

```bash
# Add the tap (first time only)
brew tap kcenon/tap

# Install
brew install --cask video-converter
```

### Manual Cask Update

If automatic update fails:

```bash
cd packaging/macos/homebrew

# Update with new version and SHA256
./update_cask.sh X.Y.Z "sha256-checksum-here"

# Commit and push
git add video-converter.rb
git commit -m "chore: update Homebrew Cask to vX.Y.Z"
git push origin main
```

## Troubleshooting

### Notarization Fails

1. Check that all binaries are signed with hardened runtime
2. Verify entitlements are correct
3. Check Apple's notarization log:
   ```bash
   xcrun notarytool log <submission-id> \
       --apple-id "$APPLE_ID" \
       --password "$APPLE_PASSWORD" \
       --team-id "$TEAM_ID"
   ```

### Gatekeeper Warning

If users see "unidentified developer" warning:

1. Verify the app is properly signed: `codesign -vv "Video Converter.app"`
2. Check notarization: `spctl -a -v "Video Converter.app"`
3. Ensure stapling was successful: `xcrun stapler validate "Video Converter.app"`

### DMG Won't Open

1. Verify DMG is properly signed
2. Check for quarantine: `xattr -l VideoConverter-X.Y.Z.dmg`
3. Remove quarantine if needed: `xattr -d com.apple.quarantine VideoConverter-X.Y.Z.dmg`

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 0.3.0 | 2024-12 | Initial macOS packaging pipeline |

## Related Documentation

- [Installation Guide](../installation.md)
- [Development Plan](../development-plan.md)
- [Apple Notarization Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
