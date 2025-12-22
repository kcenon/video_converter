# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Version scheme changed from 1.x.x to 0.x.x.x (project is in active development)

### Added

#### Photos-Specific Progress Display (#97)
- `PhotosProgressDisplay` class for Photos library conversion with rich UI
- Library info panel showing path, video count, total size, and estimated savings
- Two-phase progress tracking: Export (file transfer) and Convert (encoding)
- Photos-specific metadata display: album name, date taken, file size
- Styled summary panel with conversion statistics (successful, failed, saved, elapsed time)
- `_NullPhotosProgress` for quiet mode support (Null Object pattern)
- `PhotosLibraryInfo` dataclass for library information display
- `create_photos_progress()` method added to `ProgressDisplayManager`
- Export progress callback integration in `_run_photos_batch_conversion`

#### Photos Library Permission Check and User Guidance (#96)
- `--check-permissions` flag for verifying Photos library access before conversion
- Rich panel display for permission errors with step-by-step instructions
- `display_photos_permission_error()` function for access denied and not found errors
- `display_photos_permission_success()` function for successful permission check
- `display_photos_library_info()` function for library statistics display
- Quick access command to open System Settings directly
- Improved error handling with `PhotosLibraryNotFoundError` and `PhotosAccessDeniedError`

#### Metadata Preservation for Photos Re-Import (#103)
- `MetadataPreserver` class for preserving metadata during Photos re-import workflow
- `VideoMetadataSnapshot` dataclass for capturing complete video metadata
- `capture_metadata()` method to snapshot original video metadata (albums, favorites, date, location)
- `embed_metadata_in_file()` method to embed date/GPS metadata via ExifTool before import
- `apply_photos_metadata()` method to apply Albums/favorites via AppleScript after import
- `verify_metadata()` method to validate metadata preservation with configurable tolerance
- `MetadataTolerance` dataclass with default, strict, and relaxed presets
- `VerificationResult` dataclass with detailed comparison results
- Exception classes: `MetadataPreservationError`, `MetadataEmbedError`, `MetadataApplicationError`
- Integration with existing `MetadataProcessor` for ExifTool operations
- Support for preserving: albums, favorites, hidden status, date, location, description, keywords

#### Photos Library Re-Import Support (#101)
- `PhotosImporter` class for importing converted videos back to Photos library
- AppleScript integration via `osascript` command for Photos.app automation
- `import_video()` method to import video files and return UUID
- `verify_import()` method to confirm successful import by UUID
- `get_video_info()` method to retrieve imported video metadata
- Configurable timeout (default 5 minutes) for large video imports
- Comprehensive exception hierarchy:
  - `PhotosImportError`: Base exception for import operations
  - `PhotosNotRunningError`: Photos.app activation failure
  - `ImportTimeoutError`: Operation timeout
  - `DuplicateVideoError`: Video already exists in library
  - `ImportFailedError`: General import failure
- New `AppleScriptRunner` utility class for safe AppleScript execution
- `escape_applescript_string()` utility for safe string injection

#### iCloud Drive Folder Support (#88)
- Automatic detection of iCloud stub files (`.filename.icloud` format) in `FolderExtractor`
- `_is_icloud_stub()` and `_is_video_stub()` methods for stub file detection
- `_get_original_path_from_stub()` for inferring actual filename from stub
- `in_cloud` and `stub_path` properties in `FolderVideoInfo` dataclass
- `scan()` method now includes iCloud files with `include_icloud` parameter
- `get_video_info()` handles both local and iCloud stub files
- `in_cloud` counter in `FolderStats` for iCloud file statistics
- `_ensure_file_available()` in Orchestrator for automatic iCloud download
- Integration with existing `iCloudHandler` for download management
- New `FolderConfig` class with iCloud-specific settings:
  - `auto_download_icloud`: Enable/disable automatic downloads (default: True)
  - `icloud_timeout`: Download timeout in seconds (default: 3600)
  - `skip_icloud_on_timeout`: Skip on timeout instead of error (default: True)
  - `include_patterns` and `exclude_patterns` for file filtering
- `OrchestratorConfig` extended with iCloud options
- 15 comprehensive unit tests for iCloud folder support

#### VMAF Quality Measurement (#26)
- `VmafAnalyzer` class for perceptual video quality measurement
- VMAF score calculation between original and converted videos
- `VmafScores` dataclass with min, mean, max, 5th/95th percentile statistics
- `VmafQualityLevel` enum for score interpretation (visually lossless >= 93)
- Support for frame sampling via `sample_interval` for faster analysis
- Graceful handling when libvmaf is not available (`is_available()` check)
- `quick_analyze()` method for fast quality estimation (1:30 sampling)
- Human-readable quality assessment via `get_quality_assessment()`
- Async support with `analyze_async()` method
- 46 comprehensive unit tests
- Exported from `video_converter.processors` package

#### macOS Notification Center Integration
- `NotificationManager` class for sending macOS notifications
- Automatic notifications on batch conversion completion
- Support for success, partial success, and failure notification types
- Summary statistics (videos converted, space saved) in notification body
- `NotificationConfig` for customizing sound and grouping options
- Orchestrator integration with `enable_notifications` option
- Comprehensive unit tests for notification functionality

#### Statistics and Reporting
- Time-based filtering for conversion statistics (today, week, month, all)
- `StatsPeriod` enum for period selection
- `StatisticsReporter` class for formatted output with box drawing
- Enhanced `stats` CLI command with real history integration
- `stats-export` CLI command for JSON/CSV export
- `--detailed` flag for showing recent conversions
- `--period` option for time-based statistics filtering
- `--include-records` option for exporting individual conversion records
- Comprehensive unit tests for statistics features

#### Rich Progress Bar Display (#38)
- New `ui/progress.py` module with Rich-based progress display components
- `SingleFileProgressDisplay` class showing filename, progress bar, size (original -> current), ETA, and encoding speed
- `BatchProgressDisplay` class with combined overall and per-file progress tracking
- `IndeterminateSpinner` class for operations with unknown duration
- `ProgressDisplayManager` for unified progress creation with quiet mode support
- Null object pattern implementations for quiet mode (no output pollution)
- Custom Rich columns: `SizeProgressColumn`, `SpeedColumn`, `ETAColumn`
- Integration with existing `ProgressInfo` from `converters/progress.py`
- 35 unit tests for all progress display components

#### Service Status Query (#36)
- `calculate_next_run()` method for computing next scheduled execution time
- `get_last_run_info()` method for parsing service logs to get last run details
- `get_detailed_status()` method combining status, schedule, history, and statistics
- `LastRunInfo` dataclass for last run timestamp, success status, and statistics
- `DetailedServiceStatus` dataclass for comprehensive service information
- `format_bytes()` helper function for human-readable byte display
- Enhanced CLI `status` command with next run time, last run result, and conversion statistics
- Launchd weekday to Python weekday conversion for accurate schedule calculation
- 26 new tests for service status functionality

#### launchctl Wrapper for Service Management (#35)
- Public `load()`, `unload()`, `restart()` methods in ServiceManager
- Permission checking for plist files before loading
- CLI commands: `service-start`, `service-stop`, `service-load`, `service-unload`, `service-restart`, `service-logs`
- `--follow` and `--stderr` options for service-logs command
- Tests for load/unload/restart operations and permission checks

#### Failure Isolation and Error Recovery (#32)
- ErrorCategory enum for classifying conversion failures (input, encoding, validation, metadata, disk space, permission)
- RecoveryAction enum for recommended recovery actions per error category
- ErrorRecoveryManager class for centralized error handling
- Automatic error classification based on error message patterns
- Disk space monitoring with configurable minimum threshold
- Automatic pause on low disk space with `pause_on_disk_full` option
- Partial output file cleanup on conversion failure
- FailureRecord dataclass for tracking failed conversions
- Manual retry API: `retry_failed()`, `retry_all_failed()` methods
- Failure summary with statistics by error category
- Failed file movement with collision handling

#### Concurrent Processing Support (#31)
- ConcurrentProcessor class for parallel video processing with configurable max concurrent jobs
- ResourceMonitor for system resource tracking (CPU, memory utilization)
- AggregatedProgress for combined progress tracking across concurrent jobs
- Semaphore-based concurrency limiting to prevent system overload
- Automatic switching between sequential and concurrent processing based on max_concurrent setting
- Thread-safe job progress management
- Comprehensive unit tests (32 test cases)

#### Validation Retry Logic (#27)
- RetryManager class with configurable retry strategies
- Four-stage retry: same settings → switch encoder → adjust quality → final attempt
- Automatic encoder fallback (Hardware ↔ Software) on encoder-related failures
- CRF adjustment for compression issues with configurable step size
- RetryConfig for customizing max attempts, encoder switching, quality adjustment
- RetryAttempt tracking with timing and failure classification
- RetryResult with comprehensive failure reporting
- Retry tracking fields in ConversionResult (retry_count, retry_strategy_used, retry_history)
- Enable/disable retry via OrchestratorConfig.enable_retry
- 35 unit tests covering all retry scenarios

#### Metadata Verification System (#22)
- MetadataVerifier class for comprehensive metadata comparison between original and converted files
- ToleranceSettings dataclass for configurable comparison thresholds (date: 1s, GPS: 0.000001°, duration: 0.1s)
- CheckResult and VerificationResult dataclasses for structured verification results
- Support for date/time, GPS, camera, video, and audio metadata verification
- Category-based verification with selectable categories
- Pre-configured tolerance profiles (strict, default, relaxed)
- Comprehensive unit tests (43 test cases)

#### File Timestamp Synchronization (#21)
- TimestampSynchronizer class for copying timestamps from original to converted files
- FileTimestamps dataclass for timestamp extraction and management
- Support for birth time (creation date) on macOS via SetFile command
- Modification time and access time synchronization using os.utime
- TimestampVerificationResult for comparing timestamps with configurable tolerance
- Integration with Orchestrator pipeline (METADATA stage)
- preserve_timestamps config option (default: True)
- Comprehensive unit tests (23 test cases)

#### Conversion History for Duplicate Prevention (#18)
- ConversionHistory class for tracking converted videos
- ConversionRecord dataclass for storing conversion metadata
- HistoryStatistics for aggregated conversion statistics
- Support for UUID (Photos) and file hash identification
- JSON persistence with atomic file writes
- Export functionality (JSON, CSV formats)
- Thread-safe operations with RLock
- Comprehensive unit tests (41 test cases)

#### iCloud Video Download Handling (#16)
- iCloudHandler class for detecting and downloading iCloud-stored videos
- CloudStatus enum (LOCAL, CLOUD_ONLY, DOWNLOADING, FAILED, UNKNOWN)
- Automatic iCloud status detection using stub file analysis
- Download triggering via macOS brctl command (requires macOS 12+)
- Download progress tracking with DownloadProgress dataclass
- Configurable download timeout (icloud_timeout option)
- Option to skip cloud-only videos (skip_cloud_only option)
- Eviction support for freeing local storage space

#### Real-time Progress Monitoring (#11)
- ProgressInfo dataclass with ETA calculation properties (eta_seconds, eta_formatted)
- ProgressParser for parsing FFmpeg stderr output
- ProgressMonitor for callback-based progress updates with throttling
- create_simple_callback helper for console progress display
- Support for both simple (float 0-1) and detailed (ProgressInfo) callbacks in BaseConverter
- Human-readable size formatting (size_formatted property)

#### 10-bit HDR Encoding Support
- Add `bit_depth` option for 8-bit and 10-bit encoding
- Add `hdr` option for HDR10 (BT.2020 PQ) color space encoding
- Software encoder (libx265) now supports 10-bit output with yuv420p10le pixel format
- HDR x265-params for professional-grade HDR content preservation

#### Folder Extractor
- FolderExtractor class for direct video conversion from filesystem folders
- Recursive directory scanning with include/exclude pattern filtering
- Video codec detection and conversion candidate identification
- FolderVideoInfo and FolderStats dataclasses for structured video information
- Comprehensive error handling (FolderNotFoundError, FolderAccessDeniedError, InvalidVideoFileError)
- Unit tests with 62 test cases covering all functionality

## [0.1.0.0] - 2025-12-22

### Added

#### Core Conversion
- H.264 to H.265 (HEVC) video conversion with hardware acceleration (VideoToolbox)
- Software encoder fallback with x265 for maximum compatibility
- Configurable quality settings (1-100 for hardware, CRF 0-51 for software)
- Real-time progress tracking with speed and ETA estimation
- Automatic codec detection using FFprobe

#### Photos Library Integration
- macOS Photos library access via osxphotos
- H.264 video filtering from Photos library
- Album-based video selection
- Video export from Photos library

#### Metadata Preservation
- GPS coordinate preservation across conversions
- ExifTool integration for comprehensive metadata handling
- File timestamp synchronization (creation date, modification date)
- Critical metadata verification after conversion

#### Quality Validation
- Video integrity validation using FFprobe
- Compression ratio validation
- Video property comparison (resolution, duration, audio)
- GPS coordinate verification

#### Orchestration
- Batch conversion workflow with priority ordering
- Session state management for resumable conversions
- Pause/resume functionality
- Failure isolation and error recovery

#### Automation
- macOS launchd integration for scheduled conversions
- Service install/uninstall commands
- Daily/weekly scheduling support
- Watch path monitoring

#### CLI Interface
- Complete command-line interface with Rich formatting
- `convert` command for single file or directory conversion
- `photos` command for Photos library conversion
- `scan` command to preview conversion candidates
- `config` command for configuration management
- `service` command for automation management
- `status` command for service status

#### Configuration
- JSON-based configuration system
- Environment variable overrides
- Configurable paths, encoding settings, and automation options

#### Logging
- Structured logging with file and console output
- Log rotation support
- Configurable log levels

### Documentation
- Comprehensive README with installation and usage instructions
- Software Requirements Specification (SRS)
- Software Design Specification (SDS)
- Product Requirements Document (PRD)
- Architecture documentation

[0.1.0.0]: https://github.com/kcenon/video_converter/releases/tag/v0.1.0.0
[Unreleased]: https://github.com/kcenon/video_converter/compare/v0.1.0.0...HEAD
