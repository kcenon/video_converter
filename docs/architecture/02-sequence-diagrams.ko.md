# 시퀀스 다이어그램

## 1. 메인 변환 워크플로우

### 1.1 전체 배치 변환 프로세스

```mermaid
sequenceDiagram
    autonumber
    participant LAUNCHD as launchd
    participant ORCH as Orchestrator
    participant CONFIG as ConfigManager
    participant EXTRACT as PhotosExtractor
    participant DETECT as CodecDetector
    participant CONV as VideoConverter
    participant META as MetadataManager
    participant VALID as QualityValidator
    participant FS as FileSystem
    participant NOTIF as Notifier

    LAUNCHD->>ORCH: trigger (scheduled/watch)
    activate ORCH

    ORCH->>CONFIG: load_config()
    CONFIG-->>ORCH: config

    ORCH->>EXTRACT: extract_videos(filter="h264")
    activate EXTRACT
    EXTRACT->>EXTRACT: connect to Photos DB
    EXTRACT->>EXTRACT: query all movies
    loop For each video
        EXTRACT->>DETECT: is_h264(video_path)
        DETECT-->>EXTRACT: bool
    end
    EXTRACT-->>ORCH: List[VideoInfo]
    deactivate EXTRACT

    Note over ORCH: Filter already converted

    loop For each video to convert
        ORCH->>ORCH: update_status(IN_PROGRESS)

        ORCH->>EXTRACT: export_video(video, temp_dir)
        EXTRACT-->>ORCH: exported_path

        ORCH->>CONV: convert(input, output)
        activate CONV

        CONV->>CONV: build_ffmpeg_command()
        CONV->>CONV: execute_ffmpeg()

        alt Conversion Success
            CONV->>META: extract_metadata(input)
            META-->>CONV: metadata

            CONV->>META: apply_metadata(output, metadata)
            META-->>CONV: success

            CONV->>VALID: validate(input, output)
            activate VALID
            VALID->>VALID: check_file_integrity()
            VALID->>VALID: calculate_vmaf() [optional]
            VALID-->>CONV: ValidationResult
            deactivate VALID

            CONV-->>ORCH: ConversionResult(success=true)
        else Conversion Failed
            CONV-->>ORCH: ConversionResult(success=false, error)
        end
        deactivate CONV

        alt Success
            ORCH->>FS: move_to_processed(original)
            ORCH->>ORCH: update_statistics()
        else Failed
            ORCH->>FS: move_to_failed(original)
            ORCH->>NOTIF: notify_error(video, error)
        end
    end

    ORCH->>ORCH: generate_report()
    ORCH->>NOTIF: notify_completion(stats)
    NOTIF-->>ORCH: sent

    ORCH-->>LAUNCHD: completed
    deactivate ORCH
```

### 1.2 단일 비디오 변환 상세

```mermaid
sequenceDiagram
    autonumber
    participant CLI as CLI/Orchestrator
    participant CONV as VideoConverter
    participant FFMPEG as FFmpeg Process
    participant VT as VideoToolbox
    participant META as MetadataManager
    participant EXIF as ExifTool

    CLI->>CONV: convert(input.mp4, output.mp4)
    activate CONV

    Note over CONV: 1. 인코딩 명령 구성
    CONV->>CONV: validate_input_file()
    CONV->>CONV: create_output_directory()
    CONV->>CONV: build_command()

    Note over CONV: 2. FFmpeg 실행
    CONV->>FFMPEG: spawn_process(command)
    activate FFMPEG

    FFMPEG->>VT: initialize_encoder(hevc_videotoolbox)
    VT-->>FFMPEG: encoder_session

    loop For each frame
        FFMPEG->>FFMPEG: decode_h264_frame()
        FFMPEG->>VT: encode_hevc_frame(frame)
        VT-->>FFMPEG: encoded_data
        FFMPEG->>FFMPEG: write_to_output()

        FFMPEG-->>CONV: progress_update
        CONV-->>CLI: progress_callback(progress%)
    end

    FFMPEG->>FFMPEG: finalize_output()
    FFMPEG-->>CONV: exit_code=0
    deactivate FFMPEG

    Note over CONV: 3. 메타데이터 복원
    CONV->>META: restore_metadata(input, output)
    activate META

    META->>EXIF: extract_all_tags(input)
    activate EXIF
    EXIF-->>META: tags_dict
    deactivate EXIF

    META->>EXIF: write_tags(output, tags_dict)
    activate EXIF
    EXIF-->>META: success
    deactivate EXIF

    META->>META: sync_file_timestamps(input, output)
    META-->>CONV: metadata_restored
    deactivate META

    Note over CONV: 4. 결과 생성
    CONV->>CONV: calculate_compression_ratio()
    CONV->>CONV: create_result()
    CONV-->>CLI: ConversionResult

    deactivate CONV
```

## 2. Photos 라이브러리 접근

### 2.1 osxphotos를 통한 비디오 추출

```mermaid
sequenceDiagram
    autonumber
    participant EXTRACT as PhotosExtractor
    participant OSXP as osxphotos Library
    participant PHOTOSDB as Photos SQLite DB
    participant ICLOUD as iCloud Service
    participant FS as File System

    EXTRACT->>OSXP: PhotosDB()
    activate OSXP

    OSXP->>PHOTOSDB: connect(~/Pictures/Photos Library)
    PHOTOSDB-->>OSXP: connection

    OSXP->>PHOTOSDB: query assets
    PHOTOSDB-->>OSXP: asset_list

    OSXP-->>EXTRACT: photosdb instance
    deactivate OSXP

    EXTRACT->>OSXP: photos(movies=True)
    activate OSXP
    OSXP-->>EXTRACT: List[PhotoInfo]
    deactivate OSXP

    loop For each video
        EXTRACT->>EXTRACT: check if H.264

        alt Video in iCloud only
            EXTRACT->>OSXP: export(video, download=True)
            activate OSXP
            OSXP->>ICLOUD: download_asset(uuid)
            ICLOUD-->>OSXP: downloaded_data
            OSXP->>FS: write_file(path)
            FS-->>OSXP: written
            OSXP-->>EXTRACT: exported_path
            deactivate OSXP
        else Video available locally
            EXTRACT->>OSXP: export(video)
            activate OSXP
            OSXP->>FS: copy_file(original, dest)
            FS-->>OSXP: copied
            OSXP-->>EXTRACT: exported_path
            deactivate OSXP
        end

        EXTRACT->>EXTRACT: collect_metadata(video)
    end

    EXTRACT-->>EXTRACT: List[ExportedVideo]
```

### 2.2 PhotoKit을 통한 비디오 접근 (Swift)

```mermaid
sequenceDiagram
    autonumber
    participant APP as Swift App
    participant PHLIB as PHPhotoLibrary
    participant AUTH as Authorization
    participant FETCH as PHFetchResult
    participant IMGMGR as PHImageManager
    participant EXPORT as AVAssetExportSession

    APP->>PHLIB: requestAuthorization(.readWrite)
    activate PHLIB
    PHLIB->>AUTH: show permission dialog
    AUTH-->>PHLIB: authorized
    PHLIB-->>APP: PHAuthorizationStatus
    deactivate PHLIB

    APP->>FETCH: PHAsset.fetchAssets(with: .video)
    activate FETCH
    FETCH-->>APP: PHFetchResult<PHAsset>
    deactivate FETCH

    loop For each PHAsset
        APP->>IMGMGR: requestAVAsset(forVideo: asset)
        activate IMGMGR

        alt Asset in iCloud
            Note over IMGMGR: Download from iCloud
            IMGMGR->>IMGMGR: download asset
        end

        IMGMGR-->>APP: AVAsset
        deactivate IMGMGR

        APP->>EXPORT: requestExportSession(forVideo:)
        activate EXPORT
        EXPORT->>EXPORT: configure outputURL
        EXPORT->>EXPORT: configure outputFileType
        EXPORT->>EXPORT: exportAsynchronously()
        EXPORT-->>APP: AVAssetExportSession.Status
        deactivate EXPORT
    end
```

## 3. 자동화 트리거

### 3.1 launchd WatchPaths 트리거

```mermaid
sequenceDiagram
    autonumber
    participant USER as User
    participant FINDER as Finder
    participant LAUNCHD as launchd Daemon
    participant PLIST as LaunchAgent plist
    participant SCRIPT as Convert Script
    participant ORCH as Orchestrator

    Note over PLIST: com.user.videoconverter.plist<br/>WatchPaths: ~/Videos/ToConvert

    USER->>FINDER: Drop video file
    FINDER->>FINDER: Write file to watched folder

    LAUNCHD->>LAUNCHD: detect filesystem change
    LAUNCHD->>PLIST: read configuration
    PLIST-->>LAUNCHD: ProgramArguments

    LAUNCHD->>SCRIPT: execute script
    activate SCRIPT

    SCRIPT->>ORCH: initialize()
    ORCH-->>SCRIPT: ready

    SCRIPT->>ORCH: process_folder(~/Videos/ToConvert)
    activate ORCH

    ORCH->>ORCH: scan for new videos
    ORCH->>ORCH: filter H.264 only
    ORCH->>ORCH: convert each video
    ORCH->>ORCH: move to output folder

    ORCH-->>SCRIPT: completed
    deactivate ORCH

    SCRIPT-->>LAUNCHD: exit 0
    deactivate SCRIPT

    Note over LAUNCHD: ThrottleInterval: 30s<br/>Wait before next trigger
```

### 3.2 스케줄 기반 실행 (StartCalendarInterval)

```mermaid
sequenceDiagram
    autonumber
    participant CLOCK as System Clock
    participant LAUNCHD as launchd
    participant SCRIPT as Convert Script
    participant PHOTOS as Photos Extractor
    participant CONV as Converter
    participant NOTIF as Notification Center

    Note over LAUNCHD: StartCalendarInterval:<br/>Hour: 3, Minute: 0

    CLOCK->>LAUNCHD: 03:00:00 reached
    LAUNCHD->>LAUNCHD: check schedule match

    LAUNCHD->>SCRIPT: execute batch conversion
    activate SCRIPT

    SCRIPT->>PHOTOS: extract_new_videos()
    activate PHOTOS
    PHOTOS->>PHOTOS: query since last run
    PHOTOS-->>SCRIPT: List[Video]
    deactivate PHOTOS

    alt No new videos
        SCRIPT->>SCRIPT: log "No new videos"
        SCRIPT-->>LAUNCHD: exit 0
    else Has new videos
        loop For each video
            SCRIPT->>CONV: convert(video)
            CONV-->>SCRIPT: result
        end

        SCRIPT->>SCRIPT: generate_summary()
        SCRIPT->>NOTIF: display notification
        Note over NOTIF: "변환 완료: 15개 비디오<br/>절약된 용량: 2.3GB"

        SCRIPT-->>LAUNCHD: exit 0
    end
    deactivate SCRIPT
```

## 4. 에러 처리 및 복구

### 4.1 변환 실패 시 재시도 로직

```mermaid
sequenceDiagram
    autonumber
    participant ORCH as Orchestrator
    participant CONV as Converter
    participant FFMPEG as FFmpeg
    participant RETRY as RetryManager
    participant FAILED as FailedQueue
    participant LOG as Logger

    ORCH->>CONV: convert(video)
    activate CONV

    CONV->>FFMPEG: execute()
    activate FFMPEG

    alt FFmpeg Error (exit code != 0)
        FFMPEG-->>CONV: error (exit_code=1)
        deactivate FFMPEG

        CONV->>RETRY: should_retry(attempt=1)
        RETRY-->>CONV: true (max_retries=3)

        CONV->>LOG: log_warning("Attempt 1 failed, retrying...")

        Note over CONV: Wait with exponential backoff<br/>delay = 5 * attempt seconds
        CONV->>CONV: sleep(5)

        CONV->>FFMPEG: execute() [retry 2]
        activate FFMPEG
        FFMPEG-->>CONV: error
        deactivate FFMPEG

        CONV->>RETRY: should_retry(attempt=2)
        RETRY-->>CONV: true

        CONV->>CONV: sleep(10)

        CONV->>FFMPEG: execute() [retry 3]
        activate FFMPEG
        FFMPEG-->>CONV: error
        deactivate FFMPEG

        CONV->>RETRY: should_retry(attempt=3)
        RETRY-->>CONV: false (max reached)

        CONV->>FAILED: add_to_queue(video, error)
        CONV->>LOG: log_error("Conversion failed after 3 attempts")

        CONV-->>ORCH: ConversionResult(success=false)
    else FFmpeg Success
        FFMPEG-->>CONV: success (exit_code=0)
        deactivate FFMPEG
        CONV-->>ORCH: ConversionResult(success=true)
    end

    deactivate CONV
```

### 4.2 iCloud 다운로드 실패 처리

```mermaid
sequenceDiagram
    autonumber
    participant EXTRACT as Extractor
    participant OSXP as osxphotos
    participant ICLOUD as iCloud
    participant QUEUE as PendingQueue
    participant LOG as Logger

    EXTRACT->>OSXP: export(video, download=True)
    activate OSXP

    OSXP->>ICLOUD: request_download(asset_id)
    activate ICLOUD

    alt Network Error
        ICLOUD-->>OSXP: NetworkError
        deactivate ICLOUD

        OSXP-->>EXTRACT: ExportError("Network unavailable")

        EXTRACT->>QUEUE: add_pending(video, reason="network")
        EXTRACT->>LOG: log_info("Video queued for later: network issue")

    else Timeout
        ICLOUD-->>OSXP: TimeoutError
        deactivate ICLOUD

        OSXP-->>EXTRACT: ExportError("Download timeout")

        EXTRACT->>QUEUE: add_pending(video, reason="timeout")
        EXTRACT->>LOG: log_warning("Video queued: download timeout")

    else iCloud Quota Exceeded
        ICLOUD-->>OSXP: QuotaExceededError

        OSXP-->>EXTRACT: ExportError("iCloud quota exceeded")

        EXTRACT->>LOG: log_error("Cannot download: quota exceeded")
        Note over EXTRACT: Skip this video entirely

    else Success
        ICLOUD-->>OSXP: downloaded_data
        OSXP->>OSXP: write_to_disk()
        OSXP-->>EXTRACT: exported_path
    end

    deactivate OSXP
```

## 5. 품질 검증 프로세스

### 5.1 변환 후 품질 검증

```mermaid
sequenceDiagram
    autonumber
    participant CONV as Converter
    participant VALID as QualityValidator
    participant FFPROBE as FFprobe
    participant VMAF as VMAF Calculator
    participant CONFIG as Config

    CONV->>VALID: validate(original, converted)
    activate VALID

    Note over VALID: Step 1: 파일 무결성 검사
    VALID->>FFPROBE: probe(converted)
    activate FFPROBE
    FFPROBE-->>VALID: MediaInfo
    deactivate FFPROBE

    alt Invalid file structure
        VALID-->>CONV: ValidationResult(valid=false, reason="corrupt")
    end

    Note over VALID: Step 2: 기본 속성 비교
    VALID->>VALID: compare_duration(original, converted)
    VALID->>VALID: compare_resolution(original, converted)
    VALID->>VALID: compare_framerate(original, converted)

    alt Properties mismatch
        VALID-->>CONV: ValidationResult(valid=false, reason="properties_mismatch")
    end

    Note over VALID: Step 3: 화질 검증 (선택적)
    VALID->>CONFIG: get_validation_settings()
    CONFIG-->>VALID: {validate_quality: true, min_vmaf: 93}

    alt Quality validation enabled
        VALID->>VMAF: calculate_vmaf(original, converted)
        activate VMAF
        Note over VMAF: FFmpeg libvmaf filter<br/>Takes significant time
        VMAF-->>VALID: vmaf_score (0-100)
        deactivate VMAF

        alt VMAF score below threshold
            VALID-->>CONV: ValidationResult(valid=false, reason="quality_below_threshold", vmaf=score)
        end
    end

    Note over VALID: Step 4: 압축률 확인
    VALID->>VALID: calculate_compression_ratio()

    alt Unusual compression (< 20% or > 80%)
        VALID->>VALID: add_warning("unusual_compression")
    end

    VALID-->>CONV: ValidationResult(valid=true, vmaf=score, warnings=[])
    deactivate VALID
```

## 6. 메타데이터 처리 상세

### 6.1 메타데이터 추출 및 복원

```mermaid
sequenceDiagram
    autonumber
    participant CONV as Converter
    participant META as MetadataManager
    participant FFMPEG as FFmpeg
    participant EXIF as ExifTool
    participant FS as FileSystem

    Note over META: Phase 1: FFmpeg 변환 시 기본 메타데이터 복사
    CONV->>FFMPEG: convert with -map_metadata 0
    FFMPEG-->>CONV: output with basic metadata

    Note over META: Phase 2: ExifTool로 상세 메타데이터 복원
    CONV->>META: restore_full_metadata(original, converted)
    activate META

    META->>EXIF: exiftool -json original.mp4
    activate EXIF
    EXIF-->>META: JSON metadata
    deactivate EXIF

    Note over META: 주요 메타데이터 항목:<br/>- CreateDate, ModifyDate<br/>- GPSLatitude, GPSLongitude<br/>- Make, Model (카메라 정보)<br/>- Duration, VideoFrameRate

    META->>META: filter_transferable_tags(metadata)

    META->>EXIF: exiftool -tagsFromFile original.mp4 converted.mp4
    activate EXIF
    EXIF->>EXIF: copy all transferable tags
    EXIF-->>META: success (tags copied)
    deactivate EXIF

    Note over META: Phase 3: 파일 시스템 타임스탬프 동기화
    META->>FS: get_timestamps(original)
    FS-->>META: {created, modified, accessed}

    META->>FS: set_timestamps(converted, timestamps)
    FS-->>META: success

    META-->>CONV: metadata_restored
    deactivate META
```

### 6.2 GPS 및 위치 정보 보존

```mermaid
sequenceDiagram
    autonumber
    participant META as MetadataManager
    participant EXIF as ExifTool
    participant ORIG as Original Video
    participant CONV as Converted Video

    META->>EXIF: extract GPS data from original
    activate EXIF

    EXIF->>ORIG: read QuickTime:GPSCoordinates
    ORIG-->>EXIF: "37.5665, 126.9780"

    EXIF->>ORIG: read Keys:GPSCoordinates
    ORIG-->>EXIF: "37.5665, 126.9780"

    EXIF->>ORIG: read UserData:GPSCoordinates
    ORIG-->>EXIF: (may be empty)

    EXIF-->>META: GPS data extracted
    deactivate EXIF

    META->>META: validate GPS coordinates

    META->>EXIF: write GPS to converted
    activate EXIF

    Note over EXIF: Write to multiple locations<br/>for maximum compatibility

    EXIF->>CONV: write QuickTime:GPSCoordinates
    EXIF->>CONV: write Keys:GPSCoordinates
    EXIF->>CONV: write XMP:GPSLatitude/Longitude

    EXIF-->>META: GPS data written
    deactivate EXIF

    META->>META: verify GPS in converted file
```

## 7. 진행 상황 모니터링

### 7.1 실시간 진행률 추적

```mermaid
sequenceDiagram
    autonumber
    participant ORCH as Orchestrator
    participant CONV as Converter
    participant FFMPEG as FFmpeg Process
    participant PROGRESS as ProgressTracker
    participant UI as CLI/Notification

    ORCH->>CONV: convert(video)
    CONV->>FFMPEG: spawn with -progress pipe:1
    activate FFMPEG

    CONV->>PROGRESS: start_tracking(video.duration)
    activate PROGRESS

    loop While FFmpeg running
        FFMPEG-->>CONV: progress output line
        Note over CONV: out_time_ms=12500000<br/>frame=375<br/>fps=45.2

        CONV->>PROGRESS: update(out_time_ms)
        PROGRESS->>PROGRESS: calculate percentage
        PROGRESS->>PROGRESS: estimate remaining time

        PROGRESS-->>UI: progress_callback(45%, eta="2:30")
        UI->>UI: update display
    end

    FFMPEG-->>CONV: process completed
    deactivate FFMPEG

    PROGRESS->>PROGRESS: finalize()
    PROGRESS-->>ORCH: final_stats
    deactivate PROGRESS

    ORCH->>UI: display_completion(stats)
```
