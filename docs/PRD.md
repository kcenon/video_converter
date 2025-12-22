# Video Converter - Product Requirements Document (PRD)

**Document Version**: 1.1.0
**Date**: 2025-12-23
**Status**: Active
**Author**: Product Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Definition](#2-problem-definition)
3. [Product Vision and Goals](#3-product-vision-and-goals)
4. [User Personas](#4-user-personas)
5. [User Stories](#5-user-stories)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [User Flows](#8-user-flows)
9. [UI/UX Requirements](#9-uiux-requirements)
10. [Scope Definition](#10-scope-definition)
11. [Dependencies and Constraints](#11-dependencies-and-constraints)
12. [Success Metrics](#12-success-metrics)
13. [Release Plan](#13-release-plan)
14. [Appendix](#14-appendix)

---

## 1. Executive Summary

### 1.1 Product Overview

**Video Converter** is an automated video codec conversion solution for macOS users. It automatically converts H.264 codec videos stored in Apple Photos library to H.265 (HEVC), achieving **50%+ storage savings** while maintaining **visually identical quality** and **preserving all metadata (GPS, dates, album information)**.

### 1.2 Core Value Proposition

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Core Value Proposition                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   "Keep your precious memories, halve your storage"                  │
│                                                                       │
│   ✓ Automation: Set once, runs daily automatically                   │
│   ✓ Lossless: Visually indistinguishable quality                    │
│   ✓ Safe: 100% preservation of GPS, dates, all metadata             │
│   ✓ Efficient: Fast conversion with Apple Silicon hardware accel.   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Target Market

- **Primary**: Individual users using Apple Photos on macOS
- **Secondary**: Prosumers/creators managing large video archives

---

## 2. Problem Definition

### 2.1 User Pain Points

#### Pain Point 1: Rapidly Growing Video Storage

> "My 4K videos from iPhone are piling up and even 512GB iCloud isn't enough anymore. The monthly iCloud fees are becoming a burden."

**Current State**:
- Smartphone camera improvements → 4K 60fps recording commonplace
- 1 minute 4K video = ~400MB (H.264)
- Average user: 50-100 videos/month → 20-40GB/month increase

**Result**:
- iCloud/local storage shortage
- Additional storage purchase costs
- Pressure to delete precious videos

#### Pain Point 2: Manual Conversion Hassle

> "Converting one by one with HandBrake takes too much time, and the settings are too complicated."

**Current State**:
- Existing conversion tools: Manual work required per file
- Complex encoding settings to understand
- Risk of metadata loss

**Result**:
- Abandoning conversion efforts
- Continued inefficient storage usage

#### Pain Point 3: Metadata Loss Concerns

> "I'm worried that GPS info and recording dates will disappear after conversion. These are my travel memories..."

**Current State**:
- Most conversion tools: Partial metadata loss
- GPS coordinates: Particularly high risk of loss
- Photos app sorting/search functionality disabled

**Result**:
- Location-based search unavailable after conversion
- Chronological sorting broken
- Context of memories lost

### 2.2 Opportunity Analysis

| Factor | Current State | Opportunity |
|--------|---------------|-------------|
| H.265 Codec Maturity | All Apple devices support (2017+) | Transition possible without compatibility issues |
| Apple Silicon Adoption | M1+ Macs majority | Fast conversion with hardware acceleration |
| Automation Infrastructure | macOS launchd built-in | Background execution without separate app |
| Open Source Tools | FFmpeg, osxphotos mature | Stable technical foundation secured |

---

## 3. Product Vision and Goals

### 3.1 Product Vision

> **"Enable all macOS users to preserve memories without worrying about storage space"**

### 3.2 Product Goals

#### Short-term Goals (v1.0)

| # | Goal | Metric |
|---|------|--------|
| G1 | Provide automated batch conversion | 0 user interventions after setup |
| G2 | 50%+ storage savings | Average compression ratio 50%+ |
| G3 | 100% metadata preservation | GPS, date preservation rate 100% |
| G4 | Visually lossless quality | VMAF 93+ |

#### Mid-term Goals (v1.x)

| # | Goal | Metric |
|---|------|--------|
| G5 | Intuitive GUI | NPS 50+ |
| G6 | iCloud integration support | Cloud video conversion possible |
| G7 | Smart scheduling | Auto-scheduling based on system resources |

#### Long-term Goals (v2.0+)

| # | Goal | Metric |
|---|------|--------|
| G8 | In-place Photos app replacement | Original replacement feature |
| G9 | AV1 codec support | M3+ hardware acceleration |
| G10 | Cross-platform | iOS/iPadOS support |

---

## 4. User Personas

### 4.1 Primary Persona: "Family Recorder" Minsu

```
┌─────────────────────────────────────────────────────────────────────┐
│  👤 Minsu (38, Office Worker)                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📱 Devices: iPhone 15 Pro, MacBook Air M2, 200GB iCloud            │
│  📸 Activity: Records family videos on weekends, 30-50 4K videos/mo │
│  💾 Current: iCloud 90% used, monthly storage shortage warnings      │
│                                                                       │
│  🎯 Goals:                                                           │
│  • Want to keep all family videos                                    │
│  • Want to avoid additional iCloud costs                             │
│  • Want automatic processing without complex settings                │
│                                                                       │
│  😤 Frustrations:                                                    │
│  • "I keep getting notifications to delete videos"                   │
│  • "HandBrake settings are too complicated"                          │
│  • "Location info disappears after conversion"                       │
│                                                                       │
│  ✅ Success Criteria:                                                │
│  • Set once, runs daily automatically                                │
│  • Keep iCloud usage under 50%                                       │
│  • Maintain map view for travel videos                               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Secondary Persona: "Video Archiver" Jiyeon

```
┌─────────────────────────────────────────────────────────────────────┐
│  👤 Jiyeon (29, YouTube Creator)                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📱 Devices: iPhone 15 Pro Max, Mac Studio M2 Ultra, 4TB SSD        │
│  📸 Activity: Produces 3-4 videos/week, must keep originals         │
│  💾 Current: 200-300GB new videos/month, 2-3TB increase/year        │
│                                                                       │
│  🎯 Goals:                                                           │
│  • Save storage while maintaining maximum original quality           │
│  • Batch process large numbers of videos                             │
│  • Fast conversion with hardware acceleration                        │
│                                                                       │
│  😤 Frustrations:                                                    │
│  • "Software encoding is too slow"                                   │
│  • "Batch job management is difficult"                               │
│  • "I'm worried about quality loss"                                  │
│                                                                       │
│  ✅ Success Criteria:                                                │
│  • Convert 4K 1-hour video in under 10 minutes                       │
│  • Guaranteed VMAF 95+ quality                                       │
│  • Overnight automatic batch processing                              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Tertiary Persona: "Tech Enthusiast" Sungho

```
┌─────────────────────────────────────────────────────────────────────┐
│  👤 Sungho (45, Developer)                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📱 Devices: Various Macs, runs NAS                                  │
│  📸 Activity: Tech testing, prefers script automation               │
│  💾 Current: Prefers command-line tools, wants fine control         │
│                                                                       │
│  🎯 Goals:                                                           │
│  • Complete control via CLI                                          │
│  • Integration with other scripts                                    │
│  • Open source for customization                                     │
│                                                                       │
│  ✅ Success Criteria:                                                │
│  • Rich CLI options                                                  │
│  • JSON/YAML config file support                                     │
│  • Pipeline integration possible                                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. User Stories

### 5.1 Epic 1: Initial Setup

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-101 | As a user, I want to install all dependencies with a single install script | Must | Complete installation in 5 minutes |
| US-102 | As a user, I want to complete basic setup with a setup wizard | Should | 3 steps or fewer |
| US-103 | As a user, I want to easily grant Photos app access permission | Must | Auto-navigate to system settings |
| US-104 | As a user, I want to select quality/speed presets | Should | 3 presets provided |

### 5.2 Epic 2: Video Conversion

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-201 | As a user, I want to automatically find H.264 videos in Photos library | Must | No manual selection needed |
| US-202 | As a user, I want to convert only selected videos | Should | Album/date filter support |
| US-203 | As a user, I want to see real-time conversion progress | Should | Progress % display |
| US-204 | As a user, I want Mac to remain responsive during conversion | Must | CPU 30% or less (HW mode) |
| US-205 | As a user, I want already converted videos to be skipped | Must | Duplicate conversion prevention |

### 5.3 Epic 3: Metadata Preservation

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-301 | As a user, I want recording dates preserved after conversion | Must | 100% date preservation |
| US-302 | As a user, I want GPS location info preserved after conversion | Must | 100% GPS preservation |
| US-303 | As a user, I want album info preserved after conversion | Should | Album mapping maintained |
| US-304 | As a user, I want file creation date in Finder to match original | Should | Timestamp synchronization |

### 5.4 Epic 4: Automation

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-401 | As a user, I want auto conversion to run at a specific time daily | Must | Schedule configurable |
| US-402 | As a user, I want new videos to be auto-converted when added | Should | Folder watch feature |
| US-403 | As a user, I want to receive notification on conversion completion | Should | macOS notification support |
| US-404 | As a user, I want conversion delayed when Mac is in use | Could | Idle time detection |

### 5.5 Epic 5: Safety and Recovery

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-501 | As a user, I don't want original files deleted immediately | Must | Move to processed folder |
| US-502 | As a user, I want originals preserved on conversion failure | Must | Original retained on failure |
| US-503 | As a user, I want to verify quality of converted files | Should | Verification report provided |
| US-504 | As a user, I want to restore from original if problems occur | Should | Recovery feature provided |

### 5.6 Epic 6: Monitoring and Reporting

| ID | User Story | Priority | Acceptance Criteria |
|----|------------|----------|---------------------|
| US-601 | As a user, I want to see total storage saved | Should | Statistics dashboard |
| US-602 | As a user, I want to view conversion history | Should | Log viewing feature |
| US-603 | As a user, I want to see list of failed conversions | Must | Failed list displayed |
| US-604 | As a user, I want to see next scheduled conversion | Could | Schedule display |

---

## 6. Functional Requirements

### 6.1 Functional Requirements Matrix

| ID | Feature | Description | Priority | Release |
|----|---------|-------------|----------|---------|
| **Core Features** |
| FR-001 | H.264 Detection | Automatic video codec detection | P0 | v1.0 |
| FR-002 | H.265 Conversion | VideoToolbox hardware accelerated conversion | P0 | v1.0 |
| FR-003 | Software Conversion | libx265 high-quality conversion option | P1 | v1.0 |
| FR-004 | Progress Display | Real-time conversion progress | P1 | v1.0 |
| **Photos Integration** |
| FR-101 | Photos Scan | Library scan with osxphotos | P0 | v1.0 |
| FR-102 | Video Filtering | Filter H.264 videos only | P0 | v1.0 |
| FR-103 | Video Export | Extract original video to temp | P0 | v1.0 |
| FR-104 | iCloud Download | Download cloud videos | P1 | v1.0 |
| FR-105 | Album Filter | Process specific albums only | P2 | v1.1 |
| **Metadata** |
| FR-201 | Metadata Extraction | Full metadata extraction with ExifTool | P0 | v1.0 |
| FR-202 | Metadata Application | Restore metadata to converted file | P0 | v1.0 |
| FR-203 | GPS Preservation | Special handling for GPS coordinates | P0 | v1.0 |
| FR-204 | Timestamp Sync | File system time synchronization | P1 | v1.0 |
| **Quality Management** |
| FR-301 | Integrity Check | File verification with FFprobe | P0 | v1.0 |
| FR-302 | Property Comparison | Resolution/framerate/duration comparison | P0 | v1.0 |
| FR-303 | Compression Check | Abnormal compression ratio warning | P1 | v1.0 |
| FR-304 | VMAF Measurement | Quality score calculation (optional) | P2 | v1.1 |
| **Automation** |
| FR-401 | Scheduled Execution | launchd StartCalendarInterval | P0 | v1.0 |
| FR-402 | Folder Watch | launchd WatchPaths | P1 | v1.0 |
| FR-403 | Notification | macOS Notification Center | P1 | v1.0 |
| FR-404 | Service Management | launchctl wrapper | P1 | v1.0 |
| **CLI** |
| FR-501 | Single Conversion | `convert <input> <output>` | P0 | v1.0 |
| FR-502 | Batch Conversion | `run --mode photos` | P0 | v1.0 |
| FR-503 | Status Query | `status` | P1 | v1.0 |
| FR-504 | Stats Query | `stats` | P2 | v1.0 |
| FR-505 | Service Install | `install-service` | P0 | v1.0 |
| **Safety** |
| FR-601 | Original Preservation | Move to processed folder | P0 | v1.0 |
| FR-602 | Retry Logic | 3 retries on failure | P0 | v1.0 |
| FR-603 | Failure Isolation | Failed files to separate folder | P0 | v1.0 |
| FR-604 | Checkpoint | Session state save/restore | P2 | v1.1 |

### 6.2 Feature Detailed Specifications

#### FR-002: H.265 Conversion (VideoToolbox)

**Description**: Hardware accelerated H.265 encoding using Apple Silicon's VideoToolbox

**Input**:
- H.264 codec video file (.mp4, .mov, .m4v)
- Quality setting (1-100, default 45)

**Processing**:
```bash
ffmpeg -i <input> \
  -c:v hevc_videotoolbox \
  -q:v <quality> \
  -tag:v hvc1 \
  -c:a copy \
  -map_metadata 0 \
  -movflags use_metadata_tags \
  <output>
```

**Output**:
- H.265/HEVC codec video file
- QuickTime compatible tag (hvc1)

**Success Criteria**:
- Conversion success rate 99%+
- Average compression ratio 50%+
- Conversion speed: 20x+ realtime (4K)

#### FR-203: GPS Preservation

**Description**: Perfect preservation of GPS coordinate information during conversion

**Input**:
- Original video GPS metadata
  - QuickTime:GPSCoordinates
  - Keys:GPSCoordinates
  - XMP:GPSLatitude/Longitude

**Processing**:
1. Basic copy with FFmpeg `-map_metadata 0`
2. Detailed copy with ExifTool `-tagsFromFile`
3. Explicit GPS tag copy (`-GPS*`)
4. Post-copy verification

**Output**:
- Same GPS coordinates on converted video

**Success Criteria**:
- GPS preservation rate 100%
- Accuracy maintained to 6 decimal places

---

## 7. Non-Functional Requirements

### 7.1 Performance Requirements

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-P01 | 4K 30min video conversion time (HW) | Under 5 minutes | Benchmark test |
| NFR-P02 | 1080p 10min video conversion time (HW) | Under 30 seconds | Benchmark test |
| NFR-P03 | CPU usage (HW mode) | 30% or less | Activity Monitor |
| NFR-P04 | Memory usage | 1GB or less | Activity Monitor |
| NFR-P05 | Concurrent conversion support | 2 | Configurable |

### 7.2 Reliability Requirements

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-R01 | Conversion success rate | 99%+ | Batch test |
| NFR-R02 | Metadata preservation rate | 100% | Auto verification |
| NFR-R03 | Service uptime (automation) | 99.9% | Log analysis |
| NFR-R04 | Error recovery success rate | 95%+ | Retry logs |

### 7.3 Usability Requirements

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-U01 | Initial setup time | Under 5 minutes | User testing |
| NFR-U02 | CLI learning time | Under 10 minutes | User testing |
| NFR-U03 | Error message clarity | 90% comprehension | User feedback |

### 7.4 Compatibility Requirements

| ID | Requirement | Target | Notes |
|----|-------------|--------|-------|
| NFR-C01 | macOS version | 12.0+ (Monterey) | Apple Silicon required |
| NFR-C02 | Python version | 3.10+ | osxphotos requirement |
| NFR-C03 | FFmpeg version | 5.0+ | hevc_videotoolbox support |
| NFR-C04 | Video formats | .mp4, .mov, .m4v | H.264 codec |

### 7.5 Security Requirements

| ID | Requirement | Target | Implementation |
|----|-------------|--------|----------------|
| NFR-S01 | Photos access permission | Minimum privilege | Read-only |
| NFR-S02 | Temp file security | Delete after use | Auto cleanup |
| NFR-S03 | Config file security | Store in user home | 0600 permission |

---

## 8. User Flows

### 8.1 Initial Setup Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Initial Setup Flow                           │
└─────────────────────────────────────────────────────────────────────┘

[Start]
   │
   ▼
┌─────────────────┐
│ 1. Run install  │ ──▶ brew install, pip install
│    script       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Dependency   │ ──▶ ffmpeg, exiftool, osxphotos
│    check (auto) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 3. Photos       │ ──▶ │ Auto-navigate   │
│    permission   │     │ to System Prefs │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│ 4. Quality      │ ──▶ Fast(HW) / Balanced(HW) / High Quality(SW)
│    preset       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Schedule     │ ──▶ Daily 3 AM (default)
│    setup        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. Service      │ ──▶ launchctl load
│    registration │
└────────┬────────┘
         │
         ▼
[Complete - Waiting for auto execution]
```

### 8.2 Auto Conversion Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Auto Conversion Flow                           │
└─────────────────────────────────────────────────────────────────────┘

[Schedule Trigger - 3 AM]
   │
   ▼
┌─────────────────┐
│ 1. Photos Scan  │ ──▶ Query video list with osxphotos
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. H.264 Filter │ ──▶ Exclude already HEVC videos
│                 │      Exclude already converted
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 3. No targets?  │──Y──▶│ Log and exit   │
│                 │     │                 │
└────────┬────────┘     └─────────────────┘
         │N
         ▼
┌─────────────────┐
│ 4. Per-video    │
│ loop            │
│ ┌─────────────┐ │
│ │ 4a. Export  │ │ ──▶ Extract to temp directory
│ └──────┬──────┘ │
│        ▼        │
│ ┌─────────────┐ │
│ │ 4b. Convert │ │ ──▶ FFmpeg hevc_videotoolbox
│ └──────┬──────┘ │
│        ▼        │
│ ┌─────────────┐ │
│ │ 4c. Verify  │ │ ──▶ Integrity, property comparison
│ └──────┬──────┘ │
│        ▼        │
│ ┌─────────────┐ │
│ │ 4d. Meta-   │ │ ──▶ ExifTool metadata restore
│ │     data    │ │
│ └──────┬──────┘ │
│        ▼        │
│ ┌─────────────┐ │
│ │ 4e. Cleanup │ │ ──▶ Original → processed folder
│ └─────────────┘ │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Generate     │ ──▶ Success/failure/space saved
│    report       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. Send         │ ──▶ macOS Notification Center
│    notification │
└────────┬────────┘
         │
         ▼
[End]
```

### 8.3 Manual Conversion Flow (CLI)

```
[User command input]
   │
   ▼
$ video-converter convert input.mp4 output.mp4 --mode hardware --quality 45
   │
   ▼
┌─────────────────┐
│ 1. Input        │ ──▶ File exists, codec check
│    validation   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Execute      │ ──▶ Progress bar display
│    conversion   │     [████████░░░░░░░░] 50% (2:30 remaining)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Post-        │ ──▶ Metadata, timestamps
│    processing   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Output       │ ──▶ ✅ Complete: 1.5GB → 680MB (54% saved)
│    result       │
└─────────────────┘
```

---

## 9. UI/UX Requirements

### 9.1 CLI Interface

#### Command Structure

```bash
video-converter <command> [options]

Commands:
  convert     Single file conversion
  run         Batch conversion execution
  status      Service status check
  stats       Conversion statistics query
  config      Configuration management
  install     Service installation
  uninstall   Service removal

Global Options:
  --config    Config file path
  --verbose   Detailed log output
  --quiet     Minimal output
  --help      Show help
```

#### Output Format

**Progress Display**:
```
Converting: vacation_2024.mp4
[████████████░░░░░░░░] 60% | 1.2GB → 540MB | ETA: 1:45
```

**Completion Summary**:
```
╭─────────────────────────────────────────────╮
│           Conversion Report                  │
├─────────────────────────────────────────────┤
│  Videos processed:  15                       │
│  Success:           14                       │
│  Failed:            1                        │
│  Skipped:           3 (already HEVC)         │
├─────────────────────────────────────────────┤
│  Original size:     35.2 GB                  │
│  Converted size:    15.8 GB                  │
│  Space saved:       19.4 GB (55%)            │
├─────────────────────────────────────────────┤
│  Total time:        45 min 32 sec            │
│  Average speed:     3.2x realtime            │
╰─────────────────────────────────────────────╯
```

**Error Display**:
```
❌ Error: vacation_corrupted.mp4
   Cause: Invalid data found when processing input
   Solution: File is corrupted. Check original.
   Location: ~/Videos/Failed/vacation_corrupted.mp4
```

### 9.2 macOS Notifications

**Success Notification**:
```
┌─────────────────────────────────┐
│ 🎬 Video Converter              │
│                                 │
│ Conversion Complete             │
│ 14 videos, 19.4GB saved         │
│                                 │
│ [Details]       [Close]         │
└─────────────────────────────────┘
```

**Error Notification**:
```
┌─────────────────────────────────┐
│ ⚠️ Video Converter              │
│                                 │
│ Conversion Failed               │
│ Error during 1 video conversion │
│                                 │
│ [View Log]      [Close]         │
└─────────────────────────────────┘
```

### 9.3 Configuration File Format

```json
{
  "version": "0.1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "crf": 22,
    "preset": "slow"
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "enabled": true,
    "schedule": "daily",
    "time": "03:00"
  },
  "photos": {
    "include_albums": [],
    "exclude_albums": ["Screenshots"],
    "download_from_icloud": true
  },
  "processing": {
    "max_concurrent": 2,
    "validate_quality": true,
    "preserve_original": true
  },
  "notification": {
    "on_complete": true,
    "on_error": true,
    "daily_summary": false
  }
}
```

---

## 10. Scope Definition

### 10.1 In Scope

#### v1.0 Scope

| Category | Included Items |
|----------|---------------|
| **Platform** | macOS 12.0+ (Apple Silicon) |
| **Source** | Apple Photos library, local folders |
| **Codec** | H.264 → H.265 conversion |
| **Encoder** | VideoToolbox (HW), libx265 (SW) |
| **Automation** | launchd schedule/folder watch |
| **Interface** | CLI |
| **Metadata** | GPS, dates, camera info |
| **Notification** | macOS Notification Center |

### 10.2 Out of Scope

#### Excluded from v1.0

| Item | Reason | Future Plan |
|------|--------|-------------|
| GUI app | Development complexity | v2.0 consideration |
| In-place Photos replacement | API limitations | Research needed |
| Windows/Linux | Platform-specific | TBD |
| iOS/iPadOS | Platform-specific | v3.0 consideration |
| AV1 codec | M3+ only | v1.x consideration |
| Real-time streaming | Different use case | Excluded |
| Video editing | Different use case | Excluded |
| Cloud storage | Complexity | v2.0 consideration |

### 10.3 Assumptions and Dependencies

**Assumptions**:
- User uses macOS Photos app as primary video management tool
- Has Apple Silicon Mac (hardware acceleration required)
- Homebrew installable environment
- Basic terminal usage ability

**Dependencies**:
- FFmpeg: Core video conversion engine
- osxphotos: Photos library access
- ExifTool: Metadata processing
- launchd: macOS automation infrastructure

---

## 11. Dependencies and Constraints

### 11.1 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Cannot directly modify Photos library | Converted files stored separately | Clearly guide output folder |
| VideoToolbox quality limitations | Slightly larger files than SW | Provide quality presets |
| iCloud sync delays | Some videos not processable | Retry logic, wait option |
| Large file memory usage | System load on some systems | Streaming processing |

### 11.2 Operational Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Power required (laptop) | Battery drain | Check power state |
| 2x storage needed | Space shortage during conversion | Pre-check space |
| Mac must be on for overnight | Schedule may be missed | Process on next run |

---

## 12. Success Metrics

### 12.1 Key Performance Indicators (KPIs)

| Metric | Target | Measurement Frequency | Data Source |
|--------|--------|----------------------|-------------|
| **Conversion success rate** | 99%+ | Per batch | Execution logs |
| **Average compression ratio** | 50%+ | Per batch | Conversion results |
| **Metadata preservation rate** | 100% | Per file | Auto verification |
| **VMAF quality score** | 93+ | Sampling | VMAF measurement |
| **User setup time** | Under 5 min | Onboarding | User feedback |

### 12.2 Business Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Storage saved per user | 50GB+/month | Statistics aggregation |
| Daily active usage rate | 80%+ | Service logs |
| Error rate | Under 1% | Error logs |
| User satisfaction (NPS) | 50+ | Survey |

### 12.3 Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Bug rate | Critical 0, Major ≤2/month | Issue tracking |
| Test coverage | 80%+ | pytest-cov |
| Code quality score | Grade A | CodeClimate |

---

## 13. Release Plan

### 13.1 Release Roadmap

> **Note**: This project uses 0.x.x.x versioning to indicate active development status.
> Version 1.0.0.0 will be assigned when the project reaches production-ready stability.

```
2025 Q4 (Completed)
└── v0.1.0.0 (Initial Release) - 2025-12-22 ✅
    └── Core conversion, Photos integration, automation, CLI

2026 Q1 (In Progress)
└── v0.2.0.0 (Feature Release) - In Development
    ├── VMAF quality verification
    ├── macOS Notification Center integration
    ├── Statistics and reporting
    ├── Concurrent processing support
    ├── Rich progress display
    └── Error recovery and retry logic

2026 Q2
└── v0.3.0.0
    └── GUI application (basic)

2026 Q3+
└── v0.4.0.0
    └── AV1 codec support, advanced features
```

### 13.2 Feature Mapping by Version

| Version | Major Features | Target Users | Status |
|---------|---------------|--------------|--------|
| **v0.1.0.0** | Core conversion, Photos integration, launchd automation, CLI | General users | ✅ Released |
| **v0.2.0.0** | VMAF verification, notifications, statistics, concurrent processing, error recovery | General users | 🔄 In Development |
| **v0.3.0.0** | Basic GUI application | General users | 📅 Planned |
| **v0.4.0.0** | AV1 codec support, advanced features | All users | 📅 Planned |

### 13.3 Release Checklist

**Pre-Release**:
- [ ] All P0 features implemented
- [ ] Unit test 80%+ coverage
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Security review complete

**Release**:
- [ ] CHANGELOG updated
- [ ] Version tag created
- [ ] PyPI deployment
- [ ] GitHub Release created
- [ ] Documentation updated

**Post-Release**:
- [ ] User feedback collection
- [ ] Bug monitoring
- [ ] Performance metrics verification

---

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| H.264 | AVC (Advanced Video Coding), video codec standardized in 2003 |
| H.265 | HEVC (High Efficiency Video Coding), standardized 2013, 50% efficiency improvement over H.264 |
| VideoToolbox | Apple's hardware video encoding/decoding framework |
| CRF | Constant Rate Factor, quality-based encoding setting (lower = higher quality) |
| VMAF | Video Multimethod Assessment Fusion, quality metric developed by Netflix (0-100) |
| launchd | macOS service management framework |
| osxphotos | Python-based Photos library access tool |

### 14.2 Reference Documents

**Design Documents**:
- [Software Requirements Specification (SRS)](SRS.md)
- **[Software Design Specification (SDS)](SDS.md)** - Technical design implementation of this PRD
- [Development Plan](development-plan.md)

**Architecture Documents**:
- [System Architecture](architecture/01-system-architecture.md)
- [Sequence Diagrams](architecture/02-sequence-diagrams.md)
- [Data Flow](architecture/03-data-flow-and-states.md)
- [Processing Procedures](architecture/04-processing-procedures.md)

**Reference Materials**:
- [Codec Comparison](reference/01-codec-comparison.md)
- [FFmpeg Guide](reference/02-ffmpeg-hevc-encoding.md)
- [VideoToolbox Guide](reference/03-videotoolbox-hardware-acceleration.md)
- [Photos Access Methods](reference/04-macos-photos-access.md)
- [Automation Methods](reference/05-macos-automation-methods.md)

### 14.3 Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-21 | - | Initial creation |
| 1.1.0 | 2025-12-23 | - | Updated release roadmap to reflect v1.0.0 release and v1.1.0 development status |

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Tech Lead | | | |
| Design Lead | | | |

---

*This document is updated as the project progresses.*
