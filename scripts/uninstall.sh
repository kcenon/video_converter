#!/bin/bash
# Video Converter Uninstallation Script

set -e

echo "=================================="
echo "  Video Converter Uninstallation"
echo "=================================="
echo ""

# Remove launchd service
PLIST_FILE="$HOME/Library/LaunchAgents/com.videoconverter.service.plist"
if [[ -f "$PLIST_FILE" ]]; then
    echo "Stopping and removing launchd service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    rm -f "$PLIST_FILE"
    echo "✓ Service removed"
fi

# Uninstall Python package
echo "Uninstalling Python package..."
pip3 uninstall video-converter -y 2>/dev/null || true
echo "✓ Package removed"

# Ask about config removal
CONFIG_DIR="$HOME/.config/video_converter"
if [[ -d "$CONFIG_DIR" ]]; then
    read -p "Remove configuration files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo "✓ Configuration removed"
    fi
fi

echo ""
echo "=================================="
echo "  Uninstallation Complete!"
echo "=================================="
echo ""
echo "Note: FFmpeg and ExifTool were not removed."
echo "Run 'brew uninstall ffmpeg exiftool' to remove them."
echo ""
