#!/bin/bash
# Video Converter macOS .app Bundle Build Script
#
# This script builds the Video Converter application as a macOS .app bundle
# using PyInstaller, with optional code signing and notarization.
#
# Usage:
#   ./build_app.sh [options]
#
# Options:
#   --sign          Sign the application with the specified identity
#   --notarize      Notarize the application (requires --sign)
#   --clean         Clean build artifacts before building
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

# Build configuration
APP_NAME="Video Converter"
BUNDLE_ID="com.github.kcenon.videoconverter"
SPEC_FILE="${SCRIPT_DIR}/video_converter.spec"
DIST_DIR="${PROJECT_ROOT}/dist"
BUILD_DIR="${PROJECT_ROOT}/build"

# Code signing configuration (set via environment variables)
SIGNING_IDENTITY="${SIGNING_IDENTITY:-}"
APPLE_ID="${APPLE_ID:-}"
APPLE_PASSWORD="${APPLE_PASSWORD:-}"
TEAM_ID="${TEAM_ID:-}"

# Flags
DO_SIGN=false
DO_NOTARIZE=false
DO_CLEAN=false

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
    echo "Video Converter macOS .app Bundle Build Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --sign          Sign the application (requires SIGNING_IDENTITY env var)"
    echo "  --notarize      Notarize the application (requires --sign and Apple credentials)"
    echo "  --clean         Clean build artifacts before building"
    echo "  --help          Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  SIGNING_IDENTITY    Code signing identity (e.g., 'Developer ID Application: ...')"
    echo "  APPLE_ID            Apple ID for notarization"
    echo "  APPLE_PASSWORD      App-specific password for notarization"
    echo "  TEAM_ID             Apple Developer Team ID"
    echo ""
}

check_dependencies() {
    print_header "Checking Dependencies"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"

    # Check PyInstaller
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        print_warning "PyInstaller not found, installing..."
        pip3 install pyinstaller
    fi
    print_success "PyInstaller found"

    # Check if project is installed
    if ! python3 -c "import video_converter" &> /dev/null; then
        print_warning "video_converter not installed, installing..."
        pip3 install -e "${PROJECT_ROOT}[gui]"
    fi
    print_success "video_converter package found"

    # Get version from package
    APP_VERSION=$(python3 -c "from video_converter import __version__; print(__version__)")
    print_success "App version: ${APP_VERSION}"

    # Check for code signing tools (if signing is enabled)
    if $DO_SIGN; then
        if ! command -v codesign &> /dev/null; then
            print_error "codesign not found (Xcode command line tools required)"
            exit 1
        fi
        print_success "codesign found"

        if [ -z "$SIGNING_IDENTITY" ]; then
            print_error "SIGNING_IDENTITY environment variable is not set"
            exit 1
        fi
        print_success "Signing identity: $SIGNING_IDENTITY"
    fi

    # Check for notarization tools (if notarization is enabled)
    if $DO_NOTARIZE; then
        if ! command -v xcrun &> /dev/null; then
            print_error "xcrun not found (Xcode command line tools required)"
            exit 1
        fi
        print_success "xcrun found"

        if [ -z "$APPLE_ID" ] || [ -z "$APPLE_PASSWORD" ] || [ -z "$TEAM_ID" ]; then
            print_error "APPLE_ID, APPLE_PASSWORD, and TEAM_ID environment variables are required for notarization"
            exit 1
        fi
        print_success "Apple credentials configured"
    fi
}

clean_build() {
    print_header "Cleaning Build Artifacts"

    if [ -d "$DIST_DIR" ]; then
        rm -rf "$DIST_DIR"
        print_success "Removed dist directory"
    fi

    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        print_success "Removed build directory"
    fi

    print_success "Clean complete"
}

create_app_icon() {
    print_header "Creating App Icon"

    ICON_DIR="${SCRIPT_DIR}/resources"
    ICON_FILE="${ICON_DIR}/AppIcon.icns"
    mkdir -p "$ICON_DIR"

    if [ -f "$ICON_FILE" ]; then
        print_success "App icon already exists"
        return
    fi

    # Create a placeholder icon (you should replace this with actual icon)
    print_warning "Creating placeholder icon (replace with actual icon for production)"

    # Create iconset directory
    ICONSET_DIR="${ICON_DIR}/AppIcon.iconset"
    mkdir -p "$ICONSET_DIR"

    # Try multiple methods to create placeholder icons
    ICON_CREATED=false

    # Method 1: Use Python with Pillow (most reliable, installed as GUI dependency)
    if ! $ICON_CREATED && python3 -c "from PIL import Image" &> /dev/null; then
        echo "Using Python/Pillow to create placeholder icons..."
        export ICONSET_DIR
        python3 << 'PYTHON_SCRIPT'
from PIL import Image, ImageDraw

# Video converter theme color
COLOR = (74, 144, 217)  # #4A90D9

sizes = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

import os
iconset_dir = os.environ.get("ICONSET_DIR", "AppIcon.iconset")

for size, filename in sizes:
    img = Image.new("RGB", (size, size), COLOR)
    draw = ImageDraw.Draw(img)

    # Draw a simple "V" shape for Video
    margin = size // 4
    points = [
        (margin, margin),
        (size // 2, size - margin),
        (size - margin, margin),
    ]
    line_width = max(2, size // 16)
    draw.line([points[0], points[1]], fill="white", width=line_width)
    draw.line([points[1], points[2]], fill="white", width=line_width)

    img.save(os.path.join(iconset_dir, filename))
    print(f"  Created {filename}")

print("All icon sizes created successfully")
PYTHON_SCRIPT
        ICON_CREATED=true
        print_success "Icons created using Python/Pillow"

    # Method 2: Use ImageMagick if available
    elif ! $ICON_CREATED && command -v convert &> /dev/null; then
        echo "Using ImageMagick to create placeholder icons..."
        for size in 16 32 128 256 512; do
            double=$((size * 2))
            convert -size ${size}x${size} xc:'#4A90D9' "${ICONSET_DIR}/icon_${size}x${size}.png"
            convert -size ${double}x${double} xc:'#4A90D9' "${ICONSET_DIR}/icon_${size}x${size}@2x.png"
        done
        ICON_CREATED=true
        print_success "Icons created using ImageMagick"
    fi

    if ! $ICON_CREATED; then
        print_error "No icon generation method available"
        print_warning "Please install Pillow (pip install pillow) or ImageMagick"
        print_warning "Or provide AppIcon.icns manually in ${ICON_DIR}"
        return 1
    fi

    # Convert iconset to icns
    echo "Converting iconset to .icns..."
    iconutil -c icns "$ICONSET_DIR" -o "$ICON_FILE"

    if [ -f "$ICON_FILE" ]; then
        # Clean up iconset
        rm -rf "$ICONSET_DIR"
        print_success "App icon created: $ICON_FILE"
    else
        print_error "Failed to create .icns file"
        return 1
    fi
}

build_app() {
    print_header "Building Application Bundle"

    cd "$PROJECT_ROOT"

    # Create app icon if needed
    create_app_icon

    # Run PyInstaller
    echo "Running PyInstaller..."
    pyinstaller \
        --clean \
        --noconfirm \
        --distpath "$DIST_DIR" \
        --workpath "$BUILD_DIR" \
        "$SPEC_FILE"

    if [ ! -d "${DIST_DIR}/${APP_NAME}.app" ]; then
        print_error "Build failed: .app bundle not created"
        exit 1
    fi

    print_success "Application bundle created: ${DIST_DIR}/${APP_NAME}.app"
}

sign_app() {
    if ! $DO_SIGN; then
        return
    fi

    print_header "Signing Application"

    APP_PATH="${DIST_DIR}/${APP_NAME}.app"
    ENTITLEMENTS="${SCRIPT_DIR}/entitlements.plist"

    # Sign all frameworks and dylibs first
    echo "Signing embedded frameworks and libraries..."
    find "$APP_PATH" -type f \( -name "*.dylib" -o -name "*.so" -o -name "*.framework" \) -print0 | \
    while IFS= read -r -d '' file; do
        codesign --force --options runtime \
            --sign "$SIGNING_IDENTITY" \
            --timestamp \
            "$file" 2>/dev/null || true
    done

    # Sign the main executable
    echo "Signing main executable..."
    codesign --force --options runtime \
        --sign "$SIGNING_IDENTITY" \
        --entitlements "$ENTITLEMENTS" \
        --timestamp \
        "$APP_PATH"

    # Verify signature
    echo "Verifying signature..."
    codesign --verify --deep --strict --verbose=2 "$APP_PATH"

    print_success "Application signed successfully"
}

notarize_app() {
    if ! $DO_NOTARIZE; then
        return
    fi

    print_header "Notarizing Application"

    APP_PATH="${DIST_DIR}/${APP_NAME}.app"
    ZIP_PATH="${DIST_DIR}/${APP_NAME}.zip"

    # Create ZIP for notarization
    echo "Creating ZIP archive..."
    ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

    # Submit for notarization
    echo "Submitting for notarization (this may take several minutes)..."
    xcrun notarytool submit "$ZIP_PATH" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_PASSWORD" \
        --team-id "$TEAM_ID" \
        --wait

    # Staple the notarization ticket
    echo "Stapling notarization ticket..."
    xcrun stapler staple "$APP_PATH"

    # Clean up ZIP
    rm -f "$ZIP_PATH"

    print_success "Application notarized successfully"
}

print_summary() {
    print_header "Build Summary"

    APP_PATH="${DIST_DIR}/${APP_NAME}.app"
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)

    echo "Application: ${APP_NAME}"
    echo "Version:     ${APP_VERSION}"
    echo "Bundle ID:   ${BUNDLE_ID}"
    echo "Location:    ${APP_PATH}"
    echo "Size:        ${APP_SIZE}"
    echo ""

    if $DO_SIGN; then
        echo "Signed:      Yes"
    else
        echo "Signed:      No"
    fi

    if $DO_NOTARIZE; then
        echo "Notarized:   Yes"
    else
        echo "Notarized:   No"
    fi

    echo ""
    print_success "Build complete!"
    echo ""
    echo "To install, drag '${APP_NAME}.app' to your Applications folder."
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sign)
            DO_SIGN=true
            shift
            ;;
        --notarize)
            DO_NOTARIZE=true
            DO_SIGN=true  # Notarization requires signing
            shift
            ;;
        --clean)
            DO_CLEAN=true
            shift
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
check_dependencies

print_header "Video Converter macOS Build"
echo "Version: ${APP_VERSION}"
echo "Building: ${APP_NAME}.app"

if $DO_CLEAN; then
    clean_build
fi

build_app
sign_app
notarize_app
print_summary
