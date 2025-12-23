# Error Handling Examples

Examples for handling various error scenarios.

## Conversion Errors

### FFmpeg Failure

```python
from video_converter.core.orchestrator import Orchestrator
from video_converter.core.config import Config
from video_converter.core.types import ConversionRequest

async def safe_convert(input_path: Path, output_path: Path):
    """Convert with proper error handling."""
    config = Config.load()
    orchestrator = Orchestrator(config)

    try:
        result = await orchestrator.convert_single(input_path, output_path)
        if result.success:
            print(f"Success: {result.compression_ratio:.1%} saved")
        else:
            print(f"Failed: {result.error_message}")
    except FFmpegError as e:
        print(f"FFmpeg error: {e}")
        # Try software encoder as fallback
        result = await orchestrator.convert_single(
            input_path, output_path, encoder="software"
        )
    except FileNotFoundError:
        print("Input file not found")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Retry with Exponential Backoff

```python
from video_converter.processors.retry_manager import RetryManager, RetryConfig

async def convert_with_retry(input_path: Path, output_path: Path):
    """Convert with automatic retry on failure."""
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        exponential_base=2.0
    )

    retry_manager = RetryManager(retry_config)

    async def do_convert():
        result = await converter.convert(ConversionRequest(
            input_path=input_path,
            output_path=output_path
        ))
        if not result.success:
            raise ConversionError(result.error_message)
        return result

    try:
        result = await retry_manager.execute(do_convert)
        print(f"Success after {retry_manager.attempts} attempts")
    except MaxRetriesExceeded:
        print(f"Failed after {retry_config.max_retries} attempts")
```

## Validation Errors

### Quality Validation

```python
from video_converter.processors.quality_validator import QualityValidator
from video_converter.processors.vmaf_analyzer import VmafAnalyzer

async def validate_conversion(original: Path, converted: Path):
    """Validate conversion quality."""
    validator = QualityValidator()

    # Basic validation
    result = await validator.validate(original, converted)

    if not result.valid:
        print("Validation failed:")
        for error in result.errors:
            print(f"  - {error}")
        return False

    # VMAF validation (optional)
    vmaf = VmafAnalyzer()
    scores = await vmaf.analyze(original, converted)

    if scores.mean < 85.0:
        print(f"Low VMAF score: {scores.mean:.1f}")
        return False

    print(f"Validation passed (VMAF: {scores.mean:.1f})")
    return True
```

### Metadata Verification

```python
from video_converter.processors.gps import GPSHandler

async def verify_metadata(original: Path, converted: Path):
    """Verify metadata was preserved."""
    gps_handler = GPSHandler()

    # Extract GPS from both files
    original_gps = gps_handler.extract(original)
    converted_gps = gps_handler.extract(converted)

    if original_gps and not converted_gps:
        print("GPS data was lost during conversion!")
        # Attempt to fix
        gps_handler.copy(original, converted)
        return False

    if original_gps and converted_gps:
        if not original_gps.matches(converted_gps):
            print("GPS coordinates don't match!")
            return False

    print("Metadata verification passed")
    return True
```

## File Access Errors

### Photos Library Access

```python
from video_converter.extractors.photos_extractor import PhotosExtractor

def check_photos_access():
    """Check Photos library access permission."""
    try:
        extractor = PhotosExtractor()
        videos = extractor.scan_videos(limit=1)
        print("Photos access: OK")
        return True
    except PermissionError:
        print("Photos access denied!")
        print("Grant access in System Preferences > Privacy > Photos")
        return False
    except PhotosLibraryNotFound:
        print("Photos library not found")
        return False
```

### iCloud Download Errors

```python
from video_converter.extractors.icloud_handler import iCloudHandler, CloudStatus

async def handle_icloud_video(video_info):
    """Handle iCloud-only video."""
    icloud = iCloudHandler()

    status = icloud.get_status(video_info.path)

    if status == CloudStatus.LOCAL:
        return video_info.path

    if status == CloudStatus.DOWNLOADING:
        print("Video is already downloading...")
        await icloud.wait_for_download(video_info.path, timeout=600)

    if status == CloudStatus.CLOUD_ONLY:
        print("Requesting download from iCloud...")
        try:
            await icloud.download(video_info.path, timeout=600)
        except iCloudTimeoutError:
            print("iCloud download timed out")
            raise
        except iCloudQuotaExceeded:
            print("iCloud quota exceeded")
            raise

    return video_info.path
```

## Batch Error Handling

### Skip and Continue

```python
async def batch_convert_resilient(videos: list[Path]):
    """Convert batch, skipping failures."""
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }

    for video in videos:
        try:
            result = await convert_single(video)
            if result.success:
                results["success"].append(video)
            else:
                results["failed"].append((video, result.error_message))
        except SkipVideoError as e:
            results["skipped"].append((video, str(e)))
        except Exception as e:
            results["failed"].append((video, str(e)))
            # Log but continue
            logger.error(f"Failed to convert {video}: {e}")

    # Summary
    print(f"Success: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Skipped: {len(results['skipped'])}")

    return results
```

### Error Report Generation

```python
import json
from datetime import datetime

def generate_error_report(results: dict, output_path: Path):
    """Generate detailed error report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results["success"]) + len(results["failed"]) + len(results["skipped"]),
            "success": len(results["success"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"])
        },
        "failures": [
            {"file": str(path), "error": error}
            for path, error in results["failed"]
        ],
        "skipped": [
            {"file": str(path), "reason": reason}
            for path, reason in results["skipped"]
        ]
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Error report saved to {output_path}")
```

## CLI Error Handling

```bash
#!/bin/bash
# Robust conversion script with error handling

set -e  # Exit on error

log_file="conversion_$(date +%Y%m%d_%H%M%S).log"

run_conversion() {
    video-converter run --mode photos 2>&1 | tee "$log_file"
    return ${PIPESTATUS[0]}
}

if run_conversion; then
    echo "Conversion completed successfully"
    osascript -e 'display notification "Conversion complete" with title "Video Converter"'
else
    echo "Conversion failed - check $log_file for details"
    osascript -e 'display notification "Conversion failed" with title "Video Converter"'
    exit 1
fi
```
