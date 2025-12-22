# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-22

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

## [Unreleased]

### Added

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

#### Real-time Progress Monitoring (#11)
- ProgressInfo dataclass with ETA calculation properties (eta_seconds, eta_formatted)
- ProgressParser for parsing FFmpeg stderr output
- ProgressMonitor for callback-based progress updates with throttling
- create_simple_callback helper for console progress display
- Support for both simple (float 0-1) and detailed (ProgressInfo) callbacks in BaseConverter
- Human-readable size formatting (size_formatted property)

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

#### iCloud Video Download Handling (#16)
- iCloudHandler class for detecting and downloading iCloud-stored videos
- CloudStatus enum (LOCAL, CLOUD_ONLY, DOWNLOADING, FAILED, UNKNOWN)
- Automatic iCloud status detection using stub file analysis
- Download triggering via macOS brctl command (requires macOS 12+)
- Download progress tracking with DownloadProgress dataclass
- Configurable download timeout (icloud_timeout option)
- Option to skip cloud-only videos (skip_cloud_only option)
- Eviction support for freeing local storage space

#### Conversion History for Duplicate Prevention (#18)
- ConversionHistory class for tracking converted videos
- ConversionRecord dataclass for storing conversion metadata
- HistoryStatistics for aggregated conversion statistics
- Support for UUID (Photos) and file hash identification
- JSON persistence with atomic file writes
- Export functionality (JSON, CSV formats)
- Thread-safe operations with RLock
- Comprehensive unit tests (41 test cases)

#### File Timestamp Synchronization (#21)
- TimestampSynchronizer class for copying timestamps from original to converted files
- FileTimestamps dataclass for timestamp extraction and management
- Support for birth time (creation date) on macOS via SetFile command
- Modification time and access time synchronization using os.utime
- TimestampVerificationResult for comparing timestamps with configurable tolerance
- Integration with Orchestrator pipeline (METADATA stage)
- preserve_timestamps config option (default: True)
- Comprehensive unit tests (23 test cases)

#### Metadata Verification System (#22)
- MetadataVerifier class for comprehensive metadata comparison between original and converted files
- ToleranceSettings dataclass for configurable comparison thresholds (date: 1s, GPS: 0.000001°, duration: 0.1s)
- CheckResult and VerificationResult dataclasses for structured verification results
- Support for date/time, GPS, camera, video, and audio metadata verification
- Category-based verification with selectable categories
- Pre-configured tolerance profiles (strict, default, relaxed)
- Comprehensive unit tests (43 test cases)

#### Concurrent Processing Support (#31)
- ConcurrentProcessor class for parallel video processing with configurable max concurrent jobs
- ResourceMonitor for system resource tracking (CPU, memory utilization)
- AggregatedProgress for combined progress tracking across concurrent jobs
- Semaphore-based concurrency limiting to prevent system overload
- Automatic switching between sequential and concurrent processing based on max_concurrent setting
- Thread-safe job progress management
- Comprehensive unit tests (32 test cases)

### Planned
- Rich progress bar display
- Statistics and reporting
- macOS Notification Center integration
- VMAF quality measurement (optional)

[1.0.0]: https://github.com/kcenon/video_converter/releases/tag/v1.0.0
[Unreleased]: https://github.com/kcenon/video_converter/compare/v1.0.0...HEAD
