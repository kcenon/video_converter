# Video Converter - Software Design Specification (SDS)

**문서 버전**: 1.1.0
**작성일**: 2025-12-23
**상태**: Active
**기준 문서**: SRS v1.0.0

---

## 문서 정보

### 추적성 정보

| 항목 | 참조 |
|------|------|
| 상위 문서 | SRS.md v1.0.0 |
| 관련 문서 | PRD.md, architecture/*.md, development-plan.md |
| 설계 ID 체계 | SDS-Mxx-xxx (모듈-항목 형식) |

### 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2025-12-21 | - | 최초 작성 |
| 1.1.0 | 2025-12-23 | - | 구현에 맞게 디렉토리 구조 업데이트, 새 모듈 추가 (ui, vmaf_analyzer, concurrent, session, error_recovery 등) |

---

## 목차

1. [설계 개요](#1-설계-개요)
2. [시스템 아키텍처 설계](#2-시스템-아키텍처-설계)
3. [모듈 상세 설계](#3-모듈-상세-설계)
4. [클래스 상세 설계](#4-클래스-상세-설계)
5. [데이터베이스 설계](#5-데이터베이스-설계)
6. [인터페이스 설계](#6-인터페이스-설계)
7. [에러 처리 설계](#7-에러-처리-설계)
8. [보안 설계](#8-보안-설계)
9. [성능 설계](#9-성능-설계)
10. [설계 추적 매트릭스](#10-설계-추적-매트릭스)
11. [부록](#11-부록)

---

## 1. 설계 개요

### 1.1 목적

본 문서는 Video Converter 시스템의 상세 설계를 정의합니다. SRS에서 명세된 요구사항을 구현하기 위한 구체적인 설계 결정사항, 알고리즘, 데이터 구조, 인터페이스를 제공합니다.

### 1.2 범위

| 항목 | 내용 |
|------|------|
| 시스템 명 | Video Converter |
| 대상 버전 | v0.1.0.0+ |
| 설계 범위 | 전체 시스템 (코어 모듈, 자동화, CLI) |

> **참고**: 본 프로젝트는 활발한 개발 상태를 나타내기 위해 0.x.x.x 버전 체계를 사용합니다.

### 1.3 설계 원칙

| 원칙 | 설명 | 적용 |
|------|------|------|
| **단일 책임 원칙 (SRP)** | 각 클래스는 하나의 책임만 가짐 | 모든 클래스 설계에 적용 |
| **개방-폐쇄 원칙 (OCP)** | 확장에 열려있고 수정에 닫혀있음 | Strategy 패턴 적용 |
| **의존성 역전 원칙 (DIP)** | 추상화에 의존, 구체화에 의존하지 않음 | 인터페이스 기반 설계 |
| **실패 안전 (Fail-Safe)** | 실패 시 데이터 손실 방지 | 원본 보존 정책 |
| **점진적 처리** | 대용량 데이터 스트리밍 처리 | 메모리 효율 설계 |

### 1.4 설계 ID 체계

```
SDS-{Module}-{Number}
     │        │
     │        └── 순번 (001-999)
     └── 모듈 코드:
         C01: Core (Orchestrator, Config)
         E01: Extractors
         V01: Video Converters
         P01: Processors (Codec, Metadata, Validator)
         A01: Automation (launchd, Folder Action)
         R01: Reporters (Statistics, Notifier)
         U01: Utils
         D01: Database
         I01: Interface (CLI)
```

---

## 2. 시스템 아키텍처 설계

### 2.1 아키텍처 개요

> **참조**: [01-system-architecture.ko.md](architecture/01-system-architecture.ko.md)

본 시스템은 **4계층 아키텍처**를 채택합니다:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │     CLI     │  │   Notifier  │  │ Log Viewer  │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
├─────────────────────────────────────────────────────────────────────────┤
│                         Application Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ Orchestrator│  │  Scheduler  │  │   Config    │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
├─────────────────────────────────────────────────────────────────────────┤
│                          Domain Layer                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Extractor  │  │  Converter  │  │  Metadata   │  │  Validator  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                       Infrastructure Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ FFmpeg API  │  │ osxphotos   │  │  ExifTool   │  │   Logger    │    │
│  │  Adapter    │  │   Adapter   │  │   Adapter   │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 패키지 구조 설계

| SDS ID | 패키지 | 책임 | SRS 추적 |
|--------|--------|------|----------|
| SDS-C01-001 | `video_converter.core` | 핵심 오케스트레이션, 설정 관리 | SRS-701 |
| SDS-E01-001 | `video_converter.extractors` | 비디오 소스 추출 | SRS-301, SRS-302 |
| SDS-V01-001 | `video_converter.converters` | 비디오 인코딩 변환 | SRS-201, SRS-202 |
| SDS-P01-001 | `video_converter.processors` | 코덱 감지, 메타데이터, 검증 | SRS-101, SRS-401, SRS-501 |
| SDS-A01-001 | `video_converter.automation` | launchd 자동화 관리 | SRS-601, SRS-602 |
| SDS-R01-001 | `video_converter.reporters` | 통계 및 알림 | SRS-603 |
| SDS-U01-001 | `video_converter.utils` | 공통 유틸리티 | - |

### 2.3 디렉토리 구조

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── __main__.py                # CLI 엔트리 포인트
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py        # SDS-C01-001 (메인 워크플로우 조율)
│       │   ├── config.py              # SDS-C01-002 (설정 관리)
│       │   ├── logger.py              # SDS-C01-003 (로깅 시스템)
│       │   ├── types.py               # SDS-C01-004 (핵심 데이터 클래스)
│       │   ├── session.py             # SDS-C01-005 (세션 영속성)
│       │   ├── history.py             # SDS-C01-006 (변환 이력)
│       │   ├── error_recovery.py      # SDS-C01-007 (에러 처리)
│       │   └── concurrent.py          # SDS-C01-008 (병렬 처리)
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── photos_extractor.py    # SDS-E01-001 (Photos 라이브러리 접근)
│       │   ├── folder_extractor.py    # SDS-E01-002 (파일시스템 스캔)
│       │   └── icloud_handler.py      # SDS-E01-003 (iCloud 파일 처리)
│       ├── importers/
│       │   ├── __init__.py
│       │   ├── photos_importer.py         # SDS-P01-009 (Photos 재가져오기)
│       │   └── metadata_preservation.py   # SDS-P01-010 (메타데이터 보존)
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── base.py                # SDS-V01-001 (추상 인터페이스)
│       │   ├── hardware.py            # SDS-V01-002 (VideoToolbox 인코더)
│       │   ├── software.py            # SDS-V01-003 (libx265 인코더)
│       │   ├── factory.py             # SDS-V01-004 (컨버터 팩토리)
│       │   └── progress.py            # SDS-V01-005 (FFmpeg 진행률 파싱)
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── codec_detector.py      # SDS-P01-001 (코덱 감지)
│       │   ├── metadata.py            # SDS-P01-002 (ExifTool 메타데이터)
│       │   ├── quality_validator.py   # SDS-P01-003 (품질 검증)
│       │   ├── gps.py                 # SDS-P01-004 (GPS 좌표)
│       │   ├── vmaf_analyzer.py       # SDS-P01-005 (VMAF 분석)
│       │   ├── verification.py        # SDS-P01-006 (출력 검증)
│       │   ├── timestamp.py           # SDS-P01-007 (파일 타임스탬프)
│       │   └── retry_manager.py       # SDS-P01-008 (재시도 로직)
│       ├── automation/
│       │   ├── __init__.py
│       │   ├── service_manager.py     # SDS-A01-001 (launchd 서비스)
│       │   ├── launchd.py             # SDS-A01-002 (plist 생성)
│       │   └── notification.py        # SDS-A01-003 (macOS 알림)
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── statistics_reporter.py # SDS-R01-001 (통계 포맷팅)
│       │   └── batch_reporter.py      # SDS-R01-002 (배치 보고)
│       ├── ui/
│       │   ├── __init__.py
│       │   └── progress.py            # SDS-UI-001 (Rich 진행률 표시)
│       └── utils/
│           ├── __init__.py
│           ├── command_runner.py      # SDS-U01-001 (외부 도구 실행)
│           ├── progress_parser.py     # SDS-U01-002 (FFmpeg 출력 파싱)
│           ├── file_utils.py          # SDS-U01-003 (파일 작업)
│           └── dependency_checker.py  # SDS-U01-004 (시스템 의존성 확인)
├── tests/
│   ├── unit/                          # 단위 테스트 (31개 파일)
│   ├── integration/                   # 통합 테스트
│   └── conftest.py                    # Pytest 픽스처
├── config/
│   ├── default.json                   # 기본 설정
│   └── launchd/                       # 서비스 템플릿
└── scripts/
    ├── install.sh
    └── uninstall.sh
```

### 2.4 의존성 다이어그램

```
                    ┌─────────────┐
                    │    main     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ orchestrator │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  extractor  │ │  converter  │ │  reporter   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  osxphotos  │ │    ffmpeg   │ │  notifier   │
    │   adapter   │ │   adapter   │ │             │
    └─────────────┘ └──────┬──────┘ └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  metadata   │
                    │  processor  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  exiftool   │
                    │   adapter   │
                    └─────────────┘
```

---

## 3. 모듈 상세 설계

### 3.1 Core 모듈 (SDS-C01)

#### SDS-C01-001: Orchestrator 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-C01-001 |
| **모듈명** | Orchestrator |
| **파일** | `src/video_converter/core/orchestrator.py` |
| **SRS 추적** | SRS-701 (CLI 명령 구조) |
| **책임** | 전체 변환 워크플로우 조율 및 상태 관리 |

**클래스 설계**:

```python
class Orchestrator:
    """
    메인 워크플로우 오케스트레이터

    Attributes:
        config: Config - 시스템 설정
        extractor: VideoExtractor - 비디오 추출기
        converter: VideoConverter - 비디오 변환기
        validator: QualityValidator - 품질 검증기
        metadata_manager: MetadataManager - 메타데이터 관리자
        reporter: StatisticsReporter - 통계 리포터
        notifier: MacOSNotifier - 알림 관리자
        history: ConversionHistory - 변환 이력 관리
        _session: ConversionSession - 현재 세션 정보

    Design Patterns:
        - Facade: 복잡한 서브시스템을 단순화된 인터페이스로 제공
        - Template Method: 변환 워크플로우의 기본 골격 정의
    """
```

**핵심 메서드**:

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `run` | `async def run(self, options: RunOptions) -> BatchResult` | 배치 변환 실행 |
| `run_single` | `async def run_single(self, input_path: Path, output_path: Path) -> ConversionResult` | 단일 파일 변환 |
| `get_status` | `def get_status(self) -> ServiceStatus` | 서비스 상태 조회 |
| `get_statistics` | `def get_statistics(self, period: Period) -> Statistics` | 통계 조회 |

**배치 처리 알고리즘**:

```python
async def run(self, options: RunOptions) -> BatchResult:
    """
    배치 변환 실행 알고리즘

    Algorithm:
    1. 세션 초기화
       - 새 세션 UUID 생성
       - 시작 시간 기록
       - 로거 설정

    2. 비디오 스캔
       - extractor.scan_videos() 호출
       - 코덱 필터링 (H.264만)
       - 이미 변환된 항목 제외 (history 조회)

    3. 대상 필터링
       - options.since_date로 날짜 필터
       - options.albums로 앨범 필터
       - options.limit로 개수 제한

    4. 배치 처리 루프
       for video in videos:
           a. 상태 업데이트 (IN_PROGRESS)
           b. 비디오 내보내기 (export_video)
           c. 변환 실행 (converter.convert)
           d. 품질 검증 (validator.validate)
           e. 메타데이터 복원 (metadata_manager.apply)
           f. 원본 처리 (processed 폴더로 이동)
           g. 통계 업데이트

    5. 후처리
       - 보고서 생성
       - 알림 발송
       - 세션 종료 기록

    Time Complexity: O(n) where n = number of videos
    Space Complexity: O(1) per video (스트리밍 처리)
    """
```

**상태 전이 다이어그램**:

```
                    ┌─────────────┐
                    │    IDLE     │
                    └──────┬──────┘
                           │ trigger
                    ┌──────▼──────┐
                    │ INITIALIZING│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  SCANNING   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌─────│ PROCESSING  │─────┐
              │     └──────┬──────┘     │
              │            │            │
        ┌─────▼─────┐     │     ┌──────▼──────┐
        │  ERROR    │     │     │  CANCELLED  │
        └───────────┘     │     └─────────────┘
                    ┌─────▼─────┐
                    │ REPORTING │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │   IDLE    │
                    └───────────┘
```

#### SDS-C01-002: Config Manager 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-C01-002 |
| **모듈명** | ConfigManager |
| **파일** | `src/video_converter/core/config.py` |
| **SRS 추적** | SRS-701 (설정 관리) |

**설정 로딩 우선순위**:

```
Priority (높음 → 낮음):
1. CLI Arguments (--config, --quality, etc.)
2. Environment Variables (VIDEO_CONVERTER_*)
3. Project Config (./video_converter.json)
4. User Config (~/.config/video_converter/config.json)
5. Default Config (내장 기본값)
```

**설정 스키마 검증**:

```python
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "encoding", "paths"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+$"
        },
        "encoding": {
            "type": "object",
            "properties": {
                "mode": {"enum": ["hardware", "software"]},
                "quality": {"type": "integer", "minimum": 1, "maximum": 100},
                "crf": {"type": "integer", "minimum": 0, "maximum": 51},
                "preset": {"enum": ["ultrafast", "superfast", "veryfast",
                                   "faster", "fast", "medium", "slow",
                                   "slower", "veryslow"]}
            }
        },
        # ... 상세 스키마
    }
}
```

---

### 3.2 Extractors 모듈 (SDS-E01)

#### SDS-E01-001: PhotosExtractor 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-E01-001 |
| **모듈명** | PhotosExtractor |
| **파일** | `src/video_converter/extractors/photos_extractor.py` |
| **SRS 추적** | SRS-301 (Photos 스캔), SRS-302 (iCloud 다운로드) |
| **의존성** | osxphotos >= 0.70.0 |

**클래스 설계**:

```python
class PhotosExtractor(VideoExtractor):
    """
    macOS Photos 라이브러리에서 비디오 추출

    Implements:
        VideoExtractor (Abstract Base Class)

    Attributes:
        _db: osxphotos.PhotosDB - Photos 데이터베이스 연결
        _codec_detector: CodecDetector - 코덱 감지기
        _library_path: Path - Photos 라이브러리 경로
        _export_options: ExportOptions - 내보내기 설정

    Thread Safety:
        - PhotosDB는 thread-safe하지 않음
        - 단일 스레드에서만 접근
    """
```

**스캔 알고리즘**:

```python
def scan_videos(
    self,
    filter_codec: Optional[str] = "h264",
    since_date: Optional[datetime] = None,
    albums: Optional[List[str]] = None,
    exclude_converted: bool = True
) -> List[VideoInfo]:
    """
    Photos 라이브러리 스캔 알고리즘

    Algorithm:
    1. PhotosDB 연결
       db = PhotosDB(library_path)

    2. 비디오 쿼리
       videos = db.photos(movies=True)

    3. 필터링 파이프라인
       videos = filter(lambda v: is_video(v), videos)
       if since_date:
           videos = filter(lambda v: v.date >= since_date, videos)
       if albums:
           videos = filter(lambda v: intersects(v.albums, albums), videos)
       if filter_codec:
           videos = filter(lambda v: detect_codec(v.path) == filter_codec, videos)
       if exclude_converted:
           videos = filter(lambda v: not history.is_converted(v.uuid), videos)

    4. VideoInfo 변환
       return [VideoInfo.from_photo_info(v) for v in videos]

    Time Complexity: O(n * k)
        n = 비디오 수
        k = 코덱 감지 시간 (FFprobe 호출)

    Optimization:
        - 코덱 감지 결과 캐싱
        - 병렬 FFprobe 호출 (max 4 concurrent)
    """
```

**iCloud 다운로드 처리**:

```python
async def _download_from_icloud(
    self,
    video: PhotoInfo,
    timeout: int = 600
) -> Path:
    """
    iCloud 비디오 다운로드

    Algorithm:
    1. 다운로드 상태 확인
       if video.hasadjustments:
           # 편집된 버전도 처리
       if not video.path:
           # iCloud 전용 파일

    2. 다운로드 시작
       photo_info.export(
           dest,
           use_photos_export=True,
           download_missing=True
       )

    3. 진행률 모니터링
       while not downloaded:
           check_status()
           if timeout_exceeded:
               raise iCloudTimeoutError

    4. 검증 후 반환
       validate_file_integrity(downloaded_path)
       return downloaded_path

    Error Handling:
        - NetworkError: 재시도 (3회)
        - TimeoutError: 대기 큐에 추가
        - QuotaError: 건너뛰기 및 로깅
    """
```

#### SDS-E01-002: FolderExtractor 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-E01-002 |
| **모듈명** | FolderExtractor |
| **파일** | `src/video_converter/extractors/folder_extractor.py` |
| **SRS 추적** | SRS-602 (폴더 감시) |

**폴더 스캔 알고리즘**:

```python
def scan_videos(
    self,
    filter_codec: Optional[str] = "h264",
    recursive: bool = True,
    extensions: List[str] = [".mp4", ".mov", ".m4v"]
) -> List[VideoInfo]:
    """
    로컬 폴더 스캔

    Algorithm:
    1. 파일 목록 수집
       if recursive:
           files = Path(folder).rglob("*")
       else:
           files = Path(folder).glob("*")

    2. 확장자 필터링
       videos = [f for f in files
                 if f.suffix.lower() in extensions]

    3. 코덱 필터링
       if filter_codec:
           videos = [v for v in videos
                     if codec_detector.detect(v).codec_name == filter_codec]

    4. VideoInfo 생성
       return [VideoInfo.from_path(v) for v in videos]
    """
```

---

### 3.3 Converters 모듈 (SDS-V01)

#### SDS-V01-001: HardwareConverter 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-V01-001 |
| **모듈명** | HardwareConverter |
| **파일** | `src/video_converter/converters/hardware.py` |
| **SRS 추적** | SRS-201 (하드웨어 가속 변환) |
| **의존성** | FFmpeg 5.0+ (hevc_videotoolbox) |

**FFmpeg 명령 구성**:

```python
def _build_command(self, request: ConversionRequest) -> List[str]:
    """
    VideoToolbox 하드웨어 인코딩 명령 구성

    Command Template:
    ffmpeg -y -i <input> \
      -c:v hevc_videotoolbox \
      -q:v <quality> \
      -tag:v hvc1 \
      -c:a copy \
      -map_metadata 0 \
      -movflags use_metadata_tags \
      -progress pipe:1 \
      <output>

    Parameters:
        -c:v hevc_videotoolbox: Apple VideoToolbox H.265 인코더
        -q:v <1-100>: 품질 설정 (낮을수록 고품질, 기본 45)
        -tag:v hvc1: QuickTime 호환 태그
        -c:a copy: 오디오 스트림 재인코딩 없이 복사
        -map_metadata 0: 입력 파일의 모든 메타데이터 복사
        -movflags use_metadata_tags: 커스텀 메타데이터 태그 보존
        -progress pipe:1: stdout으로 진행률 출력
    """
    cmd = ["ffmpeg", "-y"]

    # 입력 설정
    cmd.extend(["-i", str(request.input_path)])

    # 비디오 인코딩 설정
    cmd.extend([
        "-c:v", "hevc_videotoolbox",
        "-q:v", str(request.quality),
        "-tag:v", "hvc1"
    ])

    # 오디오 설정
    cmd.extend(["-c:a", request.audio_mode])

    # 메타데이터 설정
    cmd.extend([
        "-map_metadata", "0",
        "-movflags", "use_metadata_tags"
    ])

    # 진행률 출력
    cmd.extend(["-progress", "pipe:1"])

    # 출력 파일
    cmd.append(str(request.output_path))

    return cmd
```

**변환 실행 알고리즘**:

```python
async def convert(
    self,
    input_path: Path,
    output_path: Path,
    options: Optional[ConversionOptions] = None
) -> ConversionResult:
    """
    하드웨어 가속 변환 실행

    Algorithm:
    1. 사전 검증
       - 입력 파일 존재 확인
       - 출력 디렉토리 생성
       - 디스크 공간 확인 (입력 파일 크기 * 1.5)

    2. FFmpeg 프로세스 시작
       process = await asyncio.create_subprocess_exec(
           *cmd,
           stdout=PIPE,
           stderr=PIPE
       )

    3. 진행률 모니터링 루프
       while process.returncode is None:
           line = await process.stdout.readline()
           progress = parse_progress(line)
           await progress_callback(progress)

    4. 완료 처리
       if process.returncode == 0:
           return ConversionResult(success=True, ...)
       else:
           return ConversionResult(success=False, error=stderr)

    Error Handling:
        - E-201: FFmpeg 실행 실패 → 재시도 (3회)
        - E-202: 디스크 공간 부족 → 즉시 실패
        - E-205: 인코더 초기화 실패 → 소프트웨어 폴백
    """
```

**진행률 파싱**:

```python
def _parse_progress(self, line: str) -> Optional[ProgressInfo]:
    """
    FFmpeg 진행률 출력 파싱

    FFmpeg Progress Output Format:
        frame=375
        fps=45.2
        stream_0_0_q=-1.0
        bitrate=1234.5kbits/s
        total_size=12345678
        out_time_us=12500000
        out_time_ms=12500
        out_time=00:00:12.500000
        dup_frames=0
        drop_frames=0
        speed=3.5x
        progress=continue

    Parsing Strategy:
        1. '=' 기준으로 key-value 분리
        2. out_time_us로 현재 시간 계산
        3. 전체 duration 대비 백분율 계산
        4. speed로 ETA 계산

    Returns:
        ProgressInfo(
            current_time_ms=12500,
            percentage=45.2,
            speed=3.5,
            eta_seconds=120
        )
    """
    if '=' not in line:
        return None

    key, value = line.strip().split('=', 1)

    if key == 'out_time_us':
        current_us = int(value)
        percentage = (current_us / self._total_duration_us) * 100
        return ProgressInfo(percentage=percentage, ...)

    return None
```

#### SDS-V01-002: SoftwareConverter 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-V01-002 |
| **모듈명** | SoftwareConverter |
| **파일** | `src/video_converter/converters/software.py` |
| **SRS 추적** | SRS-202 (소프트웨어 변환) |
| **의존성** | FFmpeg 5.0+ (libx265) |

**CRF 기반 품질 설정**:

```python
CRF_PRESETS = {
    "archival": {"crf": 18, "preset": "slow"},     # 최고 품질
    "high": {"crf": 20, "preset": "slow"},         # 고품질
    "balanced": {"crf": 23, "preset": "medium"},   # 균형 (기본값)
    "fast": {"crf": 26, "preset": "fast"},         # 빠른 처리
    "size": {"crf": 28, "preset": "veryfast"}      # 용량 우선
}

def _build_command(self, request: ConversionRequest) -> List[str]:
    """
    libx265 소프트웨어 인코딩 명령 구성

    Command Template:
    ffmpeg -y -i <input> \
      -c:v libx265 \
      -crf <crf> \
      -preset <preset> \
      -tag:v hvc1 \
      -c:a copy \
      -map_metadata 0 \
      -progress pipe:1 \
      <output>

    CRF (Constant Rate Factor):
        - 0: 무손실 (매우 큰 파일)
        - 18-20: 시각적 무손실
        - 23: 기본값 (균형)
        - 28: 작은 파일 (품질 저하 가시)
        - 51: 최저 품질
    """
```

---

### 3.4 Processors 모듈 (SDS-P01)

#### SDS-P01-001: CodecDetector 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-001 |
| **모듈명** | CodecDetector |
| **파일** | `src/video_converter/processors/codec_detector.py` |
| **SRS 추적** | SRS-101 (비디오 코덱 감지) |
| **의존성** | FFprobe (FFmpeg 포함) |

**코덱 감지 알고리즘**:

```python
def detect(self, video_path: Path) -> CodecInfo:
    """
    FFprobe를 사용한 코덱 감지

    FFprobe Command:
    ffprobe -v error \
      -select_streams v:0 \
      -show_entries stream=codec_name,codec_tag_string \
      -of json \
      <video_path>

    Algorithm:
    1. FFprobe 실행
       result = subprocess.run(cmd, capture_output=True)

    2. JSON 파싱
       data = json.loads(result.stdout)
       codec_name = data['streams'][0]['codec_name']

    3. 코덱 정규화
       normalized = CODEC_ALIASES.get(codec_name.lower(), codec_name)

    4. CodecInfo 생성
       return CodecInfo(
           codec_name=normalized,
           is_h264=normalized in ['h264', 'avc', 'avc1'],
           is_hevc=normalized in ['hevc', 'h265', 'hvc1', 'hev1']
       )

    Performance:
        - 평균 실행 시간: 50-200ms
        - 캐싱 활용 시: < 1ms (같은 파일)

    Caching Strategy:
        - 파일 경로 + mtime 기반 캐시 키
        - LRU 캐시 (최대 1000개 항목)
        - TTL: 무제한 (파일 수정 시 무효화)
    """
```

**코덱 별칭 매핑**:

```python
CODEC_ALIASES = {
    # H.264 / AVC
    'h264': 'h264',
    'avc': 'h264',
    'avc1': 'h264',
    'x264': 'h264',

    # H.265 / HEVC
    'hevc': 'hevc',
    'h265': 'hevc',
    'hvc1': 'hevc',
    'hev1': 'hevc',
    'x265': 'hevc',

    # AV1
    'av1': 'av1',
    'libaom-av1': 'av1',
    'libsvtav1': 'av1',

    # VP9
    'vp9': 'vp9',
    'libvpx-vp9': 'vp9',
}
```

#### SDS-P01-002: MetadataManager 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-002 |
| **모듈명** | MetadataManager |
| **파일** | `src/video_converter/processors/metadata.py` |
| **SRS 추적** | SRS-401 (메타데이터 추출), SRS-402 (메타데이터 검증) |
| **의존성** | ExifTool 12.0+ |

**메타데이터 추출 알고리즘**:

```python
def extract(self, video_path: Path) -> Metadata:
    """
    ExifTool을 사용한 메타데이터 추출

    ExifTool Command:
    exiftool -json -G <video_path>

    Algorithm:
    1. ExifTool 실행
       result = subprocess.run(
           ['exiftool', '-json', '-G', str(video_path)],
           capture_output=True, text=True
       )

    2. JSON 파싱
       data = json.loads(result.stdout)[0]

    3. 주요 필드 매핑
       metadata = Metadata(
           create_date=parse_date(data.get('QuickTime:CreateDate')),
           gps_latitude=parse_gps(data.get('Composite:GPSLatitude')),
           gps_longitude=parse_gps(data.get('Composite:GPSLongitude')),
           make=data.get('QuickTime:Make'),
           model=data.get('QuickTime:Model'),
           duration=parse_duration(data.get('QuickTime:Duration')),
           raw_data=data
       )

    4. GPS 좌표 정규화
       if metadata.gps_latitude:
           metadata.gps_latitude = normalize_gps(metadata.gps_latitude)

    GPS Tag Priority:
        1. Composite:GPSLatitude/GPSLongitude (계산된 값)
        2. QuickTime:GPSCoordinates
        3. Keys:GPSCoordinates
        4. XMP:GPSLatitude/XMP:GPSLongitude
    """
```

**메타데이터 적용 알고리즘**:

```python
def apply(
    self,
    source_path: Path,
    target_path: Path,
    tags: Optional[List[str]] = None
) -> None:
    """
    ExifTool을 사용한 메타데이터 적용

    Phase 1: 전체 메타데이터 복사
    exiftool -overwrite_original \
      -tagsFromFile <source> \
      -all:all \
      <target>

    Phase 2: GPS 명시적 복사 (일부 태그 누락 방지)
    exiftool -overwrite_original \
      -tagsFromFile <source> \
      "-GPS*" \
      <target>

    Phase 3: QuickTime 특수 태그 복사
    exiftool -overwrite_original \
      -tagsFromFile <source> \
      "-QuickTime:CreateDate" \
      "-QuickTime:ModifyDate" \
      <target>

    Phase 4: 파일 시스템 타임스탬프 동기화
    os.utime(target_path, (source_stat.st_atime, source_stat.st_mtime))

    Verification:
        - 적용 후 source와 target 메타데이터 비교
        - GPS 좌표: 소수점 6자리 정확도
        - 날짜: 1초 이내 오차 허용
    """
```

**GPS 좌표 처리**:

```python
def _normalize_gps(self, gps_string: str) -> Optional[float]:
    """
    GPS 좌표 문자열 정규화

    Input Formats:
        "37.5665"                      → 37.5665
        "37 33 59.4"                   → 37.566500
        "37 deg 33' 59.4\" N"          → 37.566500
        "37.5665 N"                    → 37.566500
        "37°33'59.4\"N"                → 37.566500

    Algorithm:
    1. 방향 (N/S/E/W) 추출
    2. 도/분/초 분리
    3. 10진수 변환: degrees + minutes/60 + seconds/3600
    4. 남/서 방향이면 음수

    Precision:
        - 소수점 6자리 유지 (약 0.1m 정밀도)
    """
```

#### SDS-P01-003: QualityValidator 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-003 |
| **모듈명** | QualityValidator |
| **파일** | `src/video_converter/processors/validator.py` |
| **SRS 추적** | SRS-501 (변환 결과 검증) |

**검증 알고리즘**:

```python
def validate(
    self,
    original_path: Path,
    converted_path: Path,
    config: ValidationConfig
) -> ValidationResult:
    """
    4단계 품질 검증 알고리즘

    Step 1: 파일 무결성 검사
        - 파일 존재 확인
        - 파일 크기 > 0
        - FFprobe 파싱 성공
        └── 실패 시: valid=False, reason="integrity"

    Step 2: 속성 비교
        Original          Converted        Tolerance
        ─────────────────────────────────────────────
        resolution        same             exact
        framerate         same             ±0.1 fps
        duration          same             ±1.0 sec
        audio_channels    same             exact
        └── 실패 시: valid=False, reason="properties_mismatch"

    Step 3: 압축률 확인
        ratio = converted_size / original_size

        Normal:   0.20 ≤ ratio ≤ 0.80  → OK
        Warning:  0.15 ≤ ratio < 0.20  → 경고
        Warning:  0.80 < ratio ≤ 0.90  → 경고
        Error:    ratio < 0.15         → 품질 손실 의심
        Error:    ratio > 0.90         → 변환 비효율 의심
        └── 경고만 기록, 실패 처리 안 함

    Step 4: VMAF 측정 (선택적)
        if config.validate_quality:
            vmaf = calculate_vmaf(original, converted)
            if vmaf < config.min_vmaf:  # 기본값 93
                return valid=False, reason="quality"

    Return: ValidationResult(
        valid=True/False,
        integrity_ok=bool,
        properties_match=bool,
        compression_normal=bool,
        vmaf_score=Optional[float],
        errors=[],
        warnings=[]
    )
    """
```

**VMAF 계산**:

```python
def calculate_vmaf(
    self,
    reference_path: Path,
    distorted_path: Path
) -> float:
    """
    FFmpeg libvmaf를 사용한 VMAF 측정

    FFmpeg Command:
    ffmpeg -i <distorted> -i <reference> \
      -lavfi "libvmaf=model=version=vmaf_v0.6.1:log_fmt=json" \
      -f null -

    Algorithm:
    1. FFmpeg 실행 (비디오 전체 비교)
    2. JSON 로그 파싱
    3. VMAF 평균 점수 추출

    Performance:
        - 처리 속도: 실시간의 0.1-0.5배
        - 4K 30분 영상: 1-5시간 소요
        - 따라서 선택적으로만 실행

    Sampling Strategy (대용량 파일):
        - 파일 길이 > 10분: 10% 샘플링
        - 시작, 중간, 끝 구간에서 균등 샘플링
        - 최소 30초 구간 분석
    """
```

#### SDS-P01-004: GPS 핸들러 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-004 |
| **모듈명** | GPSHandler |
| **파일** | `src/video_converter/processors/gps.py` |
| **SRS 추적** | SRS-402 (GPS 좌표 보존) |
| **책임** | GPS 좌표 추출, 적용, 형식 변환 및 검증 |

**GPS 좌표 형식**:

| 형식 | 예시 | 컨테이너 |
|------|------|----------|
| QuickTime (ISO 6709) | `+37.774900-122.419400/` | QuickTime, Keys |
| XMP | `37.774900 N`, `122.419400 W` | XMP 메타데이터 |
| EXIF DMS | `37 deg 46' 30.00"` | EXIF |
| 십진수 | `37.7749`, `-122.4194` | Composite |

**설계**:

```python
@dataclass
class GPSCoordinates:
    """형식 변환을 지원하는 GPS 좌표."""
    latitude: float       # -90 ~ 90
    longitude: float      # -180 ~ 180
    altitude: float | None = None
    accuracy: float | None = None
    source_format: GPSFormat = GPSFormat.DECIMAL

    PRECISION = 6         # ~0.1m 정확도
    TOLERANCE = 0.000001  # 검증 허용 오차

    def to_quicktime(self) -> str:
        """ISO 6709 형식으로 변환: +37.774900-122.419400/"""
        pass

    def to_xmp(self) -> tuple[str, str]:
        """XMP 형식으로 변환: ('37.774900 N', '122.419400 W')"""
        pass

    def to_exif_dms(self) -> tuple[str, str, str, str]:
        """EXIF DMS 형식으로 변환."""
        pass

    def matches(self, other: GPSCoordinates, tolerance: float | None = None) -> bool:
        """허용 오차 내에서 좌표 비교."""
        pass

    def distance_to(self, other: GPSCoordinates) -> float:
        """Haversine 공식을 사용하여 거리(미터) 계산."""
        pass

class GPSHandler:
    """비디오 변환 중 GPS 좌표 보존 처리."""

    def extract(self, path: Path) -> GPSCoordinates | None:
        """모든 형식 위치에서 GPS 추출."""
        pass

    def apply(self, path: Path, coords: GPSCoordinates) -> bool:
        """여러 형식으로 GPS 좌표 적용."""
        pass

    def copy(self, source: Path, dest: Path) -> bool:
        """원본에서 대상으로 GPS 데이터 복사."""
        pass

    def verify(self, original: Path, converted: Path) -> GPSVerificationResult:
        """허용 오차 내에서 GPS 보존 검증."""
        pass
```

#### SDS-P01-005: Photos 비디오 필터 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-005 |
| **모듈명** | PhotosVideoFilter |
| **파일** | `src/video_converter/extractors/photos_extractor.py` |
| **SRS 추적** | SRS-302 (비디오 필터링) |
| **책임** | H.264 변환 후보 비디오를 Photos 라이브러리에서 필터링 |

**필터 기준**:

| 기준 | 포함 | 제외 |
|------|------|------|
| 코덱 | H.264, AVC, AVC1, x264 | HEVC, H.265, hvc1, hev1, x265, VP9, AV1 |
| 앨범 | 사용자 지정 | Screenshots, Bursts, Slo-mo (기본값) |
| 가용성 | 로컬 파일만 | iCloud 전용 파일 |
| 유효성 | 유효한 비디오 파일 | 손상되거나 유효하지 않은 파일 |

**설계**:

```python
@dataclass
class LibraryStats:
    """Photos 라이브러리의 비디오 통계."""
    total: int = 0
    h264: int = 0
    hevc: int = 0
    other: int = 0
    in_cloud: int = 0
    total_size_h264: int = 0

    @property
    def estimated_savings(self) -> int:
        """H.265 변환으로 약 50% 절감 추정."""
        return int(self.total_size_h264 * 0.5)

class PhotosVideoFilter:
    """변환 후보 비디오를 Photos 라이브러리에서 필터링."""

    DEFAULT_EXCLUDE_ALBUMS = {"Screenshots", "Bursts", "Slo-mo"}

    def __init__(
        self,
        library: PhotosLibrary,
        include_albums: list[str] | None = None,
        exclude_albums: list[str] | None = None,
    ) -> None:
        """앨범 설정으로 필터 초기화."""
        pass

    def get_conversion_candidates(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[PhotosVideoInfo]:
        """변환이 필요한 H.264 비디오 조회."""
        pass

    def get_stats(self) -> LibraryStats:
        """코덱 분포를 포함한 라이브러리 통계 조회."""
        pass
```

#### SDS-P01-006: 비디오 내보내기 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-P01-006 |
| **모듈명** | VideoExporter |
| **파일** | `src/video_converter/extractors/photos_extractor.py` |
| **SRS 추적** | SRS-303 (비디오 내보내기) |
| **책임** | 변환을 위해 Photos 라이브러리에서 임시 디렉토리로 비디오 내보내기 |

**기능**:

| 기능 | 설명 |
|------|------|
| 진행률 추적 | 대용량 파일 복사 진행률 콜백 지원 (0.0-1.0) |
| 메타데이터 보존 | 수정 시간을 보존하여 파일 복사 |
| 안전한 정리 | 관리되는 임시 디렉토리 내의 파일만 삭제 |
| 컨텍스트 관리자 | `with` 문으로 자동 정리 지원 |
| iCloud 처리 | 클라우드 전용 비디오에 대해 `VideoNotAvailableError` 발생 |

**설계**:

```python
class VideoExporter:
    """Photos 라이브러리에서 임시 디렉토리로 비디오 내보내기."""

    COPY_BUFFER_SIZE = 1024 * 1024  # 1 MB

    def __init__(self, temp_dir: Path | None = None) -> None:
        """선택적 사용자 정의 임시 디렉토리로 초기화."""
        pass

    def export(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """진행률 추적과 함께 임시 디렉토리로 비디오 내보내기."""
        pass

    def cleanup(self, path: Path) -> bool:
        """단일 내보낸 파일 제거 (temp_dir 내의 파일만)."""
        pass

    def cleanup_all(self) -> int:
        """모든 내보낸 파일과 소유한 경우 임시 디렉토리 제거."""
        pass
```

**오류 클래스**:

| 예외 | 설명 |
|------|------|
| `VideoNotAvailableError` | 비디오가 iCloud 전용이고 다운로드되지 않은 경우 발생 |
| `ExportError` | 내보내기 실패 시 발생 (권한 거부, 디스크 공간 부족 등) |

---

### 3.5 Automation 모듈 (SDS-A01)

#### SDS-A01-001: LaunchdManager 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-A01-001 |
| **모듈명** | LaunchdManager |
| **파일** | `src/video_converter/automation/launchd.py` |
| **SRS 추적** | SRS-601 (스케줄 기반 실행), SRS-602 (폴더 감시) |

**plist 생성 알고리즘**:

```python
def _generate_plist(self, config: AutomationConfig) -> str:
    """
    launchd plist 파일 생성

    Template Structure:
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
      "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <!-- 서비스 식별자 -->
        <key>Label</key>
        <string>com.user.videoconverter</string>

        <!-- 실행 명령 -->
        <key>ProgramArguments</key>
        <array>
            <string>/usr/bin/python3</string>
            <string>{INSTALL_DIR}/main.py</string>
            <string>run</string>
            <string>--mode</string>
            <string>photos</string>
        </array>

        <!-- 스케줄 (config.schedule_hour, schedule_minute) -->
        <key>StartCalendarInterval</key>
        <dict>
            <key>Hour</key>
            <integer>{config.schedule_hour}</integer>
            <key>Minute</key>
            <integer>{config.schedule_minute}</integer>
        </dict>

        <!-- 폴더 감시 (optional) -->
        <key>WatchPaths</key>
        <array>
            <string>{config.watch_folder}</string>
        </array>

        <!-- 로그 경로 -->
        <key>StandardOutPath</key>
        <string>{LOG_DIR}/stdout.log</string>
        <key>StandardErrorPath</key>
        <string>{LOG_DIR}/stderr.log</string>

        <!-- 환경 변수 -->
        <key>EnvironmentVariables</key>
        <dict>
            <key>PATH</key>
            <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
            <key>LANG</key>
            <string>en_US.UTF-8</string>
        </dict>

        <!-- 실행 제어 -->
        <key>RunAtLoad</key>
        <false/>
        <key>ThrottleInterval</key>
        <integer>30</integer>
    </dict>
    </plist>
    """
```

**서비스 관리 명령**:

```python
class LaunchdManager:
    PLIST_DIR = Path.home() / "Library/LaunchAgents"
    LABEL = "com.user.videoconverter"
    PLIST_FILE = f"{LABEL}.plist"

    def install(self, config: AutomationConfig) -> None:
        """
        서비스 설치

        Steps:
        1. plist 파일 생성
        2. LaunchAgents 디렉토리에 복사
        3. launchctl load 실행
        4. 설치 확인
        """
        plist_content = self._generate_plist(config)
        plist_path = self.PLIST_DIR / self.PLIST_FILE
        plist_path.write_text(plist_content)

        subprocess.run(["launchctl", "load", str(plist_path)], check=True)

    def uninstall(self) -> None:
        """
        서비스 제거

        Steps:
        1. launchctl unload 실행
        2. plist 파일 삭제
        """
        plist_path = self.PLIST_DIR / self.PLIST_FILE
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
        plist_path.unlink(missing_ok=True)

    def status(self) -> ServiceStatus:
        """
        서비스 상태 조회

        Command: launchctl list | grep {LABEL}

        Output Parsing:
            - 첫 번째 컬럼: PID (- 이면 미실행)
            - 두 번째 컬럼: 마지막 종료 코드
            - 세 번째 컬럼: 레이블

        Returns:
            ServiceStatus(
                installed=True/False,
                running=True/False,
                last_exit_code=int,
                next_run_time=datetime
            )
        """
```

---

### 3.6 Reporters 모듈 (SDS-R01)

#### SDS-R01-001: MacOSNotifier 설계

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-R01-001 |
| **모듈명** | MacOSNotifier |
| **파일** | `src/video_converter/reporters/notifier.py` |
| **SRS 추적** | SRS-603 (macOS 알림) |

**알림 발송 구현**:

```python
def notify(
    self,
    title: str,
    message: str,
    subtitle: Optional[str] = None,
    sound: bool = True
) -> None:
    """
    macOS Notification Center 알림 발송

    AppleScript Implementation:
    osascript -e 'display notification "{message}"
      with title "{title}"
      subtitle "{subtitle}"
      sound name "{sound_name}"'

    Alternative: pyobjc (더 안정적)
    from Foundation import NSUserNotification, NSUserNotificationCenter

    Algorithm:
    1. 알림 내용 구성
    2. AppleScript 명령 생성
    3. osascript 실행
    4. 성공/실패 로깅
    """
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    if subtitle:
        script = f'''
        display notification "{message}" with title "{title}" subtitle "{subtitle}"
        '''
    if sound:
        script += ' sound name "Ping"'

    subprocess.run(["osascript", "-e", script], check=False)
```

**알림 메시지 템플릿**:

```python
NOTIFICATION_TEMPLATES = {
    "completion": {
        "title": "🎬 Video Converter",
        "message": "변환 완료: {count}개 영상, {saved} 절약",
    },
    "error": {
        "title": "⚠️ Video Converter",
        "message": "변환 실패: {filename}",
    },
    "daily_summary": {
        "title": "📊 Video Converter",
        "message": "오늘 {count}개 변환, 총 {saved} 절약",
    }
}
```

---

## 4. 클래스 상세 설계

### 4.1 데이터 클래스 (Data Classes)

#### VideoInfo

```python
@dataclass
class VideoInfo:
    """
    비디오 정보 데이터 클래스

    SRS Reference: SRS-301 (Photos 스캔)
    """
    uuid: str                                # Photos 내부 UUID 또는 파일 해시
    original_filename: str                   # 원본 파일명
    path: Optional[Path]                     # 로컬 파일 경로 (iCloud만 있으면 None)
    codec: str                               # 비디오 코덱 (h264, hevc 등)
    duration: float                          # 재생 시간 (초)
    size: int                                # 파일 크기 (bytes)
    width: int                               # 가로 해상도
    height: int                              # 세로 해상도
    fps: float                               # 프레임레이트
    creation_date: datetime                  # 촬영/생성 날짜
    location: Optional[Tuple[float, float]]  # (위도, 경도)
    albums: List[str]                        # 소속 앨범 목록
    is_in_icloud: bool                       # iCloud 전용 여부
    is_favorite: bool                        # 즐겨찾기 여부
    source: str                              # "photos" | "folder"

    @property
    def resolution(self) -> str:
        """해상도 문자열 (예: "3840x2160")"""
        return f"{self.width}x{self.height}"

    @property
    def is_4k(self) -> bool:
        """4K 해상도 여부"""
        return self.width >= 3840 or self.height >= 2160

    @classmethod
    def from_photo_info(cls, photo: osxphotos.PhotoInfo) -> "VideoInfo":
        """osxphotos.PhotoInfo에서 생성"""
        ...

    @classmethod
    def from_path(cls, path: Path) -> "VideoInfo":
        """파일 경로에서 생성 (FFprobe 사용)"""
        ...
```

#### ConversionResult

```python
@dataclass
class ConversionResult:
    """
    변환 결과 데이터 클래스

    SRS Reference: SRS-201, SRS-202 (비디오 변환)
    """
    success: bool                           # 성공 여부
    input_path: Path                        # 입력 파일 경로
    output_path: Optional[Path]             # 출력 파일 경로 (성공 시)
    original_size: int                      # 원본 크기 (bytes)
    converted_size: Optional[int]           # 변환된 크기 (bytes)
    compression_ratio: Optional[float]      # 압축률 (0.0-1.0)
    duration_seconds: float                 # 변환 소요 시간 (초)
    speed_ratio: Optional[float]            # 실시간 대비 속도 (예: 3.5x)
    encoding_mode: str                      # "hardware" | "software"
    vmaf_score: Optional[float]             # VMAF 점수 (측정 시)
    error_code: Optional[str]               # 에러 코드 (실패 시)
    error_message: Optional[str]            # 에러 메시지 (실패 시)
    started_at: datetime                    # 시작 시간
    completed_at: datetime                  # 완료 시간

    @property
    def saved_bytes(self) -> int:
        """절약된 바이트 수"""
        if self.converted_size is None:
            return 0
        return self.original_size - self.converted_size

    @property
    def saved_percentage(self) -> float:
        """절약 비율 (%)"""
        if self.original_size == 0:
            return 0.0
        return (self.saved_bytes / self.original_size) * 100
```

#### Metadata

```python
@dataclass
class Metadata:
    """
    비디오 메타데이터 데이터 클래스

    SRS Reference: SRS-401 (메타데이터 추출)
    """
    # 시간 정보
    create_date: Optional[datetime]
    modify_date: Optional[datetime]

    # 위치 정보
    gps_latitude: Optional[float]           # 위도 (소수점)
    gps_longitude: Optional[float]          # 경도 (소수점)
    gps_altitude: Optional[float]           # 고도 (미터)

    # 카메라 정보
    make: Optional[str]                     # 제조사 (Apple)
    model: Optional[str]                    # 모델 (iPhone 15 Pro)
    software: Optional[str]                 # 소프트웨어 버전

    # 비디오 정보
    duration: Optional[float]               # 재생 시간 (초)
    width: Optional[int]                    # 가로 해상도
    height: Optional[int]                   # 세로 해상도
    frame_rate: Optional[float]             # 프레임레이트
    bit_rate: Optional[int]                 # 비트레이트 (bps)

    # 원본 데이터
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_gps(self) -> bool:
        """GPS 정보 존재 여부"""
        return self.gps_latitude is not None and self.gps_longitude is not None

    @property
    def gps_coordinates(self) -> Optional[Tuple[float, float]]:
        """GPS 좌표 튜플"""
        if self.has_gps:
            return (self.gps_latitude, self.gps_longitude)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

    @classmethod
    def from_exiftool_json(cls, data: Dict[str, Any]) -> "Metadata":
        """ExifTool JSON 출력에서 생성"""
        return cls(
            create_date=cls._parse_date(data.get('QuickTime:CreateDate')),
            modify_date=cls._parse_date(data.get('QuickTime:ModifyDate')),
            gps_latitude=cls._parse_gps(data.get('Composite:GPSLatitude')),
            gps_longitude=cls._parse_gps(data.get('Composite:GPSLongitude')),
            gps_altitude=data.get('Composite:GPSAltitude'),
            make=data.get('QuickTime:Make'),
            model=data.get('QuickTime:Model'),
            software=data.get('QuickTime:Software'),
            duration=cls._parse_duration(data.get('QuickTime:Duration')),
            width=data.get('QuickTime:ImageWidth'),
            height=data.get('QuickTime:ImageHeight'),
            frame_rate=data.get('QuickTime:VideoFrameRate'),
            bit_rate=data.get('QuickTime:AvgBitrate'),
            raw_data=data
        )
```

#### ValidationResult

```python
@dataclass
class ValidationResult:
    """
    검증 결과 데이터 클래스

    SRS Reference: SRS-501 (변환 결과 검증)
    """
    valid: bool                             # 최종 검증 통과 여부
    integrity_ok: bool                      # 파일 무결성 통과
    properties_match: bool                  # 속성 일치
    compression_normal: bool                # 압축률 정상 범위
    metadata_preserved: bool                # 메타데이터 보존
    vmaf_score: Optional[float]             # VMAF 점수 (측정 시)
    compression_ratio: float                # 실제 압축률
    errors: List[str]                       # 에러 목록
    warnings: List[str]                     # 경고 목록
    duration_seconds: float                 # 검증 소요 시간

    @property
    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """경고 존재 여부"""
        return len(self.warnings) > 0
```

---

## 5. 데이터베이스 설계

### 5.1 데이터베이스 개요

| 항목 | 내용 |
|------|------|
| **SDS ID** | SDS-D01-001 |
| **DBMS** | SQLite 3 |
| **파일 위치** | `~/.config/video_converter/history.db` |
| **SRS 추적** | SRS-301 (변환 기록), SRS-801 (원본 보존) |

### 5.2 테이블 설계

#### conversion_history 테이블

```sql
-- 변환 이력 테이블
-- SDS-D01-002
CREATE TABLE conversion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 비디오 식별 정보
    video_uuid TEXT NOT NULL,               -- Photos UUID 또는 파일 해시
    original_filename TEXT NOT NULL,        -- 원본 파일명
    original_path TEXT NOT NULL,            -- 원본 파일 경로
    output_path TEXT NOT NULL,              -- 출력 파일 경로

    -- 크기 정보
    original_size INTEGER NOT NULL,         -- 원본 크기 (bytes)
    converted_size INTEGER NOT NULL,        -- 변환된 크기 (bytes)
    compression_ratio REAL NOT NULL,        -- 압축률 (0.0-1.0)

    -- 변환 설정
    conversion_mode TEXT NOT NULL,          -- 'hardware' | 'software'
    quality_setting INTEGER,                -- 품질 설정값
    crf_setting INTEGER,                    -- CRF 설정값 (SW 모드)

    -- 품질 정보
    vmaf_score REAL,                        -- VMAF 점수 (측정 시)

    -- 시간 정보
    started_at TIMESTAMP NOT NULL,          -- 변환 시작 시간
    completed_at TIMESTAMP NOT NULL,        -- 변환 완료 시간
    duration_seconds REAL NOT NULL,         -- 소요 시간 (초)

    -- 상태 정보
    status TEXT NOT NULL,                   -- 'success' | 'failed'
    error_code TEXT,                        -- 에러 코드 (실패 시)
    error_message TEXT,                     -- 에러 메시지 (실패 시)

    -- 메타 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_video_uuid ON conversion_history(video_uuid);
CREATE INDEX idx_status ON conversion_history(status);
CREATE INDEX idx_completed_at ON conversion_history(completed_at);
CREATE INDEX idx_original_path ON conversion_history(original_path);

-- 트리거: updated_at 자동 갱신
CREATE TRIGGER update_conversion_history_timestamp
    AFTER UPDATE ON conversion_history
BEGIN
    UPDATE conversion_history SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
```

#### conversion_sessions 테이블

```sql
-- 변환 세션 테이블 (배치 작업 단위)
-- SDS-D01-003
CREATE TABLE conversion_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 세션 식별
    session_uuid TEXT NOT NULL UNIQUE,      -- 세션 UUID

    -- 시간 정보
    started_at TIMESTAMP NOT NULL,          -- 세션 시작 시간
    completed_at TIMESTAMP,                 -- 세션 완료 시간

    -- 통계 정보
    total_videos INTEGER NOT NULL,          -- 총 비디오 수
    successful INTEGER DEFAULT 0,           -- 성공 수
    failed INTEGER DEFAULT 0,               -- 실패 수
    skipped INTEGER DEFAULT 0,              -- 건너뛴 수

    -- 용량 정보
    total_original_size INTEGER DEFAULT 0,  -- 총 원본 크기
    total_converted_size INTEGER DEFAULT 0, -- 총 변환 크기

    -- 상태 정보
    status TEXT NOT NULL,                   -- 'running' | 'completed' | 'failed' | 'cancelled'
    error_message TEXT,                     -- 세션 레벨 에러 메시지

    -- 설정 스냅샷
    config_snapshot TEXT,                   -- JSON 형태의 설정 스냅샷

    -- 메타 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_session_uuid ON conversion_sessions(session_uuid);
CREATE INDEX idx_session_status ON conversion_sessions(status);
CREATE INDEX idx_session_started_at ON conversion_sessions(started_at);
```

#### pending_queue 테이블

```sql
-- 대기 큐 테이블 (iCloud 다운로드 대기 등)
-- SDS-D01-004
CREATE TABLE pending_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 비디오 정보
    video_uuid TEXT NOT NULL,
    original_path TEXT NOT NULL,

    -- 대기 사유
    reason TEXT NOT NULL,                   -- 'icloud_download' | 'retry' | 'resource_limit'
    retry_count INTEGER DEFAULT 0,          -- 재시도 횟수
    max_retries INTEGER DEFAULT 3,          -- 최대 재시도 횟수

    -- 시간 정보
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_attempt_at TIMESTAMP,              -- 다음 시도 예정 시간
    last_attempt_at TIMESTAMP,              -- 마지막 시도 시간

    -- 상태 정보
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'processing' | 'completed' | 'failed'
    last_error TEXT,                        -- 마지막 에러 메시지

    UNIQUE(video_uuid)
);

-- 인덱스
CREATE INDEX idx_pending_status ON pending_queue(status);
CREATE INDEX idx_pending_next_attempt ON pending_queue(next_attempt_at);
```

### 5.3 ER 다이어그램

```
┌─────────────────────────┐       ┌─────────────────────────┐
│   conversion_sessions    │       │   conversion_history    │
├─────────────────────────┤       ├─────────────────────────┤
│ PK session_uuid         │───┐   │ PK id                   │
│    started_at           │   │   │ FK session_uuid         │◀──┐
│    completed_at         │   │   │    video_uuid           │   │
│    total_videos         │   │   │    original_path        │   │
│    successful           │   └──▶│    output_path          │   │
│    failed               │       │    original_size        │   │
│    skipped              │       │    converted_size       │   │
│    status               │       │    status               │   │
└─────────────────────────┘       └─────────────────────────┘   │
                                                                 │
┌─────────────────────────┐                                     │
│     pending_queue       │                                     │
├─────────────────────────┤                                     │
│ PK id                   │                                     │
│    video_uuid           │─────────────────────────────────────┘
│    reason               │       (video_uuid로 참조 가능)
│    retry_count          │
│    status               │
└─────────────────────────┘
```

### 5.4 Database Access Layer

```python
class ConversionHistory:
    """
    변환 이력 데이터 접근 계층

    SDS ID: SDS-D01-005
    SRS Reference: SRS-301
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._ensure_tables()

    def is_converted(self, video_uuid: str) -> bool:
        """
        이미 변환된 비디오인지 확인

        Query:
        SELECT COUNT(*) FROM conversion_history
        WHERE video_uuid = ? AND status = 'success'
        """

    def mark_converted(
        self,
        video_uuid: str,
        result: ConversionResult
    ) -> None:
        """
        변환 완료 기록

        Insert into conversion_history
        """

    def get_statistics(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> Statistics:
        """
        통계 조회

        Query:
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(original_size) as total_original,
            SUM(converted_size) as total_converted
        FROM conversion_history
        WHERE completed_at BETWEEN ? AND ?
        """

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[ConversionRecord]:
        """
        변환 이력 조회

        Query:
        SELECT * FROM conversion_history
        WHERE status = COALESCE(?, status)
        ORDER BY completed_at DESC
        LIMIT ? OFFSET ?
        """
```

---

## 6. 인터페이스 설계

### 6.1 CLI 인터페이스 (SDS-I01)

#### SDS-I01-001: CLI 명령 구조

```
video-converter <command> [options] [arguments]

Commands:
├── convert        단일 파일 변환
├── run            배치 변환 실행
├── scan           변환 대상 스캔 (변환 없이)
├── status         서비스 상태 확인
├── stats          변환 통계 조회
├── config         설정 관리
│   ├── show       현재 설정 표시
│   ├── set        설정값 변경
│   └── reset      기본값으로 초기화
├── install        서비스 설치
├── uninstall      서비스 제거
├── start          서비스 시작
├── stop           서비스 중지
└── version        버전 정보

Global Options:
  -c, --config PATH     설정 파일 경로 지정
  -v, --verbose         상세 로그 출력
  -q, --quiet           최소 출력 모드
  --log-file PATH       로그 파일 경로
  --no-color            컬러 출력 비활성화
  -h, --help            도움말 표시
```

#### SDS-I01-002: convert 명령 상세

```python
@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('-m', '--mode', type=click.Choice(['hardware', 'software']),
              default='hardware', help='인코딩 모드')
@click.option('-q', '--quality', type=int, default=45,
              help='품질 설정 (hardware: 1-100)')
@click.option('--crf', type=int, default=23,
              help='CRF 설정 (software: 0-51)')
@click.option('--preset', type=click.Choice(['fast', 'medium', 'slow']),
              default='medium', help='인코딩 프리셋')
@click.option('--no-metadata', is_flag=True,
              help='메타데이터 복사 안 함')
@click.option('--validate', is_flag=True,
              help='변환 후 품질 검증')
def convert(input_path, output_path, mode, quality, crf, preset,
            no_metadata, validate):
    """
    단일 파일 변환

    Examples:
        video-converter convert input.mp4 output.mp4
        video-converter convert input.mp4 output.mp4 -m hardware -q 45
        video-converter convert input.mp4 output.mp4 -m software --crf 20
    """
```

#### SDS-I01-003: run 명령 상세

```python
@cli.command()
@click.option('--mode', type=click.Choice(['photos', 'folder']),
              default='photos', help='소스 모드')
@click.option('--folder', type=click.Path(exists=True),
              help='폴더 모드 시 대상 폴더')
@click.option('--since', type=click.DateTime(formats=['%Y-%m-%d']),
              help='이 날짜 이후 비디오만')
@click.option('--album', multiple=True,
              help='특정 앨범만 (여러 개 지정 가능)')
@click.option('--dry-run', is_flag=True,
              help='실제 변환 없이 시뮬레이션')
@click.option('--limit', type=int, default=0,
              help='최대 처리 개수 (0=무제한)')
def run(mode, folder, since, album, dry_run, limit):
    """
    배치 변환 실행

    Examples:
        video-converter run
        video-converter run --mode photos --since 2024-01-01
        video-converter run --mode folder --folder ~/Videos/ToConvert
        video-converter run --dry-run --limit 5
    """
```

### 6.2 출력 포맷 설계

#### 진행률 표시

```
Converting: vacation_2024.mp4
[████████████░░░░░░░░] 60% | 1.2GB → 540MB | ETA: 1:45 | Speed: 3.5x

Format Specification:
├── 파일명: 최대 50자, 초과 시 ...으로 축약
├── 프로그레스 바: 20칸 (█ = 완료, ░ = 미완료)
├── 퍼센트: 정수 (0-100%)
├── 크기: 원본 → 현재 (자동 단위: KB/MB/GB)
├── ETA: mm:ss 또는 h:mm:ss
└── Speed: 소수점 1자리 (예: 3.5x)
```

#### 완료 요약

```
╭─────────────────────────────────────────────────╮
│             변환 완료 보고서                       │
├─────────────────────────────────────────────────┤
│  처리 영상:     15개                              │
│  성공:          14개                              │
│  실패:          1개                               │
│  건너뜀:        3개 (이미 HEVC)                   │
├─────────────────────────────────────────────────┤
│  원본 크기:     35.2 GB                           │
│  변환 크기:     15.8 GB                           │
│  절약 공간:     19.4 GB (55%)                     │
├─────────────────────────────────────────────────┤
│  총 소요 시간:  45분 32초                          │
│  평균 속도:     3.2x 실시간                        │
╰─────────────────────────────────────────────────╯
```

#### 에러 표시

```
❌ Error: vacation_corrupted.mp4
   코드: E-203
   원인: Invalid data found when processing input
   해결: 파일이 손상되었습니다. 원본 확인 필요
   위치: ~/Videos/Failed/vacation_corrupted.mp4
```

---

## 7. 에러 처리 설계

### 7.1 에러 분류 체계

| SDS ID | 에러 코드 | 분류 | 설명 | 재시도 | SRS 추적 |
|--------|----------|------|------|--------|----------|
| SDS-E01-001 | E-101 | 입력 오류 | 파일 미존재 | No | SRS-101 |
| SDS-E01-002 | E-102 | 입력 오류 | FFprobe 실행 실패 | Yes | SRS-101 |
| SDS-E01-003 | E-103 | 입력 오류 | 비디오 스트림 없음 | No | SRS-101 |
| SDS-E01-004 | E-104 | 입력 오류 | 알 수 없는 코덱 | No | SRS-101 |
| SDS-E02-001 | E-201 | 변환 오류 | FFmpeg 실행 실패 | Yes | SRS-201 |
| SDS-E02-002 | E-202 | 변환 오류 | 디스크 공간 부족 | No | SRS-201 |
| SDS-E02-003 | E-203 | 변환 오류 | 입력 파일 손상 | No | SRS-201 |
| SDS-E02-004 | E-204 | 변환 오류 | 출력 파일 생성 실패 | Yes | SRS-201 |
| SDS-E02-005 | E-205 | 변환 오류 | 인코더 초기화 실패 | Yes | SRS-201 |
| SDS-E03-001 | E-301 | Photos 오류 | Photos 접근 거부 | No | SRS-301 |
| SDS-E03-002 | E-302 | Photos 오류 | iCloud 다운로드 실패 | Yes | SRS-302 |
| SDS-E04-001 | E-401 | 메타데이터 오류 | 추출 실패 | Yes | SRS-401 |
| SDS-E04-002 | E-402 | 메타데이터 오류 | 적용 실패 | Yes | SRS-401 |
| SDS-E05-001 | E-501 | 검증 오류 | 무결성 검사 실패 | Yes | SRS-501 |
| SDS-E05-002 | E-502 | 검증 오류 | 속성 불일치 | No | SRS-501 |
| SDS-E05-003 | E-503 | 검증 오류 | VMAF 기준 미달 | No | SRS-501 |
| SDS-E06-001 | E-601 | 자동화 오류 | launchd 등록 실패 | No | SRS-601 |

### 7.2 예외 클래스 계층

```python
class VideoConverterError(Exception):
    """모든 Video Converter 예외의 기본 클래스"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class RetryableError(VideoConverterError):
    """재시도 가능한 에러"""
    pass


class PermanentError(VideoConverterError):
    """영구적 에러 (재시도 불가)"""
    pass


# 입력 오류
class FileNotFoundError(PermanentError):
    """E-101: 파일 미존재"""
    pass

class FFprobeError(RetryableError):
    """E-102: FFprobe 실행 실패"""
    pass

class NoVideoStreamError(PermanentError):
    """E-103: 비디오 스트림 없음"""
    pass


# 변환 오류
class FFmpegError(RetryableError):
    """E-201: FFmpeg 실행 실패"""
    pass

class DiskSpaceError(PermanentError):
    """E-202: 디스크 공간 부족"""
    pass

class CorruptedFileError(PermanentError):
    """E-203: 입력 파일 손상"""
    pass

class EncoderInitError(RetryableError):
    """E-205: 인코더 초기화 실패"""
    pass


# Photos 오류
class PhotosAccessDeniedError(PermanentError):
    """E-301: Photos 접근 거부"""
    pass

class iCloudDownloadError(RetryableError):
    """E-302: iCloud 다운로드 실패"""
    pass
```

### 7.3 재시도 정책

```python
@dataclass
class RetryPolicy:
    """
    재시도 정책

    SDS ID: SDS-E07-001
    SRS Reference: SRS-802
    """
    max_retries: int = 3               # 최대 재시도 횟수
    base_delay: float = 5.0            # 기본 대기 시간 (초)
    max_delay: float = 60.0            # 최대 대기 시간 (초)
    exponential_base: float = 2.0      # 지수 백오프 기준

    def get_delay(self, attempt: int) -> float:
        """
        재시도 대기 시간 계산 (지수 백오프)

        Formula: delay = min(base_delay * (exponential_base ^ attempt), max_delay)

        Examples:
            attempt 0: 5.0 * (2.0 ^ 0) = 5.0초
            attempt 1: 5.0 * (2.0 ^ 1) = 10.0초
            attempt 2: 5.0 * (2.0 ^ 2) = 20.0초
            attempt 3: min(40.0, 60.0) = 40.0초
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, error: VideoConverterError) -> bool:
        """
        재시도 여부 결정

        Logic:
        1. 재시도 가능한 에러인가?
        2. 최대 재시도 횟수 초과하지 않았는가?
        """
        if not isinstance(error, RetryableError):
            return False
        return attempt < self.max_retries
```

### 7.4 에러 처리 플로우

```
                    ┌─────────────┐
                    │  작업 시작   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   실행      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  에러 발생?  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │No          │Yes         │
              │            │            │
       ┌──────▼──────┐ ┌───▼───────────▼───┐
       │  성공 처리   │ │   에러 분류        │
       └─────────────┘ └───────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │ Retryable   │  │ Permanent   │  │  Unknown    │
       │   Error     │  │   Error     │  │   Error     │
       └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
              │                │                │
       ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │ 재시도 < 3?  │  │  로깅       │  │  로깅       │
       └──────┬──────┘  │  실패 폴더   │  │  1회 재시도 │
              │         └─────────────┘  └──────┬──────┘
         ┌────┴────┐                            │
         │Yes      │No                   ┌──────▼──────┐
         │         │                     │ 성공?       │
    ┌────▼────┐ ┌──▼──┐                  └──────┬──────┘
    │ 대기    │ │실패 │                   Yes│  │No
    │ 재시도  │ │처리 │                      │  │
    └────┬────┘ └─────┘                      │  ▼
         │                                   │ 실패 처리
         └──────────────────┐                │
                            │                │
                     ┌──────▼──────┐         │
                     │   실행      │◀────────┘
                     └─────────────┘
```

---

## 8. 보안 설계

### 8.1 보안 요구사항 매핑

| SDS ID | 보안 영역 | 구현 방법 | SRS 추적 |
|--------|----------|----------|----------|
| SDS-S01-001 | Photos 접근 제어 | 읽기 전용 접근 | SRS-NFR-501 |
| SDS-S01-002 | 임시 파일 보안 | 자동 삭제, 0600 권한 | SRS-NFR-502 |
| SDS-S01-003 | 설정 파일 보안 | 사용자 홈, 0600 권한 | SRS-NFR-503 |
| SDS-S01-004 | 로그 개인정보 | 경로 해시화, 파일명만 | - |
| SDS-S01-005 | 외부 통신 차단 | 네트워크 접근 없음 | - |

### 8.2 파일 권한 설계

```python
class FilePermissions:
    """파일 권한 관리"""

    # 권한 상수
    CONFIG_FILE_MODE = 0o600      # rw-------
    LOG_FILE_MODE = 0o644         # rw-r--r--
    TEMP_FILE_MODE = 0o600        # rw-------
    OUTPUT_FILE_MODE = 0o644      # rw-r--r--

    @staticmethod
    def secure_config_file(path: Path) -> None:
        """설정 파일 권한 설정"""
        os.chmod(path, FilePermissions.CONFIG_FILE_MODE)

    @staticmethod
    def create_temp_file() -> Path:
        """보안 임시 파일 생성"""
        fd, path = tempfile.mkstemp(prefix='vc_', suffix='.tmp')
        os.fchmod(fd, FilePermissions.TEMP_FILE_MODE)
        os.close(fd)
        return Path(path)
```

### 8.3 임시 파일 관리

```python
class TempFileManager:
    """
    임시 파일 관리자

    SDS ID: SDS-S02-001
    """

    TEMP_DIR = Path("/tmp/video_converter")
    MAX_AGE_HOURS = 24

    def __init__(self):
        self._ensure_temp_dir()
        self._cleanup_old_files()

    def create_temp_file(self, suffix: str = ".mp4") -> Path:
        """
        보안 임시 파일 생성

        Security:
        - 예측 불가능한 파일명 (UUID 사용)
        - 제한된 권한 (0600)
        - 자동 정리 등록
        """
        filename = f"{uuid.uuid4()}{suffix}"
        path = self.TEMP_DIR / filename
        path.touch(mode=0o600)
        return path

    def cleanup(self, path: Path) -> None:
        """임시 파일 삭제"""
        if path.exists() and path.parent == self.TEMP_DIR:
            path.unlink()

    def _cleanup_old_files(self) -> None:
        """
        오래된 임시 파일 정리

        Criteria:
        - 생성 후 24시간 경과
        - video_converter 디렉토리 내 파일만
        """
        now = datetime.now()
        for file in self.TEMP_DIR.glob("*"):
            age = now - datetime.fromtimestamp(file.stat().st_mtime)
            if age.total_seconds() > self.MAX_AGE_HOURS * 3600:
                file.unlink()
```

### 8.4 로깅 개인정보 보호

```python
class PrivacyLogger:
    """
    개인정보 보호 로거

    SDS ID: SDS-S03-001
    """

    @staticmethod
    def sanitize_path(path: Path) -> str:
        """
        경로 익명화

        Examples:
        /Users/john/Pictures/vacation.mp4
        → /Users/****/Pictures/vacation.mp4

        Logic:
        - 사용자명 마스킹
        - 파일명만 노출
        """
        parts = path.parts
        if len(parts) > 2 and parts[0] == '/' and parts[1] == 'Users':
            sanitized = ['/', 'Users', '****'] + list(parts[3:])
            return str(Path(*sanitized))
        return str(path)

    @staticmethod
    def hash_path(path: Path) -> str:
        """
        경로 해시화

        Use Case:
        - 에러 로그에서 경로 추적 필요 시
        - 개인정보 노출 없이 문제 추적
        """
        return hashlib.sha256(str(path).encode()).hexdigest()[:12]
```

---

## 9. 성능 설계

### 9.1 성능 목표

| SDS ID | 메트릭 | 목표값 | 측정 방법 | SRS 추적 |
|--------|--------|--------|----------|----------|
| SDS-PF-001 | 4K 30분 HW 변환 | ≤5분 | 벤치마크 | SRS-NFR-101 |
| SDS-PF-002 | 1080p 10분 HW 변환 | ≤30초 | 벤치마크 | SRS-NFR-102 |
| SDS-PF-003 | CPU 사용률 (HW) | ≤30% | 모니터링 | SRS-NFR-103 |
| SDS-PF-004 | 메모리 사용량 | ≤1GB | 모니터링 | SRS-NFR-104 |
| SDS-PF-005 | 코덱 감지 시간 | ≤500ms | 단위 테스트 | SRS-NFR-105 |
| SDS-PF-006 | Photos 스캔 (1000개) | ≤30초 | 벤치마크 | SRS-NFR-106 |

### 9.2 최적화 전략

#### 코덱 감지 캐싱

```python
from functools import lru_cache
from typing import Tuple

class CachedCodecDetector:
    """
    캐시된 코덱 감지기

    SDS ID: SDS-PF-101
    """

    @lru_cache(maxsize=1000)
    def _detect_cached(self, path_key: Tuple[str, float]) -> CodecInfo:
        """
        캐시된 코덱 감지

        Cache Key: (경로, 수정시간)
        - 같은 파일이라도 수정되면 캐시 무효화
        - 최대 1000개 항목 캐시 (LRU)

        Performance:
        - 캐시 히트: < 1ms
        - 캐시 미스: 50-200ms (FFprobe 호출)
        """

    def detect(self, path: Path) -> CodecInfo:
        mtime = path.stat().st_mtime
        return self._detect_cached((str(path), mtime))
```

#### 병렬 처리

```python
class ParallelProcessor:
    """
    병렬 처리기

    SDS ID: SDS-PF-102
    """

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers

    async def process_batch(
        self,
        videos: List[VideoInfo],
        processor: Callable[[VideoInfo], ConversionResult]
    ) -> List[ConversionResult]:
        """
        병렬 배치 처리

        Strategy:
        - 동시 실행 제한 (기본 2개)
        - VideoToolbox 리소스 경합 방지
        - CPU 과부하 방지

        Implementation:
        - asyncio.Semaphore로 동시성 제어
        - asyncio.gather로 병렬 실행
        """
        semaphore = asyncio.Semaphore(self.max_workers)

        async def limited_process(video: VideoInfo) -> ConversionResult:
            async with semaphore:
                return await processor(video)

        return await asyncio.gather(
            *[limited_process(v) for v in videos]
        )
```

#### 스트리밍 처리

```python
class StreamingProcessor:
    """
    스트리밍 처리기 (메모리 효율)

    SDS ID: SDS-PF-103
    """

    CHUNK_SIZE = 8192  # 8KB

    async def stream_progress(
        self,
        process: asyncio.subprocess.Process
    ) -> AsyncGenerator[ProgressInfo, None]:
        """
        FFmpeg 출력 스트리밍

        Memory Strategy:
        - 줄 단위 읽기 (전체 버퍼링 없음)
        - 필요한 정보만 파싱
        - 즉시 yield

        Memory Usage: O(1) constant
        """
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            progress = self._parse_progress(line.decode())
            if progress:
                yield progress
```

### 9.3 리소스 모니터링

```python
class ResourceMonitor:
    """
    시스템 리소스 모니터

    SDS ID: SDS-PF-104
    """

    def check_disk_space(self, path: Path, required_bytes: int) -> bool:
        """
        디스크 공간 확인

        Requirement:
        - 필요 공간의 1.5배 확보
        - 변환 중 임시 공간 고려
        """
        stat = os.statvfs(path)
        available = stat.f_bavail * stat.f_frsize
        return available >= required_bytes * 1.5

    def check_system_load(self) -> Tuple[float, float]:
        """
        시스템 부하 확인

        Returns: (cpu_percent, memory_percent)

        Threshold:
        - CPU > 80%: 변환 대기
        - Memory > 90%: 변환 대기
        """
        import psutil
        return psutil.cpu_percent(), psutil.virtual_memory().percent

    def estimate_completion_time(
        self,
        video: VideoInfo,
        mode: str
    ) -> float:
        """
        예상 완료 시간 계산 (초)

        Estimation Formula:
        - Hardware: duration / 20 (20x 실시간)
        - Software: duration * 3 (0.33x 실시간)

        Adjustment:
        - 4K: +50%
        - 시스템 부하 기반 조정
        """
        base_speed = 20.0 if mode == 'hardware' else 0.33
        estimate = video.duration / base_speed

        if video.is_4k:
            estimate *= 1.5

        # 시스템 부하 조정
        cpu, mem = self.check_system_load()
        if cpu > 50 or mem > 70:
            estimate *= 1.2

        return estimate
```

---

## 10. 설계 추적 매트릭스

### 10.1 SRS → SDS 추적

| SRS ID | SRS 명칭 | SDS ID | SDS 설계 항목 | 상태 |
|--------|---------|--------|--------------|------|
| **코덱 감지 모듈** |
| SRS-101 | 비디오 코덱 감지 | SDS-P01-001 | CodecDetector | 매핑 |
| **변환 모듈** |
| SRS-201 | 하드웨어 가속 변환 | SDS-V01-001 | HardwareConverter | 매핑 |
| SRS-202 | 소프트웨어 변환 | SDS-V01-002 | SoftwareConverter | 매핑 |
| **Photos 통합 모듈** |
| SRS-301 | Photos 라이브러리 스캔 | SDS-E01-001 | PhotosExtractor | 매핑 |
| SRS-302 | iCloud 비디오 다운로드 | SDS-E01-001 | PhotosExtractor._download_from_icloud | 매핑 |
| SRS-303 | H.264 비디오 필터링 | SDS-P01-005 | PhotosVideoFilter | 매핑 |
| SRS-304 | 비디오 내보내기 | SDS-P01-006 | VideoExporter | 매핑 |
| **메타데이터 모듈** |
| SRS-401 | 메타데이터 추출 | SDS-P01-002 | MetadataManager.extract | 매핑 |
| SRS-402 | 메타데이터 검증 | SDS-P01-002 | MetadataManager.verify | 매핑 |
| **품질 관리 모듈** |
| SRS-501 | 변환 결과 검증 | SDS-P01-003 | QualityValidator | 매핑 |
| **자동화 모듈** |
| SRS-601 | 스케줄 기반 실행 | SDS-A01-001 | LaunchdManager | 매핑 |
| SRS-602 | 폴더 감시 기반 실행 | SDS-A01-001 | LaunchdManager (WatchPaths) | 매핑 |
| SRS-603 | macOS 알림 | SDS-R01-001 | MacOSNotifier | 매핑 |
| **CLI 모듈** |
| SRS-701 | CLI 명령 구조 | SDS-I01-001, SDS-C01-001 | CLI, Orchestrator | 매핑 |
| **안전 관리 모듈** |
| SRS-801 | 원본 보존 | SDS-D01-002 | conversion_history | 매핑 |
| SRS-802 | 에러 복구 | SDS-E07-001 | RetryPolicy | 매핑 |

### 10.2 SDS → 코드 추적

| SDS ID | 설계 항목 | 파일 경로 | 함수/클래스 |
|--------|----------|----------|------------|
| SDS-C01-001 | Orchestrator | src/video_converter/core/orchestrator.py | Orchestrator |
| SDS-C01-002 | ConfigManager | src/video_converter/core/config.py | ConfigManager |
| SDS-E01-001 | PhotosExtractor | src/video_converter/extractors/photos_extractor.py | PhotosExtractor |
| SDS-E01-002 | FolderExtractor | src/video_converter/extractors/folder_extractor.py | FolderExtractor |
| SDS-V01-001 | HardwareConverter | src/video_converter/converters/hardware.py | HardwareConverter |
| SDS-V01-002 | SoftwareConverter | src/video_converter/converters/software.py | SoftwareConverter |
| SDS-P01-001 | CodecDetector | src/video_converter/processors/codec_detector.py | CodecDetector |
| SDS-P01-002 | MetadataManager | src/video_converter/processors/metadata.py | MetadataManager |
| SDS-P01-003 | QualityValidator | src/video_converter/processors/validator.py | QualityValidator |
| SDS-P01-005 | PhotosVideoFilter | src/video_converter/extractors/photos_extractor.py | PhotosVideoFilter |
| SDS-P01-006 | VideoExporter | src/video_converter/extractors/photos_extractor.py | VideoExporter |
| SDS-A01-001 | LaunchdManager | src/video_converter/automation/launchd.py | LaunchdManager |
| SDS-R01-001 | MacOSNotifier | src/video_converter/reporters/notifier.py | MacOSNotifier |
| SDS-D01-005 | ConversionHistory | src/video_converter/core/history.py | ConversionHistory |

### 10.3 SDS → 테스트 추적

| SDS ID | 설계 항목 | 테스트 파일 | 테스트 케이스 |
|--------|----------|------------|--------------|
| SDS-P01-001 | CodecDetector | tests/test_codec_detector.py | test_detect_h264, test_detect_hevc |
| SDS-V01-001 | HardwareConverter | tests/test_hardware_converter.py | test_convert_success, test_retry_on_failure |
| SDS-V01-002 | SoftwareConverter | tests/test_software_converter.py | test_crf_quality |
| SDS-P01-002 | MetadataManager | tests/test_metadata.py | test_extract_gps, test_apply_metadata |
| SDS-P01-003 | QualityValidator | tests/test_validator.py | test_integrity_check, test_properties_match |
| SDS-P01-006 | VideoExporter | tests/unit/test_photos_extractor.py | TestVideoExporter (16 tests) |
| SDS-A01-001 | LaunchdManager | tests/test_launchd.py | test_install_service, test_uninstall_service |

---

## 11. 부록

### 11.1 참조 문서

| 문서 | 설명 | 위치 |
|------|------|------|
| PRD.md | 제품 요구사항 정의서 | docs/PRD.md |
| SRS.md | 소프트웨어 요구사항 명세서 | docs/SRS.md |
| 01-system-architecture.md | 시스템 아키텍처 | docs/architecture/ |
| 02-sequence-diagrams.md | 시퀀스 다이어그램 | docs/architecture/ |
| 03-data-flow-and-states.md | 데이터 흐름 및 상태 | docs/architecture/ |
| 04-processing-procedures.md | 처리 절차 | docs/architecture/ |
| development-plan.md | 개발 계획서 | docs/ |

### 11.2 용어 정의

| 용어 | 정의 |
|------|------|
| SDS | Software Design Specification |
| DIP | Dependency Inversion Principle |
| SRP | Single Responsibility Principle |
| OCP | Open-Closed Principle |
| LRU | Least Recently Used |
| CRF | Constant Rate Factor |
| VMAF | Video Multimethod Assessment Fusion |

### 11.3 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2025-12-21 | 최초 작성 |

---

## 승인

| 역할 | 이름 | 서명 | 날짜 |
|------|------|------|------|
| Tech Lead | | | |
| Architect | | | |
| Developer | | | |

---

*이 문서는 개발 진행에 따라 업데이트됩니다.*
