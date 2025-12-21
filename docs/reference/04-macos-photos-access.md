# macOS Photos Library Access Methods

## Overview

This document covers various methods for programmatically accessing videos stored in the macOS Photos app.

## Photos Library Structure

### Default Location

```
~/Pictures/Photos Library.photoslibrary/
├── database/
│   ├── Photos.sqlite          # Main database
│   ├── Photos.sqlite-wal
│   └── Photos.sqlite-shm
├── originals/                 # Original files
│   ├── 0/
│   ├── 1/
│   └── ...
├── resources/
│   └── derivatives/           # Edited versions
└── private/
```

> "Photos and videos imported into Photos are stored in the photo library in your Pictures folder."
> — [Apple Support](https://support.apple.com/guide/photos/photo-library-overview-pht211de786/mac)

### System Photo Library

The System Photo Library integrates with:

- iCloud Photos
- My Photo Stream
- Shared Albums
- Other apps like iMovie, Pages, Keynote

## Method 1: osxphotos (Recommended)

### Introduction

osxphotos is a Python-based Photos library access tool:

> "OSXPhotos is a Python app for working with photos and associated metadata in Apple Photos on macOS. It includes a package that provides programmatic access to the Photos library, photos, and metadata."
> — [GitHub - RhetTbull/osxphotos](https://github.com/RhetTbull/osxphotos)

### Installation

```bash
# Using uv (recommended)
uv tool install osxphotos

# Using pip
pip install osxphotos
```

### System Requirements

- macOS Sierra (10.12.6) ~ macOS Sequoia (15.7.2)
- Python >= 3.10, <= 3.14
- Supports x86 and Apple Silicon (M1/M2/M3/M4)

### CLI Usage

#### Export Videos Only

```bash
# Export all videos
osxphotos export ~/exported_videos --only-movies

# Videos from specific album only
osxphotos export ~/exported_videos --only-movies --album "Vacation 2024"

# Videos from specific date range
osxphotos export ~/exported_videos --only-movies \
  --from-date "2024-01-01" \
  --to-date "2024-12-31"
```

#### Filter H.264 Codec Videos Only

```bash
# Check video list with query
osxphotos query --only-movies --json | \
  jq '.[] | select(.path | contains(".MOV") or contains(".mp4"))'
```

#### Get Original File Paths

```bash
# Output original paths
osxphotos query --only-movies --print "{original_filename}: {path}"
```

### Python API Usage

```python
import osxphotos

# Open Photos library
photosdb = osxphotos.PhotosDB()

# Get all videos
videos = [p for p in photosdb.photos() if p.ismovie]

for video in videos:
    print(f"Name: {video.original_filename}")
    print(f"Path: {video.path}")
    print(f"Date: {video.date}")
    print(f"Location: {video.location}")
    print(f"Albums: {video.albums}")
    print(f"Codec: {video.exif_info}")
    print("---")
```

#### Video Export Example

```python
import osxphotos
from pathlib import Path

photosdb = osxphotos.PhotosDB()
export_dir = Path.home() / "exported_videos"
export_dir.mkdir(exist_ok=True)

for video in photosdb.photos():
    if video.ismovie and video.path:
        # Export original video
        exported = video.export(str(export_dir))
        print(f"Exported: {exported}")
```

## Method 2: PhotoKit Framework (Swift/Objective-C)

### Introduction

PhotoKit is Apple's official framework for accessing the Photos library:

> "Using PhotoKit, you can work with image and video assets managed by the Photos app, including iCloud Photos and Live Photos."
> — [Apple Developer Documentation](https://developer.apple.com/documentation/photokit)

### Swift Example: Fetch All Videos

```swift
import Photos

func fetchAllVideos() {
    let fetchOptions = PHFetchOptions()
    fetchOptions.sortDescriptors = [
        NSSortDescriptor(key: "creationDate", ascending: false)
    ]

    let videos = PHAsset.fetchAssets(
        with: .video,
        options: fetchOptions
    )

    videos.enumerateObjects { (asset, index, stop) in
        print("Video: \(asset.localIdentifier)")
        print("Date: \(asset.creationDate ?? Date())")
        print("Duration: \(asset.duration) seconds")
        print("---")
    }
}
```

### Swift Example: Export Video

```swift
import Photos
import AVFoundation

func exportVideo(asset: PHAsset, to outputURL: URL) {
    let options = PHVideoRequestOptions()
    options.version = .original
    options.deliveryMode = .highQualityFormat
    options.isNetworkAccessAllowed = true  // Allow iCloud download

    PHImageManager.default().requestExportSession(
        forVideo: asset,
        options: options,
        exportPreset: AVAssetExportPresetPassthrough
    ) { exportSession, info in
        guard let session = exportSession else { return }

        session.outputURL = outputURL
        session.outputFileType = .mp4

        session.exportAsynchronously {
            switch session.status {
            case .completed:
                print("Export completed: \(outputURL)")
            case .failed:
                print("Failed: \(session.error?.localizedDescription ?? "")")
            default:
                break
            }
        }
    }
}
```

### Permission Request

```swift
import Photos

func requestPhotoLibraryAccess() {
    PHPhotoLibrary.requestAuthorization(for: .readWrite) { status in
        switch status {
        case .authorized:
            print("Full access granted")
        case .limited:
            print("Limited access")
        case .denied, .restricted:
            print("Access denied")
        default:
            break
        }
    }
}
```

## Method 3: Direct Database Access (Advanced)

### SQLite Database Query

⚠️ **Warning**: Direct DB access is not recommended. Apple may change the schema.

```bash
# Copy Photos library DB (work read-only)
cp ~/Pictures/Photos\ Library.photoslibrary/database/Photos.sqlite /tmp/

# Query with SQLite
sqlite3 /tmp/Photos.sqlite

# Query video assets
SELECT
    ZASSET.ZUUID,
    ZASSET.ZFILENAME,
    ZASSET.ZDATECREATED,
    ZASSET.ZDURATION
FROM ZASSET
WHERE ZASSET.ZKIND = 1  -- 1 = video
LIMIT 10;
```

## Method 4: Using Finder/Spotlight

### Find Videos with Spotlight Query

```bash
# Search for videos in Photos library
mdfind -onlyin ~/Pictures/Photos\ Library.photoslibrary \
  'kMDItemContentType == "public.movie"'
```

### Using AppleScript

```applescript
tell application "Photos"
    set allVideos to every media item whose type description is "Movie"

    repeat with v in allVideos
        set vidName to filename of v
        set vidDate to date of v
        log "Video: " & vidName & " - " & vidDate
    end repeat
end tell
```

## iCloud Considerations

### Local Storage vs iCloud

> "The PhotoKit API doesn't necessarily distinguish between photos available on the device and those available in the cloud."
> — [objc.io](https://www.objc.io/issues/21-camera-and-photos/the-photos-framework/)

### Network Access Control

```swift
// Disable network access in PhotoKit (local files only)
let options = PHVideoRequestOptions()
options.isNetworkAccessAllowed = false
```

### iCloud Handling in osxphotos

```bash
# Include iCloud video download
osxphotos export ~/Videos --only-movies --download-missing

# Local videos only
osxphotos export ~/Videos --only-movies --skip-missing
```

## Metadata Access

### Extract Metadata with osxphotos

```python
import osxphotos

photosdb = osxphotos.PhotosDB()

for video in photosdb.photos():
    if video.ismovie:
        metadata = {
            "filename": video.original_filename,
            "date": video.date,
            "location": video.location,  # (latitude, longitude)
            "duration": video.duration,
            "albums": video.albums,
            "keywords": video.keywords,
            "persons": video.persons,
            "favorite": video.favorite,
            "hidden": video.hidden,
        }
        print(metadata)
```

### Metadata with PhotoKit

```swift
let asset: PHAsset = // ...

// Basic metadata
let creationDate = asset.creationDate
let location = asset.location  // CLLocation
let duration = asset.duration
let isFavorite = asset.isFavorite

// EXIF data (using PHAssetResource)
let resources = PHAssetResource.assetResources(for: asset)
for resource in resources {
    print("Filename: \(resource.originalFilename)")
    print("UTI: \(resource.uniformTypeIdentifier)")
}
```

## Recommended Access Methods

| Use Case | Recommended Method |
|----------|-------------------|
| Quick scripting/automation | osxphotos CLI |
| Python integration | osxphotos Python API |
| Swift/macOS app development | PhotoKit Framework |
| One-time tasks | AppleScript |
| Advanced customization | PhotoKit + osxphotos combination |

## References

- [osxphotos GitHub](https://github.com/RhetTbull/osxphotos)
- [osxphotos Documentation](https://rhettbull.github.io/osxphotos/overview.html)
- [Apple PhotoKit Documentation](https://developer.apple.com/documentation/photokit)
- [Apple - System Photo Library](https://support.apple.com/en-us/104946)
- [objc.io - The Photos Framework](https://www.objc.io/issues/21-camera-and-photos/the-photos-framework/)
