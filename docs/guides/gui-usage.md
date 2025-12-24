# GUI Detailed Usage

Complete reference for Video Converter's graphical interface.

## Main Window Overview

The Video Converter GUI uses a tab-based layout with five main sections:

```mermaid
graph LR
    A[Home] --> B[Convert]
    B --> C[Photos]
    C --> D[Queue]
    D --> E[Settings]
```

The window has a minimum size of 900×600 pixels and centers on your screen at launch.

---

## Home Tab

The Home tab serves as your dashboard and primary drop zone.

### Drag and Drop Zone

The central drop zone accepts:

- **Single video file**: Opens in Convert tab for detailed settings
- **Multiple video files**: Added directly to the conversion queue
- **Folders**: All videos in the folder are scanned and queued

!!! tip "Supported Formats"
    Drag and drop supports: `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`

### Quick Action Buttons

| Button | Action |
|--------|--------|
| **Browse Photos Library** | Opens Photos tab to select videos from Photos.app |
| **Open Video File** | Opens file picker dialog |

### Recent Conversions

Displays a scrollable list of recently converted files with:

- Original filename
- Conversion date and time
- Status (success/failed)
- Space saved

### Statistics Bar

The bottom bar shows real-time statistics:

| Metric | Description |
|--------|-------------|
| **Hardware Encoder** | Shows if VideoToolbox is available |
| **Space Saved** | Total storage saved by conversions |
| **Videos Converted** | Running count of successful conversions |

---

## Convert Tab

The Convert tab provides detailed control over single-file conversions.

### Input Selection

1. Click **Browse** or drag a file to select input
2. File information displays:
    - Filename and path
    - Duration and resolution
    - Current codec and file size

### Output Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **Output Path** | Where to save the converted file | Same directory as input |
| **Filename** | Output filename (auto-generated with `_hevc` suffix) | `{input}_hevc.mp4` |

### Encoding Settings

#### Encoder Type

| Encoder | Pros | Cons |
|---------|------|------|
| **Hardware** | Very fast, low CPU usage | Slightly larger files |
| **Software** | Smaller files, better compression | Slower, high CPU usage |

#### Quality Settings

=== "Hardware Encoder"

    | Quality Value | Description | Use Case |
    |---------------|-------------|----------|
    | 1-30 | High quality, larger files | Archival, editing source |
    | 30-50 | Balanced | General use |
    | 50-100 | Lower quality, smaller files | Sharing, streaming |

=== "Software Encoder"

    | CRF Value | Description | Use Case |
    |-----------|-------------|----------|
    | 0-18 | Visually lossless | Archival |
    | 18-23 | High quality | General use |
    | 23-28 | Smaller files | Web, mobile |
    | 28-51 | Low quality | Testing |

### Conversion Controls

| Button | Action | Shortcut |
|--------|--------|----------|
| **Start Conversion** | Begin conversion process | - |
| **Cancel** | Stop current conversion | - |

### Progress Display

During conversion, the view shows:

- Progress bar with percentage
- Estimated time remaining (ETA)
- Current encoding speed (fps)
- Current frame being processed

---

## Photos Tab

Browse and convert videos directly from your Photos library.

### First-Time Setup

!!! warning "Permission Required"
    Photos access requires permission. If not already granted:

    1. Go to **System Settings** > **Privacy & Security** > **Photos**
    2. Enable access for Video Converter
    3. Restart the application

### Album Browser

The left sidebar displays:

- **All Videos**: Every video in your library
- **Albums**: User-created albums containing videos
- **Smart Albums**: Auto-generated albums (Favorites, etc.)

### Video Grid

The main area shows video thumbnails with:

- Preview image
- Duration
- iCloud status (local/cloud)
- Selection checkbox

### Selection and Conversion

1. Click videos to select (++cmd+click++ for multiple)
2. Use **Select All** for batch selection
3. Click **Convert Selected** to add to queue

### iCloud Integration

| Status | Icon | Description |
|--------|------|-------------|
| **Local** | - | Video is on this Mac |
| **iCloud** | ☁️ | Video is in iCloud only |
| **Downloading** | ⟳ | Currently downloading from iCloud |

!!! info "iCloud Videos"
    Videos stored only in iCloud will be downloaded automatically before conversion.

---

## Queue Tab

Manage all pending and active conversions.

### Queue List

Each item in the queue displays:

| Column | Description |
|--------|-------------|
| **Status** | Pending, Converting, Complete, Failed |
| **Filename** | Name of the video file |
| **Size** | Original file size |
| **Progress** | Conversion progress bar |
| **ETA** | Estimated time remaining |

### Queue Controls

| Button | Action |
|--------|--------|
| **Pause All** | Pause all conversions |
| **Resume All** | Resume paused conversions |
| **Cancel All** | Cancel and remove all pending items |
| **Clear Completed** | Remove finished items from list |

### Individual Item Actions

Right-click on any queue item for:

- **Remove from Queue**: Cancel this conversion
- **Open in Finder**: Show the source file
- **View Details**: Open detailed status

### Queue Behavior

- Maximum concurrent conversions: 2 (configurable in Settings)
- Failed items remain in queue with error message
- Completed items show final file size and savings

---

## Settings Tab

Configure all application preferences.

### Encoding Settings

#### Encoder Selection

| Option | Description |
|--------|-------------|
| **Hardware (VideoToolbox)** | Uses Apple's hardware encoder |
| **Software (libx265)** | Uses CPU-based x265 encoder |

#### Quality Slider

Adjust encoding quality:

- **Hardware**: 1-100 (lower = better)
- **Software CRF**: 0-51 (lower = better)

#### Preset (Software Only)

| Preset | Speed | Compression |
|--------|-------|-------------|
| ultrafast | Fastest | Lowest |
| superfast | Very fast | Low |
| veryfast | Fast | Below average |
| faster | Above average | Average |
| fast | Average | Above average |
| **medium** | Below average | High |
| slow | Slow | Very high |
| slower | Very slow | Higher |
| veryslow | Slowest | Highest |

### Path Settings

| Setting | Description |
|---------|-------------|
| **Output Directory** | Default location for converted files |
| **Temp Directory** | Location for temporary files during conversion |
| **Use Source Directory** | Save output alongside source file |

### Processing Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Concurrent Conversions** | Max simultaneous conversions | 2 |
| **Preserve Original** | Keep source files after conversion | Enabled |
| **Delete on Success** | Remove source after successful conversion | Disabled |

### Notification Settings

| Setting | Description |
|---------|-------------|
| **Desktop Notifications** | Show macOS notifications on completion |
| **Sound** | Play sound on conversion complete |
| **Show in Menubar** | Display menubar icon with progress |

### Save Settings

Click **Save Settings** to persist your configuration. Settings are automatically saved when closing the application.

---

## Menubar App

The menubar app provides background monitoring without keeping the main window open.

### Menubar Icon

When enabled, a small icon appears in the macOS menu bar showing:

- **Idle**: Static icon when no conversions
- **Converting**: Animated icon with progress percentage

### Menubar Menu

Click the icon to access:

| Item | Action |
|------|--------|
| **Progress** | Shows current conversion status |
| **Pause/Resume** | Toggle pause on current conversion |
| **Cancel** | Cancel current conversion |
| **Open Video Converter** | Show main window |
| **Quit** | Exit the application |

---

## Keyboard Shortcuts

### Navigation

| Shortcut | Action |
|----------|--------|
| ++ctrl+1++ | Go to Home tab |
| ++ctrl+2++ | Go to Convert tab |
| ++ctrl+3++ | Go to Photos tab |
| ++ctrl+4++ | Go to Queue tab |
| ++ctrl+5++ | Go to Settings tab |

### File Operations

| Shortcut | Action |
|----------|--------|
| ++ctrl+o++ | Open video file |
| ++ctrl+w++ | Close window |

### Application

| Shortcut | Action |
|----------|--------|
| ++ctrl+comma++ | Open Preferences/Settings |
| ++ctrl+q++ | Quit application |

---

## Tips and Best Practices

### For Best Performance

1. **Use Hardware Encoder** for everyday conversions
2. **Limit concurrent conversions** to 2 on most Macs
3. **Close other heavy applications** during large batch jobs
4. **Use local storage** for output (not network drives)

### For Best Quality

1. **Use Software Encoder** with CRF 18-22
2. **Use `slow` preset** for better compression
3. **Test with a short clip** before batch processing

### For Best Organization

1. **Create a dedicated output folder** in Settings
2. **Enable "Preserve Original"** until you verify results
3. **Use the Queue tab** to monitor batch conversions
4. **Clear completed items** regularly to keep queue clean

---

## See Also

- **[Quick Start Guide](gui-quickstart.md)** - Get started in 5 minutes
- **[CLI Usage](cli-usage.md)** - Command-line interface reference
- **[Photos Workflow](photos-workflow.md)** - Detailed Photos integration
- **[Troubleshooting](../troubleshooting.md)** - Common issues and solutions
