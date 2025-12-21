# Sequence Diagrams

## 1. Batch Conversion Workflow

### 1.1 Overall Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Orchestrator
    participant PhotosExtractor
    participant CodecDetector
    participant Converter
    participant MetadataManager
    participant Validator
    participant Notifier

    User->>CLI: video-converter run
    CLI->>Orchestrator: run_batch(mode="photos")

    Orchestrator->>PhotosExtractor: scan_videos()
    PhotosExtractor-->>Orchestrator: List[VideoInfo]

    loop For each video
        Orchestrator->>CodecDetector: detect_codec(video)
        CodecDetector-->>Orchestrator: CodecInfo

        alt is H.264
            Orchestrator->>PhotosExtractor: export_video(video)
            PhotosExtractor-->>Orchestrator: exported_path

            Orchestrator->>Converter: convert(request)
            Converter-->>Orchestrator: ConversionResult

            Orchestrator->>MetadataManager: apply_all(src, dst)
            MetadataManager-->>Orchestrator: success

            Orchestrator->>Validator: validate(original, converted)
            Validator-->>Orchestrator: ValidationResult
        else is HEVC
            Note over Orchestrator: Skip (already HEVC)
        end
    end

    Orchestrator->>Notifier: notify_completion(stats)
    Orchestrator-->>CLI: BatchResult
    CLI-->>User: Display report
```

### 1.2 Single File Conversion

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Orchestrator
    participant CodecDetector
    participant Converter
    participant MetadataManager
    participant Validator

    User->>CLI: video-converter convert input.mp4 output.mp4
    CLI->>Orchestrator: convert_single(input, output, options)

    Orchestrator->>CodecDetector: detect_codec(input)
    CodecDetector-->>Orchestrator: CodecInfo

    alt is H.264
        Orchestrator->>Converter: convert(ConversionRequest)

        loop While converting
            Converter-->>CLI: progress update
            CLI-->>User: [████░░░░] 50%
        end

        Converter-->>Orchestrator: ConversionResult

        Orchestrator->>MetadataManager: apply_all(input, output)
        MetadataManager-->>Orchestrator: success

        Orchestrator->>Validator: validate(input, output)
        Validator-->>Orchestrator: ValidationResult

        Orchestrator-->>CLI: ConversionResult
        CLI-->>User: ✅ Complete: 1.5GB → 680MB (54% saved)
    else is HEVC
        Orchestrator-->>CLI: Error: Already HEVC
        CLI-->>User: ❌ Video is already HEVC encoded
    end
```

## 2. Photos Library Access

### 2.1 Video Extraction

```mermaid
sequenceDiagram
    participant Orchestrator
    participant PhotosExtractor
    participant osxphotos
    participant PhotosDB
    participant iCloud

    Orchestrator->>PhotosExtractor: scan_videos(filter_codec="h264")
    PhotosExtractor->>osxphotos: PhotosDB()
    osxphotos->>PhotosDB: Connect
    PhotosDB-->>osxphotos: connection

    PhotosExtractor->>osxphotos: query(movies=True)
    osxphotos->>PhotosDB: SELECT videos
    PhotosDB-->>osxphotos: video_list
    osxphotos-->>PhotosExtractor: List[PhotoInfo]

    loop For each video
        PhotosExtractor->>PhotosExtractor: check_codec(video)
        alt is H.264
            PhotosExtractor->>PhotosExtractor: add_to_result(video)
        end
    end

    PhotosExtractor-->>Orchestrator: List[VideoInfo]
```

### 2.2 iCloud Download

```mermaid
sequenceDiagram
    participant Orchestrator
    participant PhotosExtractor
    participant osxphotos
    participant iCloud

    Orchestrator->>PhotosExtractor: export_video(video, download_icloud=True)

    PhotosExtractor->>osxphotos: is_in_icloud(video)
    osxphotos-->>PhotosExtractor: True

    PhotosExtractor->>iCloud: request_download(video)

    loop Until downloaded or timeout
        PhotosExtractor->>iCloud: check_status(video)
        iCloud-->>PhotosExtractor: downloading/complete
        alt if timeout
            PhotosExtractor-->>Orchestrator: iCloudTimeoutError
        end
    end

    iCloud-->>PhotosExtractor: download_complete
    PhotosExtractor->>osxphotos: export(video, dest_dir)
    osxphotos-->>PhotosExtractor: exported_path
    PhotosExtractor-->>Orchestrator: Path
```

## 3. Conversion Process

### 3.1 Hardware Conversion (VideoToolbox)

```mermaid
sequenceDiagram
    participant Orchestrator
    participant HardwareConverter
    participant FFmpeg
    participant VideoToolbox
    participant ProgressMonitor

    Orchestrator->>HardwareConverter: convert(ConversionRequest)
    HardwareConverter->>HardwareConverter: build_command(request)

    HardwareConverter->>FFmpeg: spawn(command)
    FFmpeg->>VideoToolbox: init hevc_videotoolbox
    VideoToolbox-->>FFmpeg: encoder_ready

    loop For each frame
        FFmpeg->>VideoToolbox: encode_frame(frame)
        VideoToolbox-->>FFmpeg: encoded_data
        FFmpeg->>ProgressMonitor: progress_update
        ProgressMonitor-->>Orchestrator: ProgressInfo
    end

    FFmpeg-->>HardwareConverter: exit_code=0
    HardwareConverter-->>Orchestrator: ConversionResult(success=True)
```

### 3.2 Error Recovery

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Converter
    participant FFmpeg
    participant RetryHandler

    Orchestrator->>Converter: convert(request)

    loop max_retries=3
        Converter->>FFmpeg: execute(command)

        alt success
            FFmpeg-->>Converter: exit_code=0
            Converter-->>Orchestrator: ConversionResult(success=True)
        else failure (retryable)
            FFmpeg-->>Converter: exit_code!=0
            Converter->>RetryHandler: should_retry(error)
            RetryHandler-->>Converter: True, delay=5s
            Note over Converter: Wait 5s (exponential backoff)
        else failure (non-retryable)
            FFmpeg-->>Converter: corrupted_input
            Converter-->>Orchestrator: ConversionResult(success=False)
        end
    end

    Note over Orchestrator: Move to failed folder if all retries exhausted
```

## 4. Metadata Processing

### 4.1 Metadata Copy

```mermaid
sequenceDiagram
    participant Orchestrator
    participant MetadataManager
    participant ExifTool

    Orchestrator->>MetadataManager: apply_all(source, target)

    MetadataManager->>ExifTool: read_metadata(source)
    ExifTool-->>MetadataManager: Metadata

    MetadataManager->>ExifTool: copy_tags(source, target)
    Note over ExifTool: exiftool -tagsFromFile src -all:all dst
    ExifTool-->>MetadataManager: success

    MetadataManager->>ExifTool: copy_gps(source, target)
    Note over ExifTool: exiftool -tagsFromFile src "-GPS*" dst
    ExifTool-->>MetadataManager: success

    MetadataManager->>MetadataManager: sync_timestamps(source, target)

    MetadataManager->>MetadataManager: verify_gps(source, target)

    MetadataManager-->>Orchestrator: success
```

## 5. Automation

### 5.1 Scheduled Execution

```mermaid
sequenceDiagram
    participant launchd
    participant Python
    participant Orchestrator
    participant Notifier

    Note over launchd: StartCalendarInterval: 03:00

    launchd->>Python: spawn video_converter run
    Python->>Orchestrator: run_batch(mode="photos")

    Orchestrator->>Orchestrator: scan_and_convert()

    alt has_videos_to_convert
        loop For each video
            Orchestrator->>Orchestrator: process_video()
        end
        Orchestrator->>Notifier: notify_completion(stats)
    else no_videos
        Note over Orchestrator: Log and exit
    end

    Orchestrator-->>Python: BatchResult
    Python-->>launchd: exit_code=0
```

### 5.2 Service Management

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant LaunchdManager
    participant launchd

    User->>CLI: video-converter install
    CLI->>LaunchdManager: install(config)

    LaunchdManager->>LaunchdManager: generate_plist(config)
    LaunchdManager->>LaunchdManager: write_plist(path)
    LaunchdManager->>launchd: launchctl load <plist>
    launchd-->>LaunchdManager: success

    LaunchdManager-->>CLI: installed
    CLI-->>User: ✅ Service installed. Next run: 03:00
```

## 6. Quality Validation

### 6.1 Validation Flow

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Validator
    participant FFprobe

    Orchestrator->>Validator: validate(original, converted)

    Validator->>FFprobe: get_properties(converted)
    FFprobe-->>Validator: VideoProperties

    Validator->>Validator: check_integrity()
    Validator->>Validator: compare_properties(original, converted)
    Validator->>Validator: check_compression_ratio()

    alt all_checks_passed
        Validator-->>Orchestrator: ValidationResult(valid=True)
    else failed
        Validator-->>Orchestrator: ValidationResult(valid=False, errors=[...])
    end
```
