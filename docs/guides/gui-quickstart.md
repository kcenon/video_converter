# GUI Quick Start Guide

Get started with Video Converter's graphical interface in minutes.

## Installation

=== "Homebrew (Recommended)"

    ```bash
    brew install --cask video-converter
    ```

=== "DMG Download"

    1. Visit the [GitHub Releases](https://github.com/kcenon/video_converter/releases) page
    2. Download the latest `.dmg` file
    3. Open the DMG and drag Video Converter to Applications

=== "From Source"

    ```bash
    pip install video-converter
    video-converter-gui
    ```

## First Launch

### 1. Open the Application

Launch Video Converter from your Applications folder or Spotlight (++cmd+space++, then type "Video Converter").

### 2. Grant Permissions

On first launch, you may be prompted for permissions:

!!! warning "Photos Library Access"
    If you plan to convert videos from your Photos library, grant access when prompted:

    1. Click **OK** on the permission dialog
    2. Or manually enable in **System Settings** > **Privacy & Security** > **Photos**

### 3. The Main Window

The application opens with a tab-based interface:

| Tab | Description |
|-----|-------------|
| **Home** | Drag & drop zone, recent conversions, statistics |
| **Convert** | Single file conversion with detailed settings |
| **Photos** | Browse and select videos from Photos library |
| **Queue** | View and manage conversion queue |
| **Settings** | Configure encoder, paths, and preferences |

## Your First Conversion

### Option 1: Drag and Drop (Fastest)

1. **Open Video Converter** from Applications
2. **Drag a video file** onto the drop zone in the Home tab
3. The file is automatically added to the queue and conversion starts
4. **Monitor progress** in the Queue tab

!!! tip "Multiple Files"
    Drop multiple files at once to add them all to the conversion queue.

### Option 2: Using the Convert Tab

1. Click the **Convert** tab (or press ++ctrl+2++)
2. Click **Browse** to select an input file
3. Choose an output location (or use default)
4. Adjust settings if needed:
    - **Encoder**: Hardware (faster) or Software (smaller files)
    - **Quality**: Lower values = higher quality, larger files
5. Click **Start Conversion**

### Option 3: From Photos Library

1. Click the **Photos** tab (or press ++ctrl+3++)
2. Grant Photos access if prompted
3. Browse your albums and select videos
4. Click **Convert Selected**
5. Videos are added to the queue automatically

## Quick Settings

Access settings with ++ctrl+comma++ or the Settings tab:

| Setting | Recommendation |
|---------|----------------|
| **Encoder** | `Hardware` for speed, `Software` for size |
| **Quality** | `45` (balanced) - lower is better quality |
| **Output Directory** | Your choice, defaults to same as input |
| **Preserve Original** | Enable to keep source files |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ++ctrl+1++ | Home tab |
| ++ctrl+2++ | Convert tab |
| ++ctrl+3++ | Photos tab |
| ++ctrl+4++ | Queue tab |
| ++ctrl+5++ | Settings tab |
| ++ctrl+o++ | Open video file |
| ++ctrl+comma++ | Open preferences |
| ++ctrl+w++ | Close window |

## What's Next?

- **[Detailed GUI Usage](gui-usage.md)** - Complete feature reference
- **[Photos Library Guide](photos-workflow.md)** - Photos integration details
- **[Troubleshooting](../troubleshooting.md)** - Common issues and solutions

!!! success "You're Ready!"
    You now know the basics of Video Converter GUI. For advanced features like batch processing, automation, and menubar integration, see the [detailed usage guide](gui-usage.md).
