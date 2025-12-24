# 시스템 아키텍처

> **Version:** 1.2.0
> **Last Updated:** 2025-12-24

## 1. 전체 시스템 구조

### 1.1 계층형 아키텍처

```mermaid
graph TB
    subgraph PresentationLayer["Presentation Layer"]
        CLI["CLI Interface"]
        NOTIF["macOS Notifications"]
        LOG_VIEW["Log Viewer"]
    end

    subgraph ApplicationLayer["Application Layer"]
        ORCH["Orchestrator"]
        SCHED["Scheduler"]
        CONFIG["Configuration Manager"]
    end

    subgraph DomainLayer["Domain Layer"]
        EXTRACTOR["Video Extractor"]
        DETECTOR["Codec Detector"]
        CONVERTER["Video Converter"]
        META["Metadata Manager"]
        VALIDATOR["Quality Validator"]
    end

    subgraph InfrastructureLayer["Infrastructure Layer"]
        PHOTOS_API["Photos API Adapter"]
        FFMPEG_API["FFmpeg Adapter"]
        EXIF_API["ExifTool Adapter"]
        FS["File System Manager"]
        LOGGER["Logger"]
    end

    subgraph ExternalSystems["External Systems"]
        PHOTOS[("macOS Photos Library")]
        FFMPEG_BIN["FFmpeg Binary"]
        EXIFTOOL_BIN["ExifTool Binary"]
        DISK[("File System")]
    end

    CLI --> ORCH
    NOTIF --> ORCH

    ORCH --> SCHED
    ORCH --> CONFIG
    ORCH --> EXTRACTOR
    ORCH --> CONVERTER

    EXTRACTOR --> DETECTOR
    CONVERTER --> META
    CONVERTER --> VALIDATOR

    EXTRACTOR --> PHOTOS_API
    DETECTOR --> FFMPEG_API
    CONVERTER --> FFMPEG_API
    META --> EXIF_API
    VALIDATOR --> FFMPEG_API

    PHOTOS_API --> PHOTOS
    FFMPEG_API --> FFMPEG_BIN
    EXIF_API --> EXIFTOOL_BIN
    FS --> DISK

    ORCH --> LOGGER
    LOGGER --> LOG_VIEW
```

### 1.2 컴포넌트 상세

```mermaid
graph TB
    subgraph AppBoundary["Video Converter Application"]
        subgraph CoreComponents["Core Components"]
            scheduler["Scheduler<br/><i>launchd/Python</i>"]
            orchestrator["Orchestrator<br/><i>Python</i>"]
            config["Config Manager<br/><i>Python/JSON</i>"]
        end

        subgraph ProcessingComponents["Processing Components"]
            extractor["Video Extractor<br/><i>osxphotos</i>"]
            detector["Codec Detector<br/><i>FFprobe</i>"]
            converter["Video Converter<br/><i>FFmpeg</i>"]
            metadata["Metadata Manager<br/><i>ExifTool</i>"]
            validator["Quality Validator<br/><i>FFmpeg/VMAF</i>"]
        end

        subgraph OutputComponents["Output Components"]
            reporter["Reporter<br/><i>Python</i>"]
            notifier["Notifier<br/><i>AppleScript</i>"]
        end
    end

    subgraph ExternalSystems["External Systems"]
        photos[("macOS Photos<br/>Library")]
        filesystem[("File System<br/>Storage")]
    end

    scheduler -->|triggers| orchestrator
    orchestrator -->|extract request| extractor
    orchestrator -->|convert request| converter
    extractor -->|codec check| detector
    converter -->|metadata| metadata
    converter -->|validate| validator
    orchestrator -->|report| reporter
    orchestrator -->|notify| notifier

    extractor -->|read| photos
    converter -->|write| filesystem
```

### 1.3 컴포넌트 책임

| 컴포넌트 | 기술 | 책임 |
|---------|------|------|
| Scheduler | launchd/Python | 일정/이벤트 기반 실행 관리 |
| Orchestrator | Python | 전체 변환 워크플로우 조율 |
| Config Manager | Python/JSON | 설정 파일 관리 |
| Video Extractor | osxphotos | Photos 라이브러리에서 비디오 추출 |
| Codec Detector | FFprobe | 비디오 코덱 분석 |
| Video Converter | FFmpeg | H.264→H.265 변환 |
| Metadata Processor | ExifTool | 메타데이터 보존/복원 |
| Video Validator | FFmpeg | 변환 결과 검증 |
| Reporter | Python | 통계 및 보고서 생성 |
| Notification | AppleScript | macOS 알림 발송 |
| Session Manager | Python/JSON | 변환 세션 상태 영속성 및 재개 지원 |
| Conversion History | Python/JSON | 변환 이력 추적 및 중복 방지 |
| Error Recovery | Python | 오류 분류, 복구 전략 결정 및 실패 격리 |
| Concurrent Processor | Python/asyncio | 병렬 변환 처리 및 리소스 관리 |
| GPS Handler | ExifTool | GPS 좌표 추출, 적용 및 보존 검증 |
| VMAF Analyzer | FFmpeg/libvmaf | 비디오 품질 점수 분석 |
| Converter Factory | Python | 인코더(HW/SW) 선택 및 인스턴스 생성 |
| Progress Monitor | Python/Regex | 실시간 FFmpeg 진행률 파싱 및 ETA 계산 |
| Photos Importer | AppleScript | 변환된 비디오를 Photos 라이브러리로 재가져오기 |
| Photos Handler | Python | Photos 소스와 CLI 인터페이스 통합 |
| iCloud Handler | Python | iCloud 전용 파일 다운로드 대기 및 처리 |
| AppleScript Runner | osascript | AppleScript 명령 실행 및 결과 파싱 |
| Dependency Checker | Python/subprocess | FFmpeg, ExifTool 등 시스템 의존성 확인 |
| GUI Services | Python/tkinter | 변환, Photos, 설정 서비스 제공 |
| GUI Widgets | Python/tkinter | 드래그앤드롭, 진행률 카드, 비디오 그리드 |

## 2. 모듈 구조

### 2.1 패키지 다이어그램

```mermaid
graph TB
    subgraph video_converter["video_converter"]
        subgraph core["core"]
            ORCH_MOD["orchestrator.py"]
            CONFIG_MOD["config.py"]
            LOGGER_MOD["logger.py"]
            TYPES_MOD["types.py"]
            SESSION_MOD["session.py"]
            HISTORY_MOD["history.py"]
            ERR_RECOV["error_recovery.py"]
            CONCURRENT["concurrent.py"]
        end

        subgraph extractors["extractors"]
            PHOTOS_EXT["photos_extractor.py"]
            FOLDER_EXT["folder_extractor.py"]
            ICLOUD_HDL["icloud_handler.py"]
        end

        subgraph converters["converters"]
            HW_CONV["hardware.py"]
            SW_CONV["software.py"]
            CONV_BASE["base.py"]
            CONV_FACTORY["factory.py"]
            CONV_PROGRESS["progress.py"]
        end

        subgraph processors["processors"]
            CODEC_DET["codec_detector.py"]
            META_PROC["metadata.py"]
            QUALITY_VAL["quality_validator.py"]
            GPS_PROC["gps.py"]
            VMAF_ANAL["vmaf_analyzer.py"]
            VERIFY_PROC["verification.py"]
            TIMESTAMP["timestamp.py"]
            RETRY_MGR["retry_manager.py"]
        end

        subgraph importers["importers"]
            PHOTOS_IMP["photos_importer.py"]
            META_PRES["metadata_preservation.py"]
        end

        subgraph handlers["handlers"]
            PHOTOS_HDL["photos_handler.py"]
        end

        subgraph automation["automation"]
            LAUNCHD["launchd.py"]
            SERVICE_MGR["service_manager.py"]
            NOTIF["notification.py"]
        end

        subgraph reporters["reporters"]
            STATS_REP["statistics_reporter.py"]
            BATCH_REP["batch_reporter.py"]
        end

        subgraph ui["ui"]
            UI_PROGRESS["progress.py"]
            UI_PANELS["panels.py"]
        end

        subgraph utils["utils"]
            FILE_UTIL["file_utils.py"]
            CMD_RUNNER["command_runner.py"]
            CONSTANTS["constants.py"]
            APPLESCRIPT["applescript.py"]
            PROG_PARSER["progress_parser.py"]
            DEP_CHECKER["dependency_checker.py"]
        end

        subgraph gui["gui"]
            GUI_APP["app.py"]
            GUI_MAIN["main_window.py"]
            subgraph gui_views["views"]
                HOME_VIEW["home_view.py"]
                CONVERT_VIEW["convert_view.py"]
                PHOTOS_VIEW["photos_view.py"]
                QUEUE_VIEW["queue_view.py"]
                SETTINGS_VIEW["settings_view.py"]
            end
            subgraph gui_services["services"]
                CONV_SVC["conversion_service.py"]
                PHOTOS_SVC["photos_service.py"]
                SETTINGS_MGR["settings_manager.py"]
                UPDATE_SVC["update_service.py"]
            end
            subgraph gui_widgets["widgets"]
                DROP_ZONE["drop_zone.py"]
                PROG_CARD["progress_card.py"]
                RECENT_LIST["recent_list.py"]
                VIDEO_GRID["video_grid.py"]
            end
        end
    end

    ORCH_MOD --> PHOTOS_EXT
    ORCH_MOD --> FOLDER_EXT
    ORCH_MOD --> CONV_FACTORY
    ORCH_MOD --> SESSION_MOD
    ORCH_MOD --> HISTORY_MOD
    ORCH_MOD --> ERR_RECOV
    ORCH_MOD --> CONCURRENT
    CONV_FACTORY --> HW_CONV
    CONV_FACTORY --> SW_CONV
    HW_CONV --> CONV_BASE
    SW_CONV --> CONV_BASE
    CONV_BASE --> CODEC_DET
    CONV_BASE --> META_PROC
    CONV_BASE --> QUALITY_VAL
    CONV_BASE --> CONV_PROGRESS
    META_PROC --> GPS_PROC
    META_PROC --> TIMESTAMP
    QUALITY_VAL --> VMAF_ANAL
    QUALITY_VAL --> VERIFY_PROC
    PHOTOS_EXT --> ICLOUD_HDL
    PHOTOS_HDL --> PHOTOS_EXT
    PHOTOS_IMP --> APPLESCRIPT
    GUI_APP --> GUI_MAIN
    GUI_MAIN --> CONV_SVC
    GUI_MAIN --> PHOTOS_SVC
```

### 2.2 클래스 다이어그램

```mermaid
classDiagram
    class Orchestrator {
        -config: Config
        -extractor: VideoExtractor
        -converter: VideoConverter
        -reporter: Reporter
        +run()
        +run_single(video_path)
        +get_status() Status
    }

    class VideoExtractor {
        <<interface>>
        +extract_videos() List~Video~
        +get_video_info(path) VideoInfo
    }

    class PhotosExtractor {
        -photos_db: PhotosDB
        +extract_videos() List~Video~
        +filter_h264_only() List~Video~
        +export_video(video) Path
    }

    class FolderExtractor {
        -watch_path: Path
        +extract_videos() List~Video~
        +watch_for_changes()
    }

    class VideoConverter {
        <<interface>>
        +convert(input, output) Result
        +get_progress() float
    }

    class HardwareConverter {
        -quality: int
        +convert(input, output) Result
        -build_ffmpeg_command() List~str~
    }

    class SoftwareConverter {
        -crf: int
        -preset: str
        +convert(input, output) Result
        -build_ffmpeg_command() List~str~
    }

    class CodecDetector {
        +detect(path) CodecInfo
        +is_h264(path) bool
        +is_hevc(path) bool
    }

    class MetadataProcessor {
        +extract(path) Metadata
        +apply(source, target)
        +sync_timestamps(source, target)
    }

    class VideoValidator {
        +validate(path) ValidationResult
        +compare(original, converted) ComparisonResult
        +check_file_integrity(path) bool
    }

    class Video {
        +path: Path
        +original_name: str
        +codec: str
        +duration: float
        +size: int
        +metadata: Metadata
    }

    class ConversionResult {
        +success: bool
        +input_path: Path
        +output_path: Path
        +original_size: int
        +converted_size: int
        +duration: float
        +error: str
    }

    Orchestrator --> VideoExtractor
    Orchestrator --> VideoConverter
    VideoExtractor <|.. PhotosExtractor
    VideoExtractor <|.. FolderExtractor
    VideoConverter <|.. HardwareConverter
    VideoConverter <|.. SoftwareConverter
    HardwareConverter --> CodecDetector
    SoftwareConverter --> CodecDetector
    HardwareConverter --> MetadataProcessor
    SoftwareConverter --> MetadataProcessor
    HardwareConverter --> VideoValidator
    SoftwareConverter --> VideoValidator
    VideoExtractor ..> Video
    VideoConverter ..> ConversionResult
```

### 2.3 Core 모듈 클래스 다이어그램

```mermaid
classDiagram
    class SessionStateManager {
        -state_dir: Path
        -current_session: SessionState
        +create_session(video_paths, output_dir) SessionState
        +save()
        +load_session() SessionState
        +has_resumable_session() bool
        +pause_session() bool
        +resume_session() SessionState
        +complete_session()
    }

    class SessionState {
        +session_id: str
        +status: SessionStatus
        +pending_videos: List~VideoEntry~
        +completed_videos: List~VideoEntry~
        +failed_videos: List~VideoEntry~
        +progress: float
        +is_resumable: bool
    }

    class ConversionHistory {
        -records: Dict~str, ConversionRecord~
        +is_converted(id) bool
        +add_record(record)
        +get_statistics() HistoryStatistics
        +export_to_json(path)
    }

    class ErrorRecoveryManager {
        -failed_dir: Path
        -failure_records: List~FailureRecord~
        +classify_error(message) ErrorCategory
        +get_recovery_action(category) RecoveryAction
        +handle_failure(input, output, category, message) FailureRecord
        +cleanup_partial_output(path) bool
    }

    class ConcurrentProcessor {
        -max_concurrent: int
        -semaphore: Semaphore
        +process_batch(items, processor) List~Result~
        +get_aggregated_progress() AggregatedProgress
        +cancel()
    }

    SessionStateManager --> SessionState
    SessionState --> VideoEntry
    ConversionHistory --> ConversionRecord
    ErrorRecoveryManager --> FailureRecord
    ConcurrentProcessor --> AggregatedProgress
```

### 2.4 Importers/Handlers 클래스 다이어그램

```mermaid
classDiagram
    class PhotosImporter {
        -timeout: float
        -script_runner: AppleScriptRunner
        +import_video(path) str
        +verify_import(uuid) bool
        +handle_original(uuid, handling)
    }

    class PhotosSourceHandler {
        -library: PhotosLibrary
        -exporter: VideoExporter
        +check_permissions() bool
        +get_candidates(options) List~PhotosVideoInfo~
        +export_video(video) Path
        +cleanup_exported(path) bool
    }

    class GPSHandler {
        -processor: MetadataProcessor
        +extract(path) GPSCoordinates
        +apply(path, coords) bool
        +verify(original, converted) GPSVerificationResult
    }

    class ConverterFactory {
        -hardware_converter: HardwareConverter
        -software_converter: SoftwareConverter
        +get_converter(mode) BaseConverter
        +get_available_converters() List~BaseConverter~
        +is_hardware_available() bool
    }

    PhotosImporter --> AppleScriptRunner
    PhotosSourceHandler --> PhotosLibrary
    PhotosSourceHandler --> VideoExporter
    ConverterFactory --> HardwareConverter
    ConverterFactory --> SoftwareConverter
```

### 2.5 GUI 모듈 클래스 다이어그램

```mermaid
classDiagram
    class MainWindow {
        -sidebar: Sidebar
        -content_area: ContentArea
        -current_view: View
        +switch_view(view_name)
    }

    class ConversionService {
        -converter_factory: ConverterFactory
        -progress_callbacks: List~Callable~
        +convert_files(files) List~Result~
        +get_progress() float
        +cancel()
    }

    class PhotosService {
        -handler: PhotosSourceHandler
        +get_candidates() List~PhotosVideoInfo~
        +convert_selected(videos)
    }

    class SettingsManager {
        -config_path: Path
        +load() Settings
        +save(settings)
        +get(key) Any
    }

    MainWindow --> ConversionService
    MainWindow --> PhotosService
    MainWindow --> SettingsManager
```

## 3. 배포 다이어그램

### 3.1 시스템 배포 구조

```mermaid
graph TB
    subgraph MacOS["macOS System"]
        subgraph UserSpace["User Space"]
            APP["Video Converter App<br/>Python Application"]
            LAUNCHD_AGENT["LaunchAgent<br/>com.user.videoconverter"]
        end

        subgraph Applications["Applications"]
            PHOTOS_APP["Photos.app"]
            TERMINAL["Terminal.app"]
        end

        subgraph CLITools["Command Line Tools<br/>/opt/homebrew/bin/"]
            FFMPEG["ffmpeg"]
            FFPROBE["ffprobe"]
            EXIFTOOL["exiftool"]
            PYTHON["python3"]
            OSXPHOTOS["osxphotos"]
        end

        subgraph Frameworks["System Frameworks"]
            VT["VideoToolbox.framework"]
            PHOTOKIT["PhotoKit.framework"]
            COREMEDIA["CoreMedia.framework"]
        end

        subgraph Storage["File System Storage"]
            PHOTOS_LIB[("Photos Library<br/>~/Pictures/")]
            INPUT_DIR[("Input Directory<br/>~/Videos/ToConvert/")]
            OUTPUT_DIR[("Output Directory<br/>~/Videos/Converted/")]
            CONFIG_DIR[("Config Directory<br/>~/.config/video_converter/")]
            LOG_DIR[("Log Directory<br/>~/Library/Logs/")]
        end
    end

    LAUNCHD_AGENT -->|triggers| APP
    APP -->|subprocess| PYTHON
    APP -->|subprocess| OSXPHOTOS
    APP -->|subprocess| FFMPEG
    APP -->|subprocess| EXIFTOOL

    OSXPHOTOS -->|read| PHOTOS_LIB
    OSXPHOTOS -->|framework| PHOTOKIT

    FFMPEG -->|framework| VT
    FFMPEG -->|framework| COREMEDIA
    FFMPEG -->|read| INPUT_DIR
    FFMPEG -->|write| OUTPUT_DIR

    FFPROBE -->|read| INPUT_DIR

    APP -->|read| CONFIG_DIR
    APP -->|write| LOG_DIR

    PHOTOS_APP -->|manages| PHOTOS_LIB
```

### 3.2 배포 노드 상세

```mermaid
graph LR
    subgraph DeploymentNodes["Deployment Nodes"]
        subgraph LaunchDaemon["launchd Daemon"]
            PLIST["plist 설정 파일<br/>~/Library/LaunchAgents/"]
            SCHEDULE["StartCalendarInterval<br/>Hour: 3, Minute: 0"]
            WATCHPATH["WatchPaths<br/>~/Videos/ToConvert/"]
        end

        subgraph PythonRuntime["Python Runtime"]
            VENV["Virtual Environment<br/>Python 3.10+"]
            DEPS["Dependencies<br/>osxphotos, etc."]
        end

        subgraph FFmpegStack["FFmpeg Stack"]
            FFMPEG_BIN["FFmpeg 6.0+"]
            LIBX265["libx265 encoder"]
            VIDEOTOOLBOX["VideoToolbox encoder"]
        end
    end

    PLIST -->|load| SCHEDULE
    PLIST -->|watch| WATCHPATH
    SCHEDULE -->|trigger| PythonRuntime
    WATCHPATH -->|trigger| PythonRuntime
    PythonRuntime -->|call| FFmpegStack
```

### 3.3 물리적 배포 경로

```
macOS System
├── /opt/homebrew/bin/                    # Homebrew CLI Tools
│   ├── ffmpeg                            # Video encoder/decoder
│   ├── ffprobe                           # Media analyzer
│   ├── exiftool                          # Metadata tool
│   └── python3                           # Python interpreter
│
├── ~/                                     # User Home
│   ├── Library/
│   │   ├── LaunchAgents/
│   │   │   └── com.user.videoconverter.plist
│   │   └── Logs/
│   │       └── video_converter/
│   │           ├── stdout.log
│   │           └── stderr.log
│   │
│   ├── Pictures/
│   │   └── Photos Library.photoslibrary/  # Photos Database
│   │
│   ├── Videos/
│   │   ├── ToConvert/                     # Watch directory
│   │   ├── Converted/                     # Output directory
│   │   ├── Processed/                     # Backup originals
│   │   └── Failed/                        # Failed conversions
│   │
│   └── .config/
│       └── video_converter/
│           └── config.json                # User configuration
│
└── /System/Library/Frameworks/            # System Frameworks
    ├── VideoToolbox.framework
    ├── CoreMedia.framework
    └── Photos.framework
```

## 4. 디렉토리 구조

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── __main__.py              # CLI 엔트리포인트
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py      # 메인 오케스트레이터
│       │   ├── config.py            # 설정 관리
│       │   ├── logger.py            # 로깅 설정
│       │   ├── types.py             # 핵심 데이터 타입 정의
│       │   ├── session.py           # 세션 상태 영속성 관리
│       │   ├── history.py           # 변환 이력 추적 (중복 방지)
│       │   ├── error_recovery.py    # 오류 복구 및 실패 격리
│       │   └── concurrent.py        # 병렬 처리 지원
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── photos_extractor.py  # Photos 라이브러리 추출
│       │   ├── folder_extractor.py  # 폴더 감시 추출
│       │   └── icloud_handler.py    # iCloud 파일 다운로드 처리
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── base.py              # 추상 베이스 클래스
│       │   ├── hardware.py          # VideoToolbox 변환
│       │   ├── software.py          # libx265 변환
│       │   ├── factory.py           # 변환기 팩토리 패턴
│       │   └── progress.py          # 실시간 진행률 모니터링
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── codec_detector.py    # 코덱 감지
│       │   ├── metadata.py          # 메타데이터 처리
│       │   ├── quality_validator.py # 품질 검증
│       │   ├── gps.py               # GPS 좌표 보존
│       │   ├── vmaf_analyzer.py     # VMAF 품질 분석
│       │   ├── verification.py      # 출력 파일 검증
│       │   ├── timestamp.py         # 타임스탬프 동기화
│       │   └── retry_manager.py     # 재시도 로직 관리
│       ├── importers/
│       │   ├── __init__.py
│       │   ├── photos_importer.py   # Photos 라이브러리 재가져오기
│       │   └── metadata_preservation.py  # 메타데이터 보존 처리
│       ├── handlers/
│       │   ├── __init__.py
│       │   └── photos_handler.py    # Photos 소스 핸들러 (CLI 통합)
│       ├── automation/
│       │   ├── __init__.py
│       │   ├── launchd.py           # launchd 설정 생성
│       │   ├── notification.py      # macOS 알림 발송
│       │   └── service_manager.py   # 서비스 관리
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── statistics_reporter.py  # 통계 리포터
│       │   └── batch_reporter.py       # 배치 리포터
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── progress.py          # CLI 진행률 표시
│       │   └── panels.py            # 터미널 UI 패널
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── file_utils.py        # 파일 유틸리티
│       │   ├── command_runner.py    # 명령 실행 유틸리티
│       │   ├── constants.py         # 상수 정의
│       │   ├── applescript.py       # AppleScript 실행 유틸리티
│       │   ├── progress_parser.py   # FFmpeg 진행률 파싱
│       │   └── dependency_checker.py # 시스템 의존성 확인
│       └── gui/
│           ├── __init__.py
│           ├── app.py               # GUI 애플리케이션 진입점
│           ├── main_window.py       # 메인 윈도우
│           ├── menubar/
│           │   ├── __init__.py
│           │   └── menubar_app.py   # 메뉴바 앱
│           ├── styles/
│           │   ├── __init__.py
│           │   └── theme.py         # UI 테마 설정
│           ├── views/
│           │   ├── __init__.py
│           │   ├── home_view.py     # 홈 뷰
│           │   ├── convert_view.py  # 변환 뷰
│           │   ├── photos_view.py   # Photos 뷰
│           │   ├── queue_view.py    # 큐 관리 뷰
│           │   └── settings_view.py # 설정 뷰
│           ├── services/
│           │   ├── __init__.py
│           │   ├── conversion_service.py  # 변환 서비스
│           │   ├── photos_service.py      # Photos 서비스
│           │   ├── settings_manager.py    # 설정 관리자
│           │   └── update_service.py      # 업데이트 서비스
│           ├── widgets/
│           │   ├── __init__.py
│           │   ├── drop_zone.py     # 드래그&드롭 영역
│           │   ├── progress_card.py # 진행률 카드
│           │   ├── recent_list.py   # 최근 항목 목록
│           │   └── video_grid.py    # 비디오 그리드 뷰
│           └── dialogs/
│               ├── __init__.py
│               └── result_dialog.py # 결과 대화상자
├── config/
│   ├── default.json                 # 기본 설정
│   └── launchd/
│       └── com.user.videoconverter.plist
├── scripts/
│   ├── install.sh                   # 설치 스크립트
│   ├── uninstall.sh                 # 제거 스크립트
│   └── convert_single.sh            # 단일 파일 변환
├── tests/
│   ├── __init__.py
│   ├── test_extractors.py
│   ├── test_converters.py
│   └── test_processors.py
├── docs/
│   ├── reference/                   # 참조 문서
│   └── architecture/                # 아키텍처 문서
├── pyproject.toml
└── README.md
```

## 5. 설정 스키마

### 5.1 ER 다이어그램

```mermaid
erDiagram
    CONFIG {
        string version
        string log_level
    }

    ENCODING {
        string mode
        int quality
        int crf
        string preset
        boolean two_pass
    }

    PATHS {
        string input_dir
        string output_dir
        string processed_dir
        string failed_dir
        string log_dir
    }

    AUTOMATION {
        string method
        string schedule
        string time
        boolean run_at_load
    }

    PHOTOS {
        boolean auto_export
        boolean skip_edited
        boolean download_from_icloud
        string albums_include
        string albums_exclude
    }

    PROCESSING {
        int max_concurrent
        boolean preserve_original
        boolean validate_quality
        float min_vmaf_score
    }

    NOTIFICATION {
        boolean enabled
        boolean on_complete
        boolean on_error
        boolean daily_summary
    }

    CONFIG ||--|| ENCODING : has
    CONFIG ||--|| PATHS : has
    CONFIG ||--|| AUTOMATION : has
    CONFIG ||--|| PHOTOS : has
    CONFIG ||--|| PROCESSING : has
    CONFIG ||--|| NOTIFICATION : has
```

### 5.2 설정 필드 설명

| 섹션 | 필드 | 타입 | 설명 |
|------|------|------|------|
| **encoding** | mode | string | `hardware` 또는 `software` |
| | quality | int | 하드웨어 인코딩 품질 (1-100) |
| | crf | int | 소프트웨어 인코딩 CRF (0-51) |
| | preset | string | 인코딩 속도/품질 프리셋 |
| **paths** | input_dir | string | 입력 비디오 디렉토리 |
| | output_dir | string | 출력 비디오 디렉토리 |
| **automation** | method | string | `launchd`, `folder_action`, `manual` |
| | schedule | string | `hourly`, `daily`, `weekly` |
| | time | string | HH:MM 형식 실행 시간 |
| **photos** | auto_export | boolean | Photos에서 자동 내보내기 |
| | albums_include | string | 포함할 앨범 (쉼표 구분) |
| | albums_exclude | string | 제외할 앨범 (쉼표 구분) |
| **processing** | max_concurrent | int | 동시 변환 수 |
| | validate_quality | boolean | VMAF 품질 검증 활성화 |
| | min_vmaf_score | float | 최소 VMAF 점수 |
| **notification** | enabled | boolean | 알림 활성화 |
| | on_complete | boolean | 완료 시 알림 |
| | on_error | boolean | 에러 시 알림 |

## 6. 인터페이스 정의

### 6.1 VideoExtractor 인터페이스

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VideoInfo:
    path: Path
    original_name: str
    codec: str
    duration: float
    size: int
    creation_date: datetime
    location: Optional[tuple[float, float]]
    albums: List[str]

class VideoExtractor(ABC):
    @abstractmethod
    def extract_videos(self,
                       filter_codec: Optional[str] = None,
                       since_date: Optional[datetime] = None) -> List[VideoInfo]:
        """추출 대상 비디오 목록 반환"""
        pass

    @abstractmethod
    def export_video(self, video: VideoInfo, dest_dir: Path) -> Path:
        """비디오를 지정된 디렉토리로 내보내기"""
        pass
```

### 6.2 VideoConverter 인터페이스

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

class ConversionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ConversionResult:
    status: ConversionStatus
    input_path: Path
    output_path: Optional[Path]
    original_size: int
    converted_size: Optional[int]
    compression_ratio: Optional[float]
    duration_seconds: float
    vmaf_score: Optional[float]
    error_message: Optional[str]

class VideoConverter(ABC):
    @abstractmethod
    def convert(self,
                input_path: Path,
                output_path: Path,
                preserve_metadata: bool = True) -> ConversionResult:
        """비디오 변환 실행"""
        pass

    @abstractmethod
    def get_progress(self) -> float:
        """현재 진행률 반환 (0.0 ~ 1.0)"""
        pass

    @abstractmethod
    def cancel(self) -> bool:
        """진행 중인 변환 취소"""
        pass
```

## 7. 에러 처리 전략

```mermaid
graph TD
    START["변환 시작"] --> CHECK_INPUT{"입력 파일 존재?"}
    CHECK_INPUT -->|No| ERR_NOT_FOUND["FileNotFoundError"]
    CHECK_INPUT -->|Yes| CHECK_CODEC{"H.264 코덱?"}

    CHECK_CODEC -->|No| SKIP["건너뛰기 - 이미 HEVC"]
    CHECK_CODEC -->|Yes| CONVERT["변환 시작"]

    CONVERT --> CONVERT_RESULT{"변환 성공?"}
    CONVERT_RESULT -->|Yes| VALIDATE{"품질 검증"}
    CONVERT_RESULT -->|No| RETRY{"재시도 횟수 < 3?"}

    RETRY -->|Yes| WAIT["대기 후 재시도"]
    WAIT --> CONVERT
    RETRY -->|No| MOVE_FAILED["실패 폴더로 이동"]
    MOVE_FAILED --> LOG_ERROR["에러 로깅"]
    LOG_ERROR --> NOTIFY_ERROR["에러 알림"]

    VALIDATE -->|Pass| RESTORE_META["메타데이터 복원"]
    VALIDATE -->|Fail| RETRY

    RESTORE_META --> META_RESULT{"메타데이터 성공?"}
    META_RESULT -->|Yes| MOVE_PROCESSED["원본 처리 완료 폴더로"]
    META_RESULT -->|No| LOG_WARN["경고 로깅"]
    LOG_WARN --> MOVE_PROCESSED

    MOVE_PROCESSED --> SUCCESS["완료"]

    ERR_NOT_FOUND --> LOG_ERROR
    SKIP --> SUCCESS
```

## 8. 시스템 요구사항

### 8.1 하드웨어 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| CPU | Apple M1 | Apple M2 Pro 이상 |
| RAM | 8GB | 16GB 이상 |
| Storage | 변환 대상의 2배 | 변환 대상의 3배 |

### 8.2 소프트웨어 요구사항

| 소프트웨어 | 버전 | 설치 방법 |
|------------|------|-----------|
| macOS | 12.0+ (Monterey) | - |
| Python | 3.10+ | `brew install python@3.12` |
| FFmpeg | 5.0+ | `brew install ffmpeg` |
| ExifTool | 12.0+ | `brew install exiftool` |
| osxphotos | 0.70+ | `pip install osxphotos` |

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0.0 | 2024-01-01 | 초기 문서 작성 |
| 1.1.0 | 2024-12-24 | 파일명 및 클래스명 실제 구현과 일치하도록 업데이트 (Issue #192) |
