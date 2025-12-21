#!/bin/bash
# Video Converter Installation Script

set -e

echo "=================================="
echo "  Video Converter Installation"
echo "=================================="
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This tool only supports macOS"
    exit 1
fi

# Check Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo "Warning: Apple Silicon (M1+) recommended for hardware acceleration"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
    echo "Error: Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"

# Check/Install Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "✓ Homebrew"

# Install FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    brew install ffmpeg
fi
echo "✓ FFmpeg $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"

# Install ExifTool
if ! command -v exiftool &> /dev/null; then
    echo "Installing ExifTool..."
    brew install exiftool
fi
echo "✓ ExifTool $(exiftool -ver)"

# Install Python package
echo ""
echo "Installing video-converter..."
pip3 install -e .

echo ""
echo "=================================="
echo "  Installation Complete!"
echo "=================================="
echo ""
echo "Run 'video-converter setup' to complete initial configuration."
echo ""
