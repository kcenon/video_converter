# Photos Library Import API Research

## Overview

This document presents research findings on available APIs and methods for importing converted videos back to the macOS Photos library while preserving metadata.

**Related Issue**: #100 - Research Photos library import APIs and limitations

## Research Questions Summary

| Question | Answer |
|----------|--------|
| Can osxphotos import photos/videos? | Yes, via CLI `osxphotos import` command |
| Does PhotoScript support import? | Yes, via `PhotosLibrary.import_photos()` |
| Can we preserve album membership? | Yes, via AppleScript after import |
| Can we preserve favorites/metadata? | Partially - EXIF preserved automatically, favorites via AppleScript |
| What are the main limitations? | Speed (AppleScript), Shared Albums access, macOS version compatibility |

## API Evaluation

### 1. osxphotos

> "OSXPhotos is a Python app for working with photos and associated metadata in Apple Photos on macOS."
> — [GitHub - RhetTbull/osxphotos](https://github.com/RhetTbull/osxphotos)

#### Import Capabilities

The "Importapalooza release" added import functionality:

```bash
# CLI import
osxphotos import /path/to/video.mp4 --album "Converted Videos"

# Import with metadata from export database
osxphotos import /path/to/videos --exportdb /path/to/export.db
```

#### Limitations

- Import primarily designed for recreating libraries from osxphotos exports
- Limited direct Python API for import operations
- Uses AppleScript internally for import operations

#### Recommendation

**Use for**: Metadata extraction, library querying, verification after import

### 2. PhotoScript

> "Automate Apple/MacOS Photos app with python. Wraps AppleScript calls in python."
> — [GitHub - RhetTbull/PhotoScript](https://github.com/RhetTbull/PhotoScript)

#### Import Capabilities

```python
import photoscript

photoslib = photoscript.PhotosLibrary()
new_album = photoslib.create_album("Converted Videos")
photoslib.import_photos(["/path/to/video.mp4"], album=new_album)
```

#### Available Metadata Operations

| Property | Read | Write |
|----------|------|-------|
| title | Yes | Yes |
| description | Yes | Yes |
| keywords | Yes | Yes |
| favorite | Yes | Yes (via AppleScript) |
| albums | Yes | Yes (add to album) |
| date | Yes | No (use ExifTool before import) |
| location | Yes | No (use ExifTool before import) |

#### Limitations

- Slow performance due to Python -> Objective-C -> AppleScript round trips
- Limited by Photos' AppleScript dictionary
- Cannot remove photos from albums (requires workaround)

#### Recommendation

**Use for**: Primary import method, album assignment, favorites setting

### 3. photokit (Work in Progress)

> "Python package for accessing the macOS Photos.app library via Apple's native PhotoKit framework."
> — [GitHub - RhetTbull/photokit](https://github.com/RhetTbull/photokit)

#### Import Capabilities

```python
import photokit

# Methods available (when stable)
photokit.add_video("/path/to/video.mp4")  # Returns UUID
photokit.add_live_photo(photo_path, video_path)
```

#### Status

- **Currently not production-ready**
- Being extracted from osxphotos codebase
- Uses private, undocumented PhotoKit APIs
- Requires macOS Monterey (12.0) or later

#### Recommendation

**Do not use**: Wait for stable release, monitor project progress

### 4. Direct AppleScript

#### Import Syntax

```applescript
tell application "Photos"
    -- Import video file
    set importedItems to import POSIX file "/path/to/video.mp4"

    -- Get imported item UUID
    if (count of importedItems) > 0 then
        set importedPhoto to item 1 of importedItems
        set photoUUID to id of importedPhoto

        -- Set as favorite
        set favorite of importedPhoto to true

        -- Add to album
        if exists album "Converted Videos" then
            add importedItems to album "Converted Videos"
        else
            set newAlbum to make new album named "Converted Videos"
            add importedItems to newAlbum
        end if

        return photoUUID
    end if
end tell
```

#### Key Points

1. **Use `POSIX file`**: String paths fail due to sandboxing
2. **Metadata handling**: Photos reads EXIF automatically from file
3. **Album assignment**: Must be done after import
4. **UUID retrieval**: Available via `id of importedPhoto`

#### Subprocess Integration (Python)

```python
import subprocess

def import_video_applescript(video_path: str, album_name: str) -> str:
    """Import video using AppleScript subprocess."""
    script = f'''
    tell application "Photos"
        set importedItems to import POSIX file "{video_path}" skip check duplicates yes
        if (count of importedItems) > 0 then
            set importedPhoto to item 1 of importedItems
            set photoUUID to id of importedPhoto

            if not (exists album "{album_name}") then
                make new album named "{album_name}"
            end if
            add importedItems to album "{album_name}"

            return photoUUID
        end if
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"AppleScript failed: {result.stderr}")

    return result.stdout.strip()
```

## Edge Cases and Limitations

### iCloud Photo Library

| Scenario | Behavior |
|----------|----------|
| Import to iCloud library | Works, uploads to iCloud automatically |
| Import while offline | Works locally, syncs when online |
| Original in iCloud only | N/A for imports (new files are local first) |

**Mitigation**: Always verify local file exists before import attempt.

### Shared Albums

> "OSXPhotos cannot read shared albums on macOS 26.x (Tahoe)."
> — [osxphotos documentation](https://github.com/RhetTbull/osxphotos)

| Limitation | Impact |
|------------|--------|
| Cannot add to shared albums via AppleScript | Must use native Photos.app |
| Cannot read shared album contents reliably | Skip shared albums in verification |
| 1000 photo download limit per batch | N/A for import operations |

**Mitigation**: Only assign to personal albums; document shared album limitation.

### Live Photos

| Aspect | Status |
|--------|--------|
| Import video component only | Works |
| Import as Live Photo | Requires paired HEIC + MOV |
| photokit `add_live_photo()` | Not yet stable |

**Mitigation**: For now, import converted videos as regular videos; Live Photo recreation is out of scope.

### Folders and Smart Albums

> "Since Catalina, albums inside folders are no longer visible through the albums array/list in AppleScript."
> — [Apple Community](https://discussions.apple.com/thread/253467)

| Type | AppleScript Access |
|------|-------------------|
| Top-level albums | Full access |
| Albums in folders | Limited/broken since macOS Catalina |
| Smart albums | Cannot add items (auto-populated) |

**Mitigation**: Only assign to top-level albums; warn users about folder limitations.

### HDR Videos

| Aspect | Status |
|--------|--------|
| Import HDR video | Works |
| Preserve HDR metadata | Depends on FFmpeg encoding |
| Display in Photos | Requires proper tagging |

**Mitigation**: Ensure FFmpeg preserves HDR metadata during conversion.

## Performance Considerations

### AppleScript Overhead

| Operation | Estimated Time |
|-----------|---------------|
| Import single video | 2-5 seconds |
| Add to album | 0.5-1 second |
| Set favorite | 0.5-1 second |
| Batch import (10 videos) | 20-50 seconds |

> "Every method call has to do a python->Objective C->AppleScript round trip, which makes the interface much slower than native python code."
> — [PhotoScript README](https://github.com/RhetTbull/PhotoScript)

### Batch Import Strategy

```python
# Recommended: Import files individually but batch metadata operations
def batch_import(videos: list[Path], album_name: str) -> list[str]:
    uuids = []
    for video in videos:
        uuid = import_single(video)
        uuids.append(uuid)

    # Batch album assignment
    add_to_album_batch(uuids, album_name)
    return uuids
```

## Recommended Implementation Approach

### Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Photos Re-Import Workflow                    │
├─────────────────────────────────────────────────────────────┤
│  1. Metadata Capture (osxphotos)                            │
│     └─ Read albums, favorites, date, location               │
│                                                              │
│  2. Metadata Embedding (ExifTool)                           │
│     └─ Write date, location, description to file            │
│                                                              │
│  3. Import (AppleScript via subprocess)                     │
│     └─ import POSIX file, get UUID                          │
│                                                              │
│  4. Metadata Application (PhotoScript or AppleScript)       │
│     ├─ Add to albums                                         │
│     ├─ Set favorite                                          │
│     └─ Set title/description if needed                       │
│                                                              │
│  5. Verification (osxphotos)                                │
│     └─ Confirm metadata matches expected values              │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Selection

| Component | Recommended Library | Reason |
|-----------|-------------------|--------|
| Metadata capture | osxphotos | Most complete metadata access |
| Metadata embedding | ExifTool | Industry standard, reliable |
| Video import | AppleScript (subprocess) | Direct control, UUID retrieval |
| Album/favorite assignment | PhotoScript or AppleScript | Python integration |
| Verification | osxphotos | Comprehensive metadata reading |

### Error Handling Strategy

```python
class PhotosImportError(Exception):
    """Base exception for import operations."""
    pass

class ImportTimeoutError(PhotosImportError):
    """Raised when import exceeds timeout."""
    pass

class AlbumNotFoundError(PhotosImportError):
    """Raised when target album doesn't exist."""
    pass

class VerificationFailedError(PhotosImportError):
    """Raised when post-import verification fails."""
    pass
```

## Proof of Concept

### Minimal Import Example

```python
import subprocess
from pathlib import Path

def proof_of_concept_import(video_path: Path) -> str:
    """Minimal proof of concept for Photos import."""
    script = f'''
    tell application "Photos"
        set importedItems to import POSIX file "{video_path}"
        if (count of importedItems) > 0 then
            return id of item 1 of importedItems
        else
            error "Import returned no items"
        end if
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode == 0:
        return result.stdout.strip()
    else:
        raise RuntimeError(f"Import failed: {result.stderr}")

# Test
# uuid = proof_of_concept_import(Path("/path/to/test.mp4"))
# print(f"Imported with UUID: {uuid}")
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| AppleScript API changes | Low | High | Version check, fallback handlers |
| Photos.app crashes during import | Medium | Medium | Retry logic, verification |
| Metadata loss during import | Low | High | Pre-embed metadata in file |
| Slow performance with large batches | High | Medium | Progress reporting, batch limits |
| iCloud sync conflicts | Low | Medium | Verify local file before import |
| Shared album limitations | High | Low | Document limitation, skip shared |

## Conclusion

### Feasibility: Confirmed

The research confirms that implementing Photos library re-import is feasible using:

1. **AppleScript** (via subprocess or PhotoScript) for import operations
2. **osxphotos** for metadata capture and verification
3. **ExifTool** for pre-import metadata embedding

### Recommended Next Steps

1. **Implement PhotosImporter class** (#101) using AppleScript subprocess
2. **Implement metadata preservation** (#103) using ExifTool + AppleScript
3. **Add original handling** (#102) using AppleScript delete/archive
4. **Write comprehensive tests** (#104) with mocked AppleScript

### Known Limitations to Document

- Shared albums cannot be accessed via AppleScript
- Albums in folders may not be accessible on macOS Catalina+
- Live Photo recreation not supported (out of scope)
- Performance limited by AppleScript round trips

## References

- [osxphotos GitHub](https://github.com/RhetTbull/osxphotos)
- [PhotoScript GitHub](https://github.com/RhetTbull/PhotoScript)
- [photokit GitHub](https://github.com/RhetTbull/photokit)
- [Apple Photos AppleScript Dictionary](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide)
- [AppleScript for Photos Community Discussion](https://discussions.apple.com/thread/252917619)
- [MacScripter Photos Import Thread](https://www.macscripter.net/t/help-importing-photos-to-specific-album-in-photos-app/68736)
