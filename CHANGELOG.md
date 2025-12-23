# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

#### Photos Convert Orchestrator Integration (#171)
- **Refactored Photos batch conversion** to use `orchestrator.run()` instead of direct `converter.convert()` calls
  - Enables concurrent processing via `--max-concurrent` option (1-8 workers)
  - Session persistence for recovery after interruption
  - Disk space monitoring with automatic pause when disk is full
  - VMAF quality measurement support for Photos conversions
  - Automatic retry logic on encoder failures
- **3-phase workflow implementation**:
  - Phase 1: Export all videos from Photos library (sequential)
  - Phase 2: Convert using orchestrator.run() (concurrent)
  - Phase 3: Re-import successful conversions (with original handling)
- **Added `--max-concurrent` option** for Photos mode to control parallel conversion workers

#### CLI Convert Command Orchestrator Integration (#170)
- **Refactored `convert` command** to use `orchestrator.convert_single()` instead of direct `converter.convert()` call
  - Enables full Orchestrator pipeline features for single file conversions
  - VMAF analysis is now properly triggered when `--vmaf` flag is used
  - Output validation is performed when `--validate` flag is used
  - Automatic retry logic on encoder failures through RetryManager
  - Timestamp synchronization preserves original file dates
  - iCloud file handling with automatic download before conversion
- **Added `on_progress_info` parameter to `Orchestrator.convert_single()`**
  - Allows detailed FFmpeg progress tracking (percentage, speed, ETA, current size)
  - Maintains existing progress bar display functionality in CLI

### Added

#### macOS App Packaging (#145)
- **PyInstaller Configuration**: `video_converter.spec` for building standalone macOS .app bundle
  - All dependencies bundled including PySide6, osxphotos, and core modules
  - High DPI support with Retina display optimization
  - File associations for common video formats
  - URL scheme handler for `videoconverter://` links
- **Code Signing Support**: Entitlements and build scripts for proper macOS distribution
  - `entitlements.plist` for hardened runtime and Photos library access
  - `Info.plist` with privacy descriptions and app metadata
  - Support for Developer ID signing and notarization
- **DMG Installer**: `create_dmg.sh` script for creating drag-to-install disk images
  - Styled DMG with Applications folder shortcut
  - Optional integration with `create-dmg` tool for enhanced appearance
  - SHA256 checksum generation for verification
- **Homebrew Cask Formula**: `video-converter.rb` for installation via Homebrew
  - Automatic dependency management (ffmpeg)
  - Zap support for complete uninstallation
  - Caveats with setup instructions
- **Auto-Update Service**: `UpdateService` for checking GitHub releases
  - Async update checking with Qt threading
  - Version comparison and release notes parsing
  - Download URL extraction from release assets
  - `check_for_updates_sync()` for CLI usage

#### GUI Application
- **Photos Library Browser** (#143): Full Photos library integration for the GUI:
  - `PhotosService` for async Photos library access in separate thread
  - Album tree view with video counts loaded from Photos database
  - Video grid with selectable thumbnails generated via ffmpeg
  - H.264/iCloud/favorites filtering options
  - Multi-select with total size calculation
  - iCloud status display with warning for cloud-only videos
  - Permission handling with link to System Settings
  - Batch conversion integration (selected videos go to queue)
  - Loading indicators for async operations
- **Menubar App Integration** (#142): macOS system tray application for background monitoring:
  - Real-time conversion progress display in menubar menu
  - Text-based progress bar visualization (▓░)
  - Pause/resume/cancel controls accessible from menubar
  - System notifications for task completion and errors
  - Main window toggle with single/double click on tray icon
  - Background execution support (app keeps running when window closed)
  - Integration with `ConversionService` for live status updates
- **Drag and Drop Support** (#141): Comprehensive drag and drop functionality:
  - Folder drag support to extract video files automatically
  - Visual feedback showing file count during drag operations
  - Blue border for valid files, red border for invalid files
  - Multiple file drop support with batch queue integration
  - Automatic batch addition to conversion queue with saved settings
- **Settings Persistence** (#140): `SettingsManager` service for persistent settings:
  - JSON-based settings storage in `~/Library/Application Support/VideoConverter/`
  - Automatic load on app startup and save on shutdown
  - Settings categories: encoding, paths, automation, notifications
  - Integration with `MainWindow` for seamless settings management
  - `apply_to_conversion_settings()` for applying saved settings to conversions
- **Main Window UI** (#138): PySide6-based main window with tab navigation:
  - `MainWindow` with 5 tabs: Home, Convert, Photos, Queue, Settings
  - `HomeView` with welcome section, drag & drop zone, and statistics bar
  - `DropZone` widget with visual feedback for drag & drop video files
  - `RecentConversionsList` for displaying conversion history
  - macOS-native theming with dark mode support
  - Keyboard shortcuts for tab navigation (Cmd+1-5)
  - Menu bar with File, Edit, View, Help menus

#### Testing
- **GUI Integration Tests** (#160): Comprehensive integration tests for complete user workflows in `tests/gui/test_gui_integration.py`:
  - File drop to conversion flow (single/multiple files)
  - Photos library to conversion flow
  - Settings persistence across sessions
  - Menubar and main window synchronization
  - Queue management operations (pause/resume/cancel)
  - Tab navigation state preservation
  - Error handling propagation between components
  - 23 test cases covering all main user workflows
  - Tests run in < 1 second with no flaky tests
- **CLI Test Coverage** (#128): Comprehensive test suite for CLI commands in `tests/unit/cli/`:
  - `test_convert_cmd.py` - Convert command tests (VMAF, metadata, encoding modes)
  - `test_run_cmd.py` - Batch conversion tests (folder/Photos modes, filters)
  - `test_status_cmd.py` - Status command tests for all service states
  - `test_config_cmd.py` - Configuration command tests (view, set, setup wizard)
  - `test_service_cmd.py` - Service management tests (install, uninstall, control)
  - `test_stats_cmd.py` - Statistics command tests (view, export, periods)
  - `test_error_handling.py` - Error handling and edge case tests
  - `test_helpers.py` - Helper function tests (parse_time, format_duration, format_size)
  - CLI-specific fixtures in `conftest.py` (mock converters, handlers, managers)
  - 141 test cases covering 17 CLI commands
- **UpdateService Test Coverage** (#159): Comprehensive test suite for `UpdateService` in `tests/gui/test_update_service.py`:
  - `ReleaseInfo` dataclass creation and `from_github_response()` parsing
  - Version comparison logic (`parse_version`, `is_newer_version`)
  - `UpdateCheckWorker` thread signal emissions
  - `UpdateService` async update checking and error handling
  - `check_for_updates_sync()` blocking method for CLI
  - Browser integration tests (open download page)
  - Mock GitHub API responses (no network calls during tests)
  - 36 test cases covering all UpdateService functionality
- **PhotosView Test Coverage** (#157): Comprehensive unit tests for `PhotosView` in `tests/gui/test_views.py`:
  - View creation and initialization tests
  - Album tree population and selection
  - Video grid display and filtering (H.264, iCloud, favorites)
  - Multi-selection with selection count and total size
  - iCloud status display with warnings
  - Permission error handling
  - Loading indicator visibility
  - Signal emission tests (`videos_selected`)
  - 29 test cases achieving 96% code coverage
- **VideoGrid and ResultDialog Test Coverage** (#158): Unit tests for `VideoGrid` and `ConversionResultDialog`:
  - `test_video_grid.py`: `VideoItem` dataclass, `VideoThumbnail` widget, `VideoGrid` container
  - Thumbnail click/double-click signals, selection state, iCloud/favorite badges
  - Grid operations: add, clear, multi-select, selection tracking
  - `test_result_dialog.py`: Success/failure dialog states, statistics display
  - Format helpers (`_format_size`, `_format_duration`), action buttons
  - 64 test cases covering widget functionality
- **Accessibility Tests** (#161): Comprehensive accessibility tests in `tests/gui/test_accessibility.py`:
  - Keyboard navigation through all tabs (Tab key, Ctrl+1-5 shortcuts)
  - Accessible names for widgets (buttons, sliders, combo boxes, checkboxes)
  - Accessible descriptions for complex widgets (quality slider, error states)
  - Focus indicators visibility on interactive elements
  - Color contrast compliance (WCAG 2.1 relative luminance formula)
  - Comprehensive accessibility audit (focus traps, form labels, status bar)
  - 33 test cases covering accessibility requirements

## [0.2.0.0] - 2025-12-23

### Fixed
- **Session State Deadlock** (#116): Resolved deadlock in `SessionStateManager` by using `threading.RLock()` instead of `threading.Lock()`. The nested lock acquisition when `create_session()` called `save()` was causing test hangs.

### Changed
- Version scheme changed from 1.x.x to 0.x.x.x (project is in active development)
- **Coverage Configuration**: Exclude `__main__.py` (CLI entrypoint) and `applescript.py` (macOS-specific) from coverage measurement. Focus coverage on testable business logic modules.

### Added

#### Core Features
- **VMAF Quality Measurement** (#26): `VmafAnalyzer` class for perceptual video quality measurement with VMAF score calculation, `VmafScores` dataclass (min, mean, max, percentiles), `VmafQualityLevel` enum (visually lossless >= 93), frame sampling, `quick_analyze()` for fast estimation, and async support. 46 comprehensive unit tests.
- **Concurrent Processing** (#31): `ConcurrentProcessor` for parallel video processing with configurable max concurrent jobs, `ResourceMonitor` for system resource tracking, `AggregatedProgress` for combined progress, semaphore-based concurrency limiting, and thread-safe job management. 32 test cases.
- **Error Recovery** (#32): `ErrorRecoveryManager` with `ErrorCategory` and `RecoveryAction` enums, automatic error classification, disk space monitoring, `FailureRecord` tracking, manual retry API, and partial output cleanup.
- **Retry Logic** (#27): `RetryManager` with four-stage retry (same settings → switch encoder → adjust quality → final attempt), automatic encoder fallback (HW ↔ SW), CRF adjustment, `RetryConfig`, `RetryAttempt` tracking, and `RetryResult`. 35 unit tests.

#### Photos Integration
- **Photos Re-Import** (#101): `PhotosImporter` class for importing converted videos back to Photos library via AppleScript, `import_video()`, `verify_import()`, `get_video_info()` methods, configurable timeout, and comprehensive exception hierarchy (`PhotosImportError`, `PhotosNotRunningError`, `ImportTimeoutError`, `DuplicateVideoError`, `ImportFailedError`).
- **Metadata Preservation** (#103): `MetadataPreserver` class with `VideoMetadataSnapshot`, `capture_metadata()`, `embed_metadata_in_file()` via ExifTool, `apply_photos_metadata()` via AppleScript, `verify_metadata()` with `MetadataTolerance` presets, and `VerificationResult`.
- **Original Handling** (#102): `OriginalHandling` enum (DELETE, ARCHIVE, KEEP), `handle_original()` method, CLI options (`--reimport`, `--delete-originals`, `--keep-originals`, `--archive-album`, `--confirm-delete`), and AppleScript integration.
- **Permission Guidance** (#96): `--check-permissions` flag, rich panel display for permission errors, `display_photos_permission_error()`, `display_photos_permission_success()`, `display_photos_library_info()`, and quick access to System Settings.
- **Progress Display** (#97): `PhotosProgressDisplay` with library info panel, two-phase progress tracking (Export/Convert), metadata display, styled summary panel, and `_NullPhotosProgress` for quiet mode.

#### Folder Support
- **iCloud Drive Support** (#88): Automatic iCloud stub file detection (`.filename.icloud` format) in `FolderExtractor`, `_is_icloud_stub()`, `_get_original_path_from_stub()`, `in_cloud` and `stub_path` properties, `FolderConfig` with iCloud settings, and `_ensure_file_available()` in Orchestrator. 15 unit tests.
- **Folder Extractor**: `FolderExtractor` class for direct video conversion from filesystem folders, recursive scanning with include/exclude patterns, video codec detection, `FolderVideoInfo` and `FolderStats` dataclasses. 62 test cases.

#### Automation
- **Service Management** (#35): Public `load()`, `unload()`, `restart()` methods in `ServiceManager`, permission checking, CLI commands (`service-start`, `service-stop`, `service-load`, `service-unload`, `service-restart`, `service-logs`), `--follow` and `--stderr` options.
- **Status Query** (#36): `calculate_next_run()`, `get_last_run_info()`, `get_detailed_status()` methods, `LastRunInfo` and `DetailedServiceStatus` dataclasses, enhanced CLI `status` command with next run time and statistics. 26 tests.

#### UI/UX
- **Rich Progress Display** (#38): `ui/progress.py` module with `SingleFileProgressDisplay`, `BatchProgressDisplay`, `IndeterminateSpinner`, `ProgressDisplayManager`, custom Rich columns (`SizeProgressColumn`, `SpeedColumn`, `ETAColumn`), and null object pattern for quiet mode. 35 unit tests.
- **Statistics Reporter**: `StatisticsReporter` class with `StatsPeriod` enum, time-based filtering (today, week, month, all), enhanced `stats` CLI command, `stats-export` for JSON/CSV, `--detailed` and `--period` options.
- **macOS Notifications**: `NotificationManager` class with automatic batch completion notifications, success/partial/failure types, summary statistics, `NotificationConfig`, and Orchestrator integration.

#### Quality & Validation
- **Metadata Verification** (#22): `MetadataVerifier` class for comprehensive metadata comparison, `ToleranceSettings` (date: 1s, GPS: 0.000001°, duration: 0.1s), `CheckResult` and `VerificationResult` dataclasses, category-based verification, and tolerance profiles. 43 test cases.
- **Timestamp Sync** (#21): `TimestampSynchronizer` for copying timestamps, `FileTimestamps` dataclass, birth time support on macOS via SetFile, `TimestampVerificationResult`, `preserve_timestamps` config option. 23 test cases.
- **Conversion History** (#18): `ConversionHistory` class for duplicate prevention, `ConversionRecord` dataclass, `HistoryStatistics`, UUID and file hash identification, JSON persistence, export functionality. 41 test cases.

#### Other
- **iCloud Download** (#16): `iCloudHandler` for detecting and downloading iCloud videos, `CloudStatus` enum, stub file analysis, brctl download triggering, `DownloadProgress` tracking, `icloud_timeout` and `skip_cloud_only` options.
- **Real-time Progress** (#11): `ProgressInfo` dataclass with ETA calculation, `ProgressParser` for FFmpeg output, `ProgressMonitor` with throttling, `create_simple_callback` helper.
- **10-bit HDR Encoding**: `bit_depth` option for 8/10-bit, `hdr` option for HDR10 (BT.2020 PQ), libx265 10-bit support with yuv420p10le.

#### Test Infrastructure
- **Integration Tests** (#115): `test_vmaf_integration.py` (29 tests), `test_concurrent_integration.py` (24 tests), `test_error_recovery_integration.py` (34 tests), `test_icloud_folder_integration.py` (31 tests), `test_statistics_integration.py` (47 tests), `test_notification_integration.py` (49 tests).
- **Test Coverage** (#116): Verified 81.62% unit test coverage, exceeding 80% target. Added `mock_osxphotos` fixture, updated `test_config_version`, refactored `test_photos_extractor.py`.
- **Photos CLI Tests** (#98): `test_photos_handler.py`, `test_photos_permissions.py`, `test_photos_progress.py`, `test_photos_cli.py`.
- **Photos Re-Import Tests** (#104): `test_photos_metadata_preservation.py`, `test_photos_original_handling.py`, `test_photos_reimport.py`.

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

[Unreleased]: https://github.com/kcenon/video_converter/compare/v0.2.0.0...HEAD
[0.2.0.0]: https://github.com/kcenon/video_converter/compare/v0.1.0.0...v0.2.0.0
[0.1.0.0]: https://github.com/kcenon/video_converter/releases/tag/v0.1.0.0
