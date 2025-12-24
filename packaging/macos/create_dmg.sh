#!/bin/bash
# Video Converter DMG Installer Creation Script
#
# This script creates a DMG disk image for distributing the Video Converter
# application on macOS. It creates a styled DMG with drag-to-install support.
#
# Usage:
#   ./create_dmg.sh [options]
#
# Options:
#   --app PATH      Path to the .app bundle (default: dist/Video Converter.app)
#   --output PATH   Output DMG path (default: dist/VideoConverter-VERSION.dmg)
#   --help          Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
APP_NAME="Video Converter"
VOLUME_NAME="Video Converter"

# Get version dynamically from the package
get_app_version() {
    if python3 -c "from video_converter import __version__; print(__version__)" 2>/dev/null; then
        return
    fi
    # Fallback: try to read from pyproject.toml
    if [ -f "${PROJECT_ROOT}/pyproject.toml" ]; then
        grep -m1 'version = ' "${PROJECT_ROOT}/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
        return
    fi
    echo "0.0.0"
}

APP_VERSION=$(get_app_version)
DMG_TEMP="${PROJECT_ROOT}/dist/dmg_temp"
DMG_FINAL="${PROJECT_ROOT}/dist/VideoConverter-${APP_VERSION}.dmg"
APP_PATH="${PROJECT_ROOT}/dist/${APP_NAME}.app"

# Background image dimensions (for reference)
BG_WIDTH=600
BG_HEIGHT=400

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

show_help() {
    echo "Video Converter DMG Creation Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --app PATH      Path to the .app bundle"
    echo "  --output PATH   Output DMG path"
    echo "  --help          Show this help message"
    echo ""
}

check_dependencies() {
    print_header "Checking Dependencies"

    # Check for hdiutil (should be available on macOS)
    if ! command -v hdiutil &> /dev/null; then
        print_error "hdiutil not found (requires macOS)"
        exit 1
    fi
    print_success "hdiutil found"

    # Check for create-dmg (optional, but provides better DMG styling)
    if command -v create-dmg &> /dev/null; then
        print_success "create-dmg found (will use for styled DMG)"
        USE_CREATE_DMG=true
    else
        print_warning "create-dmg not found, using basic DMG creation"
        print_warning "Install with: brew install create-dmg"
        USE_CREATE_DMG=false
    fi
}

check_app_bundle() {
    print_header "Checking Application Bundle"

    if [ ! -d "$APP_PATH" ]; then
        print_error "Application bundle not found: $APP_PATH"
        echo "Please run build_app.sh first"
        exit 1
    fi

    print_success "Application bundle found: $APP_PATH"

    # Get app size
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
    echo "Application size: $APP_SIZE"
}

create_dmg_basic() {
    print_header "Creating DMG (Basic Method)"

    # Clean up any existing temp directory
    rm -rf "$DMG_TEMP"
    mkdir -p "$DMG_TEMP"

    # Copy application to temp directory
    echo "Copying application bundle..."
    cp -R "$APP_PATH" "$DMG_TEMP/"

    # Create symbolic link to Applications
    echo "Creating Applications symlink..."
    ln -s /Applications "$DMG_TEMP/Applications"

    # Calculate DMG size (app size + 50MB buffer)
    DMG_SIZE=$(( $(du -sm "$DMG_TEMP" | cut -f1) + 50 ))

    # Create temporary DMG
    TEMP_DMG="${PROJECT_ROOT}/dist/temp.dmg"
    echo "Creating disk image..."
    hdiutil create \
        -srcfolder "$DMG_TEMP" \
        -volname "$VOLUME_NAME" \
        -fs HFS+ \
        -fsargs "-c c=64,a=16,e=16" \
        -format UDRW \
        -size "${DMG_SIZE}m" \
        "$TEMP_DMG"

    # Mount the temporary DMG
    echo "Mounting disk image..."
    MOUNT_DIR=$(hdiutil attach "$TEMP_DMG" | grep -m 1 "/Volumes" | awk '{print $3}')

    if [ -z "$MOUNT_DIR" ]; then
        print_error "Failed to mount DMG"
        exit 1
    fi

    # Set up DMG appearance using AppleScript
    echo "Configuring DMG appearance..."
    osascript <<EOF
tell application "Finder"
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {100, 100, 700, 500}
        set theViewOptions to icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 128
        set position of item "$APP_NAME.app" of container window to {150, 200}
        set position of item "Applications" of container window to {450, 200}
        update without registering applications
        close
    end tell
end tell
EOF

    # Allow time for Finder to update
    sleep 2

    # Unmount
    echo "Unmounting disk image..."
    hdiutil detach "$MOUNT_DIR"

    # Convert to compressed DMG
    echo "Creating final compressed DMG..."
    rm -f "$DMG_FINAL"
    hdiutil convert "$TEMP_DMG" -format UDZO -o "$DMG_FINAL"

    # Clean up
    rm -f "$TEMP_DMG"
    rm -rf "$DMG_TEMP"

    print_success "DMG created: $DMG_FINAL"
}

create_dmg_styled() {
    print_header "Creating DMG (Styled Method)"

    # Remove existing DMG
    rm -f "$DMG_FINAL"

    # Check if icon exists
    ICON_FILE="${SCRIPT_DIR}/resources/AppIcon.icns"
    ICON_ARGS=""
    if [ -f "$ICON_FILE" ]; then
        ICON_ARGS="--volicon $ICON_FILE"
    else
        print_warning "AppIcon.icns not found, DMG will use default icon"
    fi

    # Create DMG using create-dmg
    create-dmg \
        --volname "$VOLUME_NAME" \
        ${ICON_ARGS} \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 128 \
        --icon "$APP_NAME.app" 150 200 \
        --hide-extension "$APP_NAME.app" \
        --app-drop-link 450 200 \
        --no-internet-enable \
        "$DMG_FINAL" \
        "$APP_PATH"

    print_success "DMG created: $DMG_FINAL"
}

sign_dmg() {
    print_header "Signing DMG"

    if [ -z "$SIGNING_IDENTITY" ]; then
        print_warning "SIGNING_IDENTITY not set, skipping DMG signing"
        return
    fi

    echo "Signing DMG..."
    codesign --force --sign "$SIGNING_IDENTITY" "$DMG_FINAL"

    print_success "DMG signed"
}

notarize_dmg() {
    print_header "Notarizing DMG"

    if [ -z "$APPLE_ID" ] || [ -z "$APPLE_PASSWORD" ] || [ -z "$TEAM_ID" ]; then
        print_warning "Apple credentials not set, skipping notarization"
        return
    fi

    echo "Submitting DMG for notarization..."
    xcrun notarytool submit "$DMG_FINAL" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_PASSWORD" \
        --team-id "$TEAM_ID" \
        --wait

    echo "Stapling notarization ticket..."
    xcrun stapler staple "$DMG_FINAL"

    print_success "DMG notarized"
}

print_summary() {
    print_header "DMG Summary"

    DMG_SIZE=$(du -sh "$DMG_FINAL" | cut -f1)

    echo "DMG File:    $DMG_FINAL"
    echo "Volume Name: $VOLUME_NAME"
    echo "Version:     $APP_VERSION"
    echo "Size:        $DMG_SIZE"
    echo ""

    # Calculate SHA256 checksum
    echo "SHA256 Checksum:"
    shasum -a 256 "$DMG_FINAL"
    echo ""

    print_success "DMG creation complete!"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --app)
            APP_PATH="$2"
            shift 2
            ;;
        --output)
            DMG_FINAL="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
print_header "Video Converter DMG Creation"
echo "Version: ${APP_VERSION}"

check_dependencies
check_app_bundle

if $USE_CREATE_DMG; then
    create_dmg_styled
else
    create_dmg_basic
fi

sign_dmg
notarize_dmg
print_summary
