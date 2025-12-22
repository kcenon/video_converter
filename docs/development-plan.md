# Video Converter Development Plan

**Version**: 1.0.0
**Date**: 2025-12-21
**Status**: Planning Phase

### Related Documents

| Document | Description |
|----------|-------------|
| [PRD.md](PRD.md) | Product Requirements Document |
| [SRS.md](SRS.md) | Software Requirements Specification |
| [SDS.md](SDS.md) | Software Design Specification |
| [architecture/](architecture/) | Architecture diagrams and design |

---

## 1. Project Overview

### 1.1 Project Purpose

Develop a system that automatically converts H.264 codec videos stored in the macOS Photos library to H.265 (HEVC) to save storage space.

### 1.2 Core Values

| Item | Target |
|------|--------|
| **Storage Savings** | 50%+ file size reduction |
| **Quality Preservation** | VMAF 93+ (visually lossless) |
| **Metadata Preservation** | GPS, dates, album info 100% preserved |
| **Full Automation** | Minimize user intervention |

### 1.3 Target Users

- Individual users managing many videos on macOS
- Users primarily using Apple Photos app
- Users needing storage optimization

---

## 2. Technology Stack

### 2.1 Development Languages and Frameworks

| Component | Technology | Version Requirement |
|-----------|------------|---------------------|
| Primary Language | Python | 3.10+ |
| Photos Access | osxphotos | 0.70+ |
| Video Conversion | FFmpeg + VideoToolbox | 5.0+ |
| Metadata Processing | ExifTool | 12.0+ |
| Automation | launchd | macOS built-in |

### 2.2 System Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| macOS | 12.0 (Monterey) | 14.0+ (Sonoma) |
| CPU | Apple M1 | Apple M2 Pro or better |
| RAM | 8GB | 16GB+ |
| Storage | 2x conversion target | 3x conversion target |

### 2.3 Project Structure

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── __main__.py              # CLI entrypoint
│       ├── core/                    # Core logic
│       │   ├── orchestrator.py
│       │   ├── config.py
│       │   └── logger.py
│       ├── extractors/              # Video extraction
│       │   ├── base.py
│       │   ├── photos_extractor.py
│       │   └── folder_extractor.py
│       ├── converters/              # Conversion engines
│       │   ├── base.py
│       │   ├── hardware.py
│       │   └── software.py
│       ├── processors/              # Post-processing
│       │   ├── codec_detector.py
│       │   ├── metadata.py
│       │   └── validator.py
│       ├── automation/              # Automation
│       │   ├── launchd.py
│       │   └── folder_action.py
│       ├── reporters/               # Reporting/notifications
│       │   ├── statistics.py
│       │   └── notifier.py
│       └── utils/                   # Utilities
│           ├── file_utils.py
│           └── command_utils.py
├── config/
│   ├── default.json
│   └── launchd/
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 3. Development Phases

### Phase 1: Foundation (Week 1-2)

**Goals**: Project setup, basic infrastructure

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 1.1 | Project directory structure setup | High | 2h |
| 1.2 | pyproject.toml and dependency config | High | 2h |
| 1.3 | Logging system implementation | High | 4h |
| 1.4 | Config file load/save (config.py) | High | 4h |
| 1.5 | Command execution utility (command_utils.py) | Medium | 4h |
| 1.6 | Dependency check script | Medium | 2h |

**Deliverables**:
- [x] Project directory structure
- [x] pyproject.toml and dev environment
- [x] Config file load/save functionality
- [x] Logging system (file + console)
- [x] FFmpeg/ExifTool command executor

---

### Phase 2: Core Conversion (Week 2-3)

**Goals**: Video codec detection and conversion implementation

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 2.1 | FFprobe-based codec detection | High | 4h |
| 2.2 | VideoToolbox hardware encoding (HW) | High | 8h |
| 2.3 | libx265 software encoding (SW) | Medium | 6h |
| 2.4 | Converter Strategy pattern | High | 4h |
| 2.5 | Conversion progress monitoring | Medium | 4h |
| 2.6 | Single file conversion CLI | Medium | 3h |

**Deliverables**:
- [x] H.264/H.265 codec detection
- [x] VideoToolbox hardware encoding
- [x] libx265 software encoding
- [x] Quality preset system (Fast/Balanced/Quality)
- [x] Real-time progress display

---

### Phase 3: Photos Integration (Week 3-4)

**Goals**: macOS Photos library access and video extraction

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 3.1 | osxphotos integration | High | 6h |
| 3.2 | Video list query (filter: H.264) | High | 4h |
| 3.3 | Video export (original quality) | High | 4h |
| 3.4 | iCloud video download | Medium | 6h |
| 3.5 | Folder extractor (folder_extractor.py) ✅ | Medium | 4h |
| 3.6 | Conversion history (duplicate prevention) | Medium | 4h |

**Deliverables**:
- [x] Photos library video list query
- [x] H.264 codec video filtering only
- [x] Original video export
- [x] iCloud video download (optional)
- [x] Conversion history-based duplicate prevention

---

### Phase 4: Metadata Processing (Week 4-5)

**Goals**: GPS, dates, metadata preservation

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 4.1 | ExifTool integration | High | 4h |
| 4.2 | Metadata extraction | High | 4h |
| 4.3 | Metadata copy (tagsFromFile) | High | 4h |
| 4.4 | GPS special handling | High | 6h |
| 4.5 | File timestamp sync | Medium | 2h |
| 4.6 | Metadata verification logic | Medium | 4h |

**Deliverables**:
- [x] Original → converted file metadata copy
- [x] GPS, dates, camera info preservation
- [x] File system timestamp synchronization
- [x] Metadata preservation verification

---

### Phase 5: Quality Validation (Week 5-6)

**Goals**: Conversion result quality assurance

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 5.1 | FFprobe file integrity check | High | 4h |
| 5.2 | Property comparison (resolution, fps, duration) | High | 4h |
| 5.3 | Compression ratio normal range check | High | 3h |
| 5.4 | Audio stream verification | Medium | 2h |
| 5.5 | VMAF quality measurement (optional) | Low | 8h |
| 5.6 | Validation failure retry logic | Medium | 4h |

**Deliverables**:
- [x] Converted file integrity verification
- [x] Property match with original
- [x] Normal compression ratio range check
- [x] VMAF measurement (optional)

---

### Phase 6: Orchestration (Week 6-7)

**Goals**: Batch processing and error handling

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 6.1 | Orchestrator class implementation | High | 8h |
| 6.2 | Batch conversion workflow | High | 6h |
| 6.3 | Session management (state tracking) | High | 4h |
| 6.4 | Concurrent processing (max 2) | Medium | 4h |
| 6.5 | Failure isolation | Medium | 3h |
| 6.6 | Session state save/restore | Medium | 4h |

**Deliverables**:
- [x] Complete conversion workflow orchestration
- [x] Processing queue management
- [x] Error recovery and retry
- [x] Session state persistence

---

### Phase 7: Automation (Week 7-8)

**Goals**: launchd-based automation

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 7.1 | launchd plist generator | High | 4h |
| 7.2 | Service install/uninstall script | High | 4h |
| 7.3 | launchctl wrapper | Medium | 3h |
| 7.4 | Service status query | Medium | 2h |
| 7.5 | StartCalendarInterval schedule | Medium | 3h |
| 7.6 | Folder Action script (alternative) | Low | 4h |

**Deliverables**:
- [x] launchd service plist file
- [x] Auto install/uninstall scripts
- [x] Folder watch-based auto execution
- [x] Schedule-based daily execution

---

### Phase 8: CLI and Finalization (Week 8-9)

**Goals**: Complete CLI, notifications, documentation

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 8.1 | Complete CLI commands | High | 8h |
| 8.2 | Progress bar display | Medium | 4h |
| 8.3 | Statistics report | Medium | 4h |
| 8.4 | macOS notification | Medium | 3h |
| 8.5 | Documentation (README.md, user guide) | Medium | 4h |
| 8.6 | Final bug fixes and optimization | High | 8h |

**Deliverables**:
- [x] Complete CLI interface
- [x] Conversion statistics report
- [x] macOS notification integration
- [x] User documentation

---

## 4. Testing Strategy

### 4.1 Test Types

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit Tests | 80%+ | pytest |
| Integration Tests | Key workflows | pytest |
| E2E Tests | CLI commands | pytest + subprocess |
| Performance Tests | Benchmarks | Custom scripts |

### 4.2 Test Data Requirements

| Sample ID | Resolution | Duration | Codec | Purpose |
|-----------|------------|----------|-------|---------|
| SAMPLE-001 | 1080p | 10s | H.264 | Quick test |
| SAMPLE-002 | 4K | 1min | H.264 | Performance test |
| SAMPLE-003 | 1080p | 30s | H.264+GPS | Metadata test |
| SAMPLE-004 | 1080p | 10s | HEVC | Skip test |
| SAMPLE-005 | 4K | 30min | H.264 | Long-run test |

---

## 5. Risk Management

### 5.1 Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Photos library access issues | High | Medium | Thorough permission testing |
| iCloud sync delays | Medium | High | Retry logic, timeout handling |
| Metadata loss | High | Low | Extensive verification |
| Large file memory issues | Medium | Medium | Streaming processing |
| VideoToolbox unavailability | Medium | Low | Software fallback |

---

## 6. Milestones

| Milestone | Target Date | Success Criteria |
|-----------|-------------|------------------|
| M1: Foundation | Week 2 | Basic infrastructure working |
| M2: Core Conversion | Week 3 | Single file conversion working |
| M3: Photos Integration | Week 4 | Photos library extraction working |
| M4: Metadata | Week 5 | GPS/dates preserved 100% |
| M5: Automation | Week 7 | launchd scheduling working |
| M6: v1.0.0 Release | Week 9 | All features complete |

---

## 7. Reference Documents

**Architecture**:
- [01-system-architecture.md](architecture/01-system-architecture.md) - System Architecture
- [02-sequence-diagrams.md](architecture/02-sequence-diagrams.md) - Sequence Diagrams
- [03-data-flow-and-states.md](architecture/03-data-flow-and-states.md) - Data Flow
- [04-processing-procedures.md](architecture/04-processing-procedures.md) - Processing Procedures

**Technical References**:
- [01-codec-comparison.md](reference/01-codec-comparison.md) - Codec Comparison
- [02-ffmpeg-hevc-encoding.md](reference/02-ffmpeg-hevc-encoding.md) - FFmpeg Guide
- [03-videotoolbox-hardware-acceleration.md](reference/03-videotoolbox-hardware-acceleration.md) - Hardware Acceleration
- [04-macos-photos-access.md](reference/04-macos-photos-access.md) - Photos Access
- [05-macos-automation-methods.md](reference/05-macos-automation-methods.md) - Automation Methods

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-21 | - | Initial creation |

---

*This document is updated as development progresses.*
