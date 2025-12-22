# Video Converter - Software Requirements Specification (SRS)

**문서 버전**: 1.0.1
**작성일**: 2025-12-23
**상태**: Active
**기준 문서**: PRD v1.1.0

---

## 문서 정보

### 추적성 정보

| 항목 | 참조 |
|------|------|
| 상위 문서 | PRD.md v1.1.0 |
| 관련 문서 | SDS.md, development-plan.md, architecture/*.md |
| 요구사항 ID 체계 | SRS-xxx (본 문서), FR-xxx/NFR-xxx (PRD) |

### 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2025-12-21 | - | 최초 작성 |
| 1.0.1 | 2025-12-23 | - | PRD v1.1.0에 맞춰 문서 상태 및 참조 업데이트 |

---

## 목차

1. [개요](#1-개요)
2. [시스템 개요](#2-시스템-개요)
3. [기능 요구사항 상세](#3-기능-요구사항-상세)
4. [비기능 요구사항 상세](#4-비기능-요구사항-상세)
5. [외부 인터페이스 요구사항](#5-외부-인터페이스-요구사항)
6. [데이터 요구사항](#6-데이터-요구사항)
7. [시스템 제약사항](#7-시스템-제약사항)
8. [요구사항 추적 매트릭스](#8-요구사항-추적-매트릭스)
9. [검증 및 유효성 확인](#9-검증-및-유효성-확인)
10. [부록](#10-부록)

---

## 1. 개요

### 1.1 목적

본 문서는 Video Converter 시스템의 소프트웨어 요구사항을 상세히 명세합니다. PRD(Product Requirements Document)에서 정의된 제품 요구사항을 기술적으로 구체화하여 개발팀이 구현할 수 있는 수준의 명세를 제공합니다.

### 1.2 범위

| 항목 | 내용 |
|------|------|
| 시스템 명 | Video Converter |
| 버전 | 0.1.0.0+ |
| 대상 플랫폼 | macOS 12.0+ (Apple Silicon) |
| 개발 언어 | Python 3.10+ |

> **참고**: 본 프로젝트는 활발한 개발 상태를 나타내기 위해 0.x.x.x 버전 체계를 사용합니다.

### 1.3 정의 및 약어

| 약어 | 정의 |
|------|------|
| SRS | Software Requirements Specification |
| PRD | Product Requirements Document |
| FR | Functional Requirement (기능 요구사항) |
| NFR | Non-Functional Requirement (비기능 요구사항) |
| US | User Story (사용자 스토리) |
| RTM | Requirements Traceability Matrix (요구사항 추적 매트릭스) |
| HEVC | High Efficiency Video Coding (H.265) |
| AVC | Advanced Video Coding (H.264) |

### 1.4 참조 문서

- PRD.md - 제품 요구사항 정의서
- **SDS.md - 소프트웨어 설계 명세서** (본 문서의 설계 구현)
- development-plan.md - 개발 계획서
- 01-system-architecture.md - 시스템 아키텍처
- 02-sequence-diagrams.md - 시퀀스 다이어그램
- 03-data-flow-and-states.md - 데이터 흐름 및 상태
- 04-processing-procedures.md - 처리 절차

---

## 2. 시스템 개요

### 2.1 시스템 컨텍스트

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           시스템 컨텍스트                                  │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    User     │
                              │  (macOS)    │
                              └──────┬──────┘
                                     │ CLI / 알림
                                     ▼
┌──────────────┐            ┌─────────────────┐            ┌──────────────┐
│   Photos     │───읽기────▶│ Video Converter │───쓰기────▶│  File System │
│   Library    │            │     System      │            │   (Output)   │
└──────────────┘            └────────┬────────┘            └──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐     ┌──────────┐
             │  FFmpeg  │     │ ExifTool │     │ launchd  │
             │ (변환)   │     │ (메타)   │     │ (자동화) │
             └──────────┘     └──────────┘     └──────────┘
```

### 2.2 시스템 기능 개요

| 기능 영역 | 설명 | PRD 참조 |
|----------|------|----------|
| 코덱 감지 | H.264/H.265 코덱 자동 감지 | FR-001 |
| 비디오 변환 | H.264 → H.265 인코딩 | FR-002, FR-003 |
| Photos 통합 | Photos 라이브러리 스캔 및 추출 | FR-101 ~ FR-105 |
| 메타데이터 처리 | GPS, 날짜 등 메타데이터 보존 | FR-201 ~ FR-204 |
| 품질 관리 | 변환 결과 검증 | FR-301 ~ FR-304 |
| 자동화 | 스케줄 및 폴더 감시 기반 자동 실행 | FR-401 ~ FR-404 |
| CLI | 커맨드라인 인터페이스 | FR-501 ~ FR-505 |
| 안전 관리 | 원본 보존 및 에러 복구 | FR-601 ~ FR-604 |

### 2.3 사용자 분류

| 사용자 유형 | 설명 | PRD 참조 |
|------------|------|----------|
| 일반 사용자 | CLI 기본 기능 사용, 자동화 의존 | Persona: 민수 |
| 고급 사용자 | CLI 상세 옵션 활용, 품질 설정 커스터마이징 | Persona: 지연 |
| 개발자/관리자 | 스크립트 연동, 로그 분석, 서비스 관리 | Persona: 성호 |

---

## 3. 기능 요구사항 상세

### 3.1 코덱 감지 모듈 (SRS-100)

#### SRS-101: 비디오 코덱 감지

| 항목 | 내용 |
|------|------|
| **ID** | SRS-101 |
| **명칭** | 비디오 코덱 감지 |
| **PRD 추적** | FR-001, US-201 |
| **우선순위** | P0 (필수) |

**설명**:
시스템은 입력 비디오 파일의 비디오 스트림 코덱을 감지해야 한다.

**선행 조건**:
- 유효한 비디오 파일 경로가 제공됨
- FFprobe가 시스템에 설치되어 있음

**입력**:
```
Input: video_path: Path
       - 비디오 파일의 절대 경로
       - 지원 확장자: .mp4, .mov, .m4v, .MP4, .MOV, .M4V
```

**처리 로직**:
```python
def detect_codec(video_path: Path) -> CodecInfo:
    """
    FFprobe를 사용하여 비디오 코덱 정보 추출

    Algorithm:
    1. FFprobe 명령 구성
       - 비디오 스트림만 선택 (-select_streams v:0)
       - 코덱 이름 추출 (-show_entries stream=codec_name)
    2. 서브프로세스로 FFprobe 실행
    3. 출력 파싱 및 정규화 (소문자 변환)
    4. CodecInfo 객체 반환
    """
```

**FFprobe 명령**:
```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=codec_name \
  -of default=noprint_wrappers=1:nokey=1 \
  "<video_path>"
```

**출력**:
```
Output: CodecInfo
        - codec_name: str  # "h264", "hevc", "av1" 등
        - is_h264: bool    # H.264 여부
        - is_hevc: bool    # H.265/HEVC 여부
```

**코덱 매핑 테이블**:
| FFprobe 출력 | 정규화 값 | is_h264 | is_hevc |
|-------------|----------|---------|---------|
| h264 | h264 | True | False |
| avc | h264 | True | False |
| avc1 | h264 | True | False |
| hevc | hevc | False | True |
| h265 | hevc | False | True |
| hvc1 | hevc | False | True |
| hev1 | hevc | False | True |

**예외 처리**:
| 예외 상황 | 처리 방법 | 에러 코드 |
|----------|----------|----------|
| 파일 미존재 | FileNotFoundError 발생 | E-101 |
| FFprobe 실행 실패 | FFprobeError 발생 | E-102 |
| 비디오 스트림 없음 | NoVideoStreamError 발생 | E-103 |
| 알 수 없는 코덱 | UnknownCodecError 발생 | E-104 |

**성능 요구사항**:
- 단일 파일 감지 시간: 500ms 이하
- 메모리 사용: 10MB 이하

---

### 3.2 비디오 변환 모듈 (SRS-200)

#### SRS-201: 하드웨어 가속 변환 (VideoToolbox)

| 항목 | 내용 |
|------|------|
| **ID** | SRS-201 |
| **명칭** | 하드웨어 가속 H.265 변환 |
| **PRD 추적** | FR-002, US-203, US-204 |
| **우선순위** | P0 (필수) |

**설명**:
Apple Silicon의 VideoToolbox를 사용하여 H.264 비디오를 H.265로 하드웨어 가속 변환한다.

**선행 조건**:
- 입력 파일이 H.264 코덱임 (SRS-101로 확인)
- Apple Silicon Mac (M1/M2/M3/M4)
- FFmpeg 5.0+ (hevc_videotoolbox 지원)

**입력**:
```
Input: ConversionRequest
       - input_path: Path      # 입력 비디오 경로
       - output_path: Path     # 출력 비디오 경로
       - quality: int          # 품질 설정 (1-100, 기본값 45)
       - audio_mode: str       # "copy" | "transcode" (기본값 "copy")
```

**품질 설정 매핑**:
| 프리셋 | quality 값 | 예상 압축률 | 용도 |
|--------|-----------|------------|------|
| 고품질 | 30-40 | 35-45% | 아카이빙 |
| 균형 (기본) | 45-55 | 45-55% | 일반 사용 |
| 고속 | 60-70 | 55-65% | 대량 변환 |

**FFmpeg 명령 생성**:
```python
def build_hardware_command(request: ConversionRequest) -> List[str]:
    """
    하드웨어 인코딩용 FFmpeg 명령 생성
    """
    return [
        "ffmpeg",
        "-y",                           # 덮어쓰기 허용
        "-i", str(request.input_path),  # 입력 파일
        "-c:v", "hevc_videotoolbox",    # VideoToolbox 인코더
        "-q:v", str(request.quality),   # 품질 설정
        "-tag:v", "hvc1",               # QuickTime 호환 태그
        "-c:a", request.audio_mode,     # 오디오 처리
        "-map_metadata", "0",           # 메타데이터 복사
        "-movflags", "use_metadata_tags",
        "-progress", "pipe:1",          # 진행률 출력
        str(request.output_path)
    ]
```

**진행률 모니터링**:
```python
class ProgressMonitor:
    """
    FFmpeg 진행률 파싱 및 콜백 처리

    FFmpeg progress 출력 형식:
    - out_time_ms=12500000
    - frame=375
    - fps=45.2
    - speed=3.5x
    """

    def parse_progress(self, line: str) -> Optional[ProgressInfo]:
        """
        진행률 라인 파싱

        Returns:
            ProgressInfo: 진행 정보
            - current_time_ms: int  # 현재 처리된 시간 (ms)
            - frame: int            # 처리된 프레임 수
            - fps: float            # 현재 처리 속도
            - speed: float          # 실시간 대비 속도
        """
```

**출력**:
```
Output: ConversionResult
        - success: bool           # 성공 여부
        - input_path: Path        # 입력 경로
        - output_path: Path       # 출력 경로
        - original_size: int      # 원본 크기 (bytes)
        - converted_size: int     # 변환 크기 (bytes)
        - compression_ratio: float # 압축률 (0.0-1.0)
        - duration_seconds: float  # 변환 소요 시간
        - speed_ratio: float       # 실시간 대비 속도
        - error_message: str       # 에러 시 메시지
```

**예외 처리**:
| 예외 상황 | 재시도 | 처리 방법 | 에러 코드 |
|----------|--------|----------|----------|
| FFmpeg 실행 실패 | 3회 | 지수 백오프 후 재시도 | E-201 |
| 디스크 공간 부족 | 0회 | 즉시 실패, 사용자 알림 | E-202 |
| 입력 파일 손상 | 0회 | 실패 폴더로 이동 | E-203 |
| 출력 파일 생성 실패 | 1회 | 임시 디렉토리로 변경 후 재시도 | E-204 |
| 인코더 초기화 실패 | 1회 | 소프트웨어 인코더로 폴백 | E-205 |

**재시도 로직**:
```python
async def convert_with_retry(
    request: ConversionRequest,
    max_retries: int = 3
) -> ConversionResult:
    """
    지수 백오프를 사용한 재시도 로직

    Retry delays: 5s, 10s, 20s
    """
    for attempt in range(max_retries):
        try:
            result = await self._convert(request)
            if result.success:
                return result
        except RetryableError as e:
            if attempt < max_retries - 1:
                delay = 5 * (2 ** attempt)  # 5, 10, 20 seconds
                await asyncio.sleep(delay)
            else:
                raise MaxRetriesExceededError(e)
```

---

#### SRS-202: 소프트웨어 변환 (libx265)

| 항목 | 내용 |
|------|------|
| **ID** | SRS-202 |
| **명칭** | 소프트웨어 H.265 변환 |
| **PRD 추적** | FR-003, US-203 |
| **우선순위** | P1 (중요) |

**설명**:
libx265를 사용한 고품질 소프트웨어 인코딩. 하드웨어 인코딩 대비 느리지만 더 작은 파일 크기 및 높은 품질 제공.

**FFmpeg 명령 생성**:
```python
def build_software_command(request: ConversionRequest) -> List[str]:
    """
    소프트웨어 인코딩용 FFmpeg 명령 생성
    """
    return [
        "ffmpeg",
        "-y",
        "-i", str(request.input_path),
        "-c:v", "libx265",              # 소프트웨어 인코더
        "-crf", str(request.crf),        # CRF 품질 설정
        "-preset", request.preset,       # 인코딩 프리셋
        "-c:a", request.audio_mode,
        "-map_metadata", "0",
        "-progress", "pipe:1",
        str(request.output_path)
    ]
```

**CRF 설정 가이드**:
| 용도 | CRF 값 | preset | 예상 압축률 | 예상 VMAF |
|------|--------|--------|------------|----------|
| 아카이빙 | 18-20 | slow | 30-40% | 97+ |
| 고품질 | 20-22 | slow | 40-50% | 95+ |
| 균형 | 22-24 | medium | 45-55% | 93+ |
| 용량 우선 | 24-28 | fast | 55-65% | 90+ |

---

### 3.3 Photos 통합 모듈 (SRS-300)

#### SRS-301: Photos 라이브러리 스캔

| 항목 | 내용 |
|------|------|
| **ID** | SRS-301 |
| **명칭** | Photos 라이브러리 스캔 |
| **PRD 추적** | FR-101, FR-102, US-201, US-205 |
| **우선순위** | P0 (필수) |

**설명**:
osxphotos를 사용하여 macOS Photos 라이브러리의 비디오 목록을 조회하고 H.264 코덱 비디오만 필터링한다.

**선행 조건**:
- osxphotos 0.70+ 설치
- Photos 라이브러리 접근 권한 (Full Disk Access)

**인터페이스**:
```python
class PhotosExtractor:
    """Photos 라이브러리에서 비디오 추출"""

    def __init__(self, library_path: Optional[Path] = None):
        """
        Parameters:
            library_path: Photos 라이브러리 경로
                          None이면 기본 경로 사용
                          기본값: ~/Pictures/Photos Library.photoslibrary
        """

    def scan_videos(
        self,
        filter_codec: Optional[str] = "h264",
        since_date: Optional[datetime] = None,
        albums: Optional[List[str]] = None,
        exclude_converted: bool = True
    ) -> List[VideoInfo]:
        """
        비디오 목록 스캔

        Parameters:
            filter_codec: 필터링할 코덱 (None이면 전체)
            since_date: 이 날짜 이후 생성된 비디오만
            albums: 특정 앨범만 (None이면 전체)
            exclude_converted: 이미 변환된 비디오 제외

        Returns:
            VideoInfo 객체 리스트
        """

    def export_video(
        self,
        video: VideoInfo,
        dest_dir: Path,
        download_from_icloud: bool = True
    ) -> Path:
        """
        비디오 파일 내보내기

        Parameters:
            video: 내보낼 비디오 정보
            dest_dir: 내보내기 대상 디렉토리
            download_from_icloud: iCloud에서 다운로드 여부

        Returns:
            내보내기된 파일 경로
        """
```

**VideoInfo 데이터 구조**:
```python
@dataclass
class VideoInfo:
    """비디오 정보 데이터 클래스"""

    uuid: str                           # Photos 내부 UUID
    original_filename: str              # 원본 파일명
    path: Optional[Path]                # 로컬 파일 경로 (없으면 iCloud)
    codec: str                          # 비디오 코덱
    duration: float                     # 재생 시간 (초)
    size: int                           # 파일 크기 (bytes)
    width: int                          # 가로 해상도
    height: int                         # 세로 해상도
    fps: float                          # 프레임레이트
    creation_date: datetime             # 촬영 날짜
    location: Optional[Tuple[float, float]]  # (위도, 경도)
    albums: List[str]                   # 소속 앨범
    is_in_icloud: bool                  # iCloud 전용 여부
    is_favorite: bool                   # 즐겨찾기 여부
```

**변환 기록 관리** (중복 방지):
```python
class ConversionHistory:
    """변환 이력 관리"""

    def __init__(self, db_path: Path):
        """SQLite 기반 이력 저장소 초기화"""

    def is_converted(self, video_uuid: str) -> bool:
        """이미 변환된 비디오인지 확인"""

    def mark_converted(
        self,
        video_uuid: str,
        output_path: Path,
        converted_at: datetime
    ) -> None:
        """변환 완료 기록"""

    def get_history(
        self,
        since: Optional[datetime] = None
    ) -> List[ConversionRecord]:
        """변환 이력 조회"""
```

---

#### SRS-302: iCloud 비디오 다운로드

| 항목 | 내용 |
|------|------|
| **ID** | SRS-302 |
| **명칭** | iCloud 비디오 다운로드 |
| **PRD 추적** | FR-104, US-201 |
| **우선순위** | P1 (중요) |

**설명**:
iCloud에만 저장된 비디오를 로컬로 다운로드하여 변환 가능하게 한다.

**다운로드 상태 관리**:
```python
class iCloudDownloader:
    """iCloud 비디오 다운로드 관리"""

    async def download(
        self,
        video: VideoInfo,
        timeout: int = 600  # 10분
    ) -> Path:
        """
        iCloud에서 비디오 다운로드

        Parameters:
            video: 다운로드할 비디오 정보
            timeout: 타임아웃 (초)

        Returns:
            다운로드된 파일 경로

        Raises:
            iCloudTimeoutError: 타임아웃 초과
            iCloudQuotaError: 용량 제한 초과
            NetworkError: 네트워크 오류
        """

    def get_download_status(self, video_uuid: str) -> DownloadStatus:
        """다운로드 상태 확인"""
```

**다운로드 상태**:
```python
class DownloadStatus(Enum):
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
```

---

### 3.4 메타데이터 처리 모듈 (SRS-400)

#### SRS-401: 메타데이터 추출

| 항목 | 내용 |
|------|------|
| **ID** | SRS-401 |
| **명칭** | 메타데이터 추출 |
| **PRD 추적** | FR-201, US-301, US-302 |
| **우선순위** | P0 (필수) |

**설명**:
ExifTool을 사용하여 원본 비디오의 모든 메타데이터를 추출한다.

**인터페이스**:
```python
class MetadataManager:
    """메타데이터 추출 및 복원 관리"""

    def extract(self, video_path: Path) -> Metadata:
        """
        비디오에서 메타데이터 추출

        ExifTool 명령: exiftool -json <path>

        Returns:
            Metadata 객체
        """

    def apply(
        self,
        source_path: Path,
        target_path: Path,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        소스에서 타겟으로 메타데이터 복사

        ExifTool 명령:
        exiftool -overwrite_original -tagsFromFile <source> -all:all <target>

        Parameters:
            source_path: 원본 비디오 경로
            target_path: 대상 비디오 경로
            tags: 특정 태그만 복사 (None이면 전체)
        """

    def apply_gps(
        self,
        source_path: Path,
        target_path: Path
    ) -> None:
        """
        GPS 좌표 명시적 복사

        ExifTool 명령:
        exiftool -overwrite_original -tagsFromFile <source> "-GPS*" <target>
        """

    def sync_timestamps(
        self,
        source_path: Path,
        target_path: Path
    ) -> None:
        """
        파일 시스템 타임스탬프 동기화

        os.utime() 사용
        """
```

**Metadata 데이터 구조**:
```python
@dataclass
class Metadata:
    """비디오 메타데이터"""

    # 시간 정보
    create_date: Optional[datetime]
    modify_date: Optional[datetime]

    # 위치 정보
    gps_latitude: Optional[float]
    gps_longitude: Optional[float]
    gps_altitude: Optional[float]

    # 카메라 정보
    make: Optional[str]
    model: Optional[str]
    software: Optional[str]

    # 비디오 정보
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    frame_rate: Optional[float]

    # 원본 JSON 데이터
    raw_data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""

    @classmethod
    def from_exiftool_json(cls, data: Dict[str, Any]) -> "Metadata":
        """ExifTool JSON 출력에서 생성"""
```

**GPS 태그 매핑**:
| ExifTool 태그 | 설명 | 우선순위 |
|--------------|------|---------|
| QuickTime:GPSCoordinates | QuickTime 컨테이너 GPS | 1 |
| Keys:GPSCoordinates | Apple Keys GPS | 2 |
| XMP:GPSLatitude | XMP GPS 위도 | 3 |
| XMP:GPSLongitude | XMP GPS 경도 | 3 |
| Composite:GPSLatitude | 계산된 GPS 위도 | 4 |
| Composite:GPSLongitude | 계산된 GPS 경도 | 4 |

---

#### SRS-402: 메타데이터 검증

| 항목 | 내용 |
|------|------|
| **ID** | SRS-402 |
| **명칭** | 메타데이터 검증 |
| **PRD 추적** | FR-203, US-302, US-503 |
| **우선순위** | P0 (필수) |

**설명**:
변환 후 메타데이터가 올바르게 보존되었는지 검증한다.

**검증 로직**:
```python
def verify_metadata(
    original: Metadata,
    converted: Metadata,
    tolerance: MetadataTolerance = MetadataTolerance.DEFAULT
) -> MetadataVerificationResult:
    """
    메타데이터 보존 검증

    검증 항목:
    1. 날짜 정보 (create_date, modify_date)
       - 허용 오차: 1초
    2. GPS 좌표 (latitude, longitude)
       - 허용 오차: 소수점 6자리 (약 0.1m)
    3. 카메라 정보 (make, model)
       - 정확히 일치

    Returns:
        MetadataVerificationResult:
        - verified: bool      # 검증 통과 여부
        - issues: List[str]   # 불일치 항목
        - warnings: List[str] # 경고 항목
    """
```

---

### 3.5 품질 관리 모듈 (SRS-500)

#### SRS-501: 변환 결과 검증

| 항목 | 내용 |
|------|------|
| **ID** | SRS-501 |
| **명칭** | 변환 결과 검증 |
| **PRD 추적** | FR-301, FR-302, FR-303, US-503 |
| **우선순위** | P0 (필수) |

**설명**:
변환된 비디오 파일의 무결성과 품질을 검증한다.

**인터페이스**:
```python
class QualityValidator:
    """변환 품질 검증"""

    def validate(
        self,
        original_path: Path,
        converted_path: Path,
        config: ValidationConfig
    ) -> ValidationResult:
        """
        변환 결과 종합 검증

        검증 단계:
        1. 파일 무결성 검사 (FFprobe)
        2. 속성 비교 (해상도, 프레임레이트, 재생시간)
        3. 압축률 검사 (정상 범위 확인)
        4. VMAF 측정 (선택적)
        """
```

**검증 단계별 상세**:

**Step 1: 파일 무결성 검사**
```python
def check_integrity(self, path: Path) -> IntegrityResult:
    """
    FFprobe로 파일 무결성 검사

    명령: ffprobe -v error -show_format -show_streams <path>

    확인 항목:
    - 파일 존재 및 크기 > 0
    - 비디오 스트림 존재
    - 코덱 정보 추출 가능
    - 재생 시간 > 0
    """
```

**Step 2: 속성 비교**
```python
def compare_properties(
    self,
    original: VideoProperties,
    converted: VideoProperties
) -> PropertyComparisonResult:
    """
    비디오 속성 비교

    비교 항목 및 허용 오차:
    - 해상도: 정확히 일치
    - 프레임레이트: ±0.1 fps
    - 재생 시간: ±1.0 초
    - 오디오 채널: 정확히 일치
    """
```

**Step 3: 압축률 검사**
```python
def check_compression_ratio(
    self,
    original_size: int,
    converted_size: int
) -> CompressionResult:
    """
    압축률 정상 범위 확인

    정상 범위: 20% ~ 80%
    경고 범위: 15-20% 또는 80-90%
    오류 범위: <15% 또는 >90%

    비정상 시 원인 분석:
    - 너무 작음: 품질 손실 가능성
    - 너무 큼: 변환 실패 또는 비효율적 인코딩
    """
```

**Step 4: VMAF 측정 (선택적)**
```python
def calculate_vmaf(
    self,
    reference_path: Path,
    distorted_path: Path
) -> float:
    """
    VMAF 품질 점수 계산

    FFmpeg 명령:
    ffmpeg -i <distorted> -i <reference> \
      -lavfi libvmaf="model=version=vmaf_v0.6.1" \
      -f null -

    Returns:
        VMAF 점수 (0-100)

    참고: 계산 시간이 오래 걸림 (실시간의 0.1-0.5배)
    """
```

**ValidationResult 구조**:
```python
@dataclass
class ValidationResult:
    """검증 결과"""

    valid: bool                    # 최종 검증 통과 여부
    integrity_ok: bool             # 무결성 통과
    properties_match: bool         # 속성 일치
    compression_normal: bool       # 압축률 정상
    vmaf_score: Optional[float]    # VMAF 점수 (측정 시)
    compression_ratio: float       # 압축률
    errors: List[str]              # 에러 목록
    warnings: List[str]            # 경고 목록
    duration_seconds: float        # 검증 소요 시간
```

---

### 3.6 자동화 모듈 (SRS-600)

#### SRS-601: 스케줄 기반 실행

| 항목 | 내용 |
|------|------|
| **ID** | SRS-601 |
| **명칭** | 스케줄 기반 자동 실행 |
| **PRD 추적** | FR-401, US-401 |
| **우선순위** | P0 (필수) |

**설명**:
launchd의 StartCalendarInterval을 사용하여 지정된 시간에 자동으로 변환 작업을 실행한다.

**plist 템플릿**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/main.py</string>
        <string>run</string>
        <string>--mode</string>
        <string>photos</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${SCHEDULE_HOUR}</integer>
        <key>Minute</key>
        <integer>${SCHEDULE_MINUTE}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
```

**서비스 관리 인터페이스**:
```python
class LaunchdManager:
    """launchd 서비스 관리"""

    PLIST_DIR = Path.home() / "Library/LaunchAgents"
    LABEL = "com.user.videoconverter"

    def install(self, config: AutomationConfig) -> None:
        """
        서비스 설치

        1. plist 파일 생성
        2. LaunchAgents 디렉토리에 복사
        3. launchctl load 실행
        """

    def uninstall(self) -> None:
        """
        서비스 제거

        1. launchctl unload 실행
        2. plist 파일 삭제
        """

    def start(self) -> None:
        """서비스 수동 시작: launchctl start <label>"""

    def stop(self) -> None:
        """서비스 중지: launchctl stop <label>"""

    def status(self) -> ServiceStatus:
        """서비스 상태 조회: launchctl list | grep <label>"""

    def get_next_run_time(self) -> Optional[datetime]:
        """다음 실행 예정 시간 계산"""
```

---

#### SRS-602: 폴더 감시 기반 실행

| 항목 | 내용 |
|------|------|
| **ID** | SRS-602 |
| **명칭** | 폴더 감시 자동 실행 |
| **PRD 추적** | FR-402, US-402 |
| **우선순위** | P1 (중요) |

**설명**:
launchd의 WatchPaths를 사용하여 특정 폴더에 파일이 추가되면 자동으로 변환 작업을 실행한다.

**WatchPaths plist 추가 설정**:
```xml
<key>WatchPaths</key>
<array>
    <string>${WATCH_DIR}</string>
</array>

<key>ThrottleInterval</key>
<integer>30</integer>  <!-- 최소 30초 간격으로 실행 -->
```

---

#### SRS-603: macOS 알림

| 항목 | 내용 |
|------|------|
| **ID** | SRS-603 |
| **명칭** | macOS 알림 발송 |
| **PRD 추적** | FR-403, US-403 |
| **우선순위** | P1 (중요) |

**설명**:
변환 완료 또는 에러 발생 시 macOS Notification Center에 알림을 표시한다.

**인터페이스**:
```python
class MacOSNotifier:
    """macOS 알림 관리"""

    def notify(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: bool = True
    ) -> None:
        """
        알림 표시

        AppleScript 사용:
        osascript -e 'display notification "<message>"
          with title "<title>" subtitle "<subtitle>"'
        """

    def notify_completion(self, stats: BatchStats) -> None:
        """변환 완료 알림"""

    def notify_error(self, error: str, video_name: str) -> None:
        """에러 알림"""
```

---

### 3.7 CLI 모듈 (SRS-700)

#### SRS-701: CLI 명령 구조

| 항목 | 내용 |
|------|------|
| **ID** | SRS-701 |
| **명칭** | CLI 명령 구조 |
| **PRD 추적** | FR-501 ~ FR-505 |
| **우선순위** | P0 (필수) |

**설명**:
커맨드라인 인터페이스를 통해 시스템의 모든 기능에 접근할 수 있다.

**명령 구조**:
```
video-converter <command> [options] [arguments]

Commands:
  convert       단일 파일 변환
  run           배치 변환 실행
  scan          변환 대상 스캔 (변환 없이)
  status        서비스 상태 확인
  stats         변환 통계 조회
  config        설정 관리
  install       서비스 설치
  uninstall     서비스 제거
  version       버전 정보

Global Options:
  -c, --config PATH     설정 파일 경로
  -v, --verbose         상세 로그 출력
  -q, --quiet           최소 출력 모드
  --log-file PATH       로그 파일 경로
  -h, --help            도움말 표시
```

**명령별 상세**:

**convert 명령**:
```
video-converter convert <input> <output> [options]

Arguments:
  input                 입력 비디오 파일 경로
  output                출력 비디오 파일 경로

Options:
  -m, --mode MODE       인코딩 모드 (hardware|software) [default: hardware]
  -q, --quality INT     품질 설정 (hardware: 1-100, software: CRF 0-51)
  --preset PRESET       인코딩 프리셋 (fast|medium|slow)
  --no-metadata         메타데이터 복사 안 함
  --validate            변환 후 품질 검증

Examples:
  video-converter convert input.mp4 output.mp4
  video-converter convert input.mp4 output.mp4 -m hardware -q 45
  video-converter convert input.mp4 output.mp4 -m software --preset slow
```

**run 명령**:
```
video-converter run [options]

Options:
  --mode MODE           소스 모드 (photos|folder) [default: photos]
  --folder PATH         폴더 모드 시 대상 폴더
  --since DATE          이 날짜 이후 비디오만 (YYYY-MM-DD)
  --album ALBUM         특정 앨범만 (여러 개 지정 가능)
  --dry-run             실제 변환 없이 시뮬레이션
  --limit N             최대 N개만 처리

Examples:
  video-converter run
  video-converter run --mode photos --since 2024-01-01
  video-converter run --mode folder --folder ~/Videos/ToConvert
  video-converter run --dry-run --limit 5
```

**status 명령**:
```
video-converter status

Output:
  서비스 상태, 다음 예정 실행 시간, 마지막 실행 결과
```

**stats 명령**:
```
video-converter stats [options]

Options:
  --period PERIOD       기간 (today|week|month|all) [default: week]
  --format FORMAT       출력 형식 (table|json|csv) [default: table]

Output:
  총 변환 수, 성공/실패, 절약 공간, 평균 압축률
```

---

### 3.8 안전 관리 모듈 (SRS-800)

#### SRS-801: 원본 보존

| 항목 | 내용 |
|------|------|
| **ID** | SRS-801 |
| **명칭** | 원본 파일 보존 |
| **PRD 추적** | FR-601, US-501, US-502 |
| **우선순위** | P0 (필수) |

**설명**:
변환 성공 시 원본 파일을 삭제하지 않고 별도 폴더로 이동하여 보존한다.

**처리 흐름**:
```python
def handle_original(
    self,
    original_path: Path,
    conversion_result: ConversionResult,
    config: SafetyConfig
) -> None:
    """
    원본 파일 처리

    성공 시:
    1. 원본 → processed 폴더로 이동
    2. 이동 기록 저장

    실패 시:
    1. 원본 그대로 유지
    2. 실패 기록 저장
    3. 알림 발송
    """
```

**디렉토리 구조**:
```
~/Videos/VideoConverter/
├── input/              # 변환 대기 (폴더 모드)
├── output/             # 변환 완료 결과물
├── processed/          # 성공한 원본 (날짜별 정리)
│   ├── 2024-12/
│   └── 2025-01/
├── failed/             # 실패한 원본
└── logs/               # 로그 파일
```

---

#### SRS-802: 에러 복구

| 항목 | 내용 |
|------|------|
| **ID** | SRS-802 |
| **명칭** | 에러 복구 및 재시도 |
| **PRD 추적** | FR-602, FR-603, US-502 |
| **우선순위** | P0 (필수) |

**재시도 정책**:
```python
@dataclass
class RetryPolicy:
    """재시도 정책"""

    max_retries: int = 3           # 최대 재시도 횟수
    base_delay: float = 5.0        # 기본 대기 시간 (초)
    max_delay: float = 60.0        # 최대 대기 시간 (초)
    exponential_base: float = 2.0  # 지수 백오프 기준

    def get_delay(self, attempt: int) -> float:
        """
        재시도 대기 시간 계산
        delay = min(base_delay * (exponential_base ^ attempt), max_delay)
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
```

**에러 분류 및 처리**:
| 에러 유형 | 재시도 | 처리 |
|----------|--------|------|
| 일시적 오류 (네트워크, 리소스) | Yes | 지수 백오프 재시도 |
| 영구적 오류 (손상 파일, 권한) | No | 즉시 실패 처리 |
| 알 수 없는 오류 | 1회 | 로깅 후 1회 재시도 |

---

## 4. 비기능 요구사항 상세

### 4.1 성능 요구사항 (SRS-NFR-100)

| ID | 요구사항 | 목표값 | 측정 방법 | PRD 추적 |
|----|---------|--------|----------|----------|
| SRS-NFR-101 | 4K 30분 영상 HW 변환 | ≤5분 | 벤치마크 | NFR-P01 |
| SRS-NFR-102 | 1080p 10분 영상 HW 변환 | ≤30초 | 벤치마크 | NFR-P02 |
| SRS-NFR-103 | CPU 사용률 (HW 모드) | ≤30% | Activity Monitor | NFR-P03 |
| SRS-NFR-104 | 메모리 사용량 | ≤1GB | Activity Monitor | NFR-P04 |
| SRS-NFR-105 | 코덱 감지 시간 | ≤500ms | 단위 테스트 | - |
| SRS-NFR-106 | Photos 스캔 (1000개) | ≤30초 | 벤치마크 | - |

**성능 측정 스크립트**:
```python
def benchmark_conversion(
    input_file: Path,
    iterations: int = 3
) -> BenchmarkResult:
    """
    변환 성능 벤치마크

    측정 항목:
    - 변환 시간 (초)
    - CPU 사용률 (%)
    - 메모리 사용량 (MB)
    - 변환 속도 (실시간 대비 배율)
    """
```

### 4.2 안정성 요구사항 (SRS-NFR-200)

| ID | 요구사항 | 목표값 | 측정 방법 | PRD 추적 |
|----|---------|--------|----------|----------|
| SRS-NFR-201 | 변환 성공률 | ≥99% | 배치 테스트 | NFR-R01 |
| SRS-NFR-202 | 메타데이터 보존율 | 100% | 자동 검증 | NFR-R02 |
| SRS-NFR-203 | 서비스 가동률 | ≥99.9% | 로그 분석 | NFR-R03 |
| SRS-NFR-204 | 에러 복구 성공률 | ≥95% | 재시도 로그 | NFR-R04 |
| SRS-NFR-205 | 데이터 무손실 | 100% | 해시 비교 | - |

### 4.3 사용성 요구사항 (SRS-NFR-300)

| ID | 요구사항 | 목표값 | 측정 방법 | PRD 추적 |
|----|---------|--------|----------|----------|
| SRS-NFR-301 | 초기 설정 시간 | ≤5분 | 사용자 테스트 | NFR-U01 |
| SRS-NFR-302 | CLI 학습 시간 | ≤10분 | 사용자 테스트 | NFR-U02 |
| SRS-NFR-303 | 에러 메시지 명확성 | ≥90% 이해도 | 설문 | NFR-U03 |
| SRS-NFR-304 | 도움말 완전성 | 모든 명령 커버 | 문서 검토 | - |

### 4.4 호환성 요구사항 (SRS-NFR-400)

| ID | 요구사항 | 목표값 | 비고 | PRD 추적 |
|----|---------|--------|------|----------|
| SRS-NFR-401 | macOS 버전 | 12.0+ | Monterey 이상 | NFR-C01 |
| SRS-NFR-402 | Python 버전 | 3.10+ | osxphotos 요구 | NFR-C02 |
| SRS-NFR-403 | FFmpeg 버전 | 5.0+ | hevc_videotoolbox | NFR-C03 |
| SRS-NFR-404 | ExifTool 버전 | 12.0+ | GPS 태그 지원 | - |
| SRS-NFR-405 | osxphotos 버전 | 0.70+ | Photos 16 지원 | - |
| SRS-NFR-406 | 비디오 포맷 | .mp4/.mov/.m4v | H.264 코덱 | NFR-C04 |

### 4.5 보안 요구사항 (SRS-NFR-500)

| ID | 요구사항 | 구현 방법 | PRD 추적 |
|----|---------|----------|----------|
| SRS-NFR-501 | Photos 최소 권한 | 읽기 전용 접근 | NFR-S01 |
| SRS-NFR-502 | 임시 파일 보안 | 사용 후 즉시 삭제 | NFR-S02 |
| SRS-NFR-503 | 설정 파일 보안 | 0600 권한 설정 | NFR-S03 |
| SRS-NFR-504 | 로그 개인정보 | 파일명만 기록, 경로 해시화 | - |
| SRS-NFR-505 | 외부 통신 없음 | 로컬 처리만 수행 | - |

---

## 5. 외부 인터페이스 요구사항

### 5.1 사용자 인터페이스

#### SRS-UI-001: CLI 인터페이스

**입력 형식**:
```bash
video-converter <command> [options] [arguments]
```

**출력 형식**:

*진행률 표시*:
```
Converting: vacation_2024.mp4
[████████████░░░░░░░░] 60% | 1.2GB → 540MB | ETA: 1:45
```

*결과 요약*:
```
╭─────────────────────────────────────────────╮
│           변환 완료 보고서                   │
├─────────────────────────────────────────────┤
│  처리 영상:     15개                         │
│  성공:          14개                         │
│  실패:          1개                          │
│  건너뜀:        3개 (이미 HEVC)              │
├─────────────────────────────────────────────┤
│  원본 크기:     35.2 GB                      │
│  변환 크기:     15.8 GB                      │
│  절약 공간:     19.4 GB (55%)                │
╰─────────────────────────────────────────────╯
```

*에러 표시*:
```
❌ Error: vacation_corrupted.mp4
   원인: Invalid data found when processing input
   해결: 파일이 손상되었습니다. 원본 확인 필요
   위치: ~/Videos/Failed/vacation_corrupted.mp4
```

### 5.2 소프트웨어 인터페이스

#### SRS-SW-001: FFmpeg 인터페이스

**프로세스 실행**:
```python
class FFmpegRunner:
    """FFmpeg 프로세스 실행 관리"""

    def run(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> FFmpegResult:
        """
        FFmpeg 명령 실행

        Parameters:
            command: FFmpeg 명령 인자 리스트
            timeout: 타임아웃 (초)
            progress_callback: 진행률 콜백 함수

        Returns:
            FFmpegResult:
            - success: bool
            - exit_code: int
            - stdout: str
            - stderr: str
            - duration: float
        """
```

#### SRS-SW-002: osxphotos 인터페이스

**라이브러리 접근**:
```python
def get_photos_db() -> osxphotos.PhotosDB:
    """
    Photos 라이브러리 데이터베이스 연결

    기본 경로: ~/Pictures/Photos Library.photoslibrary
    """

def query_videos(
    db: osxphotos.PhotosDB,
    **filters
) -> List[osxphotos.PhotoInfo]:
    """
    비디오 쿼리

    Filters:
        movies: bool = True
        since_date: datetime
        albums: List[str]
    """
```

#### SRS-SW-003: ExifTool 인터페이스

**메타데이터 연산**:
```python
class ExifToolRunner:
    """ExifTool 명령 실행"""

    def read_metadata(self, path: Path) -> Dict[str, Any]:
        """메타데이터 읽기: exiftool -json <path>"""

    def copy_metadata(self, source: Path, target: Path) -> None:
        """메타데이터 복사: exiftool -tagsFromFile <source> <target>"""

    def copy_gps(self, source: Path, target: Path) -> None:
        """GPS 복사: exiftool -tagsFromFile <source> "-GPS*" <target>"""
```

### 5.3 하드웨어 인터페이스

#### SRS-HW-001: VideoToolbox

**요구사항**:
- Apple Silicon (M1/M2/M3/M4) 프로세서
- macOS 12.0+ (VideoToolbox HEVC 인코딩 지원)

**확인 방법**:
```bash
ffmpeg -encoders 2>/dev/null | grep hevc_videotoolbox
# 출력: V....D hevc_videotoolbox    VideoToolbox H.265 Encoder
```

### 5.4 통신 인터페이스

본 시스템은 네트워크 통신을 사용하지 않음. 모든 처리는 로컬에서 수행.

---

## 6. 데이터 요구사항

### 6.1 데이터 모델

#### 6.1.1 설정 데이터

**config.json 스키마**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "encoding", "paths"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "encoding": {
      "type": "object",
      "properties": {
        "mode": { "enum": ["hardware", "software"] },
        "quality": { "type": "integer", "minimum": 1, "maximum": 100 },
        "crf": { "type": "integer", "minimum": 0, "maximum": 51 },
        "preset": { "enum": ["ultrafast", "superfast", "veryfast",
                            "faster", "fast", "medium", "slow",
                            "slower", "veryslow"] }
      }
    },
    "paths": {
      "type": "object",
      "properties": {
        "output": { "type": "string" },
        "processed": { "type": "string" },
        "failed": { "type": "string" },
        "log": { "type": "string" }
      }
    },
    "automation": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean" },
        "schedule_hour": { "type": "integer", "minimum": 0, "maximum": 23 },
        "schedule_minute": { "type": "integer", "minimum": 0, "maximum": 59 }
      }
    },
    "processing": {
      "type": "object",
      "properties": {
        "max_concurrent": { "type": "integer", "minimum": 1, "maximum": 4 },
        "validate_quality": { "type": "boolean" },
        "min_vmaf": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    }
  }
}
```

#### 6.1.2 변환 기록 데이터

**SQLite 스키마**:
```sql
-- 변환 이력 테이블
CREATE TABLE conversion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_uuid TEXT NOT NULL,               -- Photos UUID
    original_filename TEXT NOT NULL,
    original_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    original_size INTEGER NOT NULL,         -- bytes
    converted_size INTEGER NOT NULL,        -- bytes
    compression_ratio REAL NOT NULL,
    conversion_mode TEXT NOT NULL,          -- 'hardware' or 'software'
    quality_setting INTEGER,
    vmaf_score REAL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    duration_seconds REAL NOT NULL,
    status TEXT NOT NULL,                   -- 'success' or 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_video_uuid ON conversion_history(video_uuid);
CREATE INDEX idx_status ON conversion_history(status);
CREATE INDEX idx_completed_at ON conversion_history(completed_at);

-- 세션 테이블 (배치 작업 단위)
CREATE TABLE conversion_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid TEXT NOT NULL UNIQUE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_videos INTEGER NOT NULL,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    total_original_size INTEGER DEFAULT 0,
    total_converted_size INTEGER DEFAULT 0,
    status TEXT NOT NULL                    -- 'running', 'completed', 'failed'
);
```

### 6.2 데이터 저장소

| 데이터 유형 | 위치 | 형식 |
|------------|------|------|
| 사용자 설정 | ~/.config/video_converter/config.json | JSON |
| 변환 기록 | ~/.config/video_converter/history.db | SQLite |
| 실행 로그 | ~/Library/Logs/video_converter/ | Text |
| 임시 파일 | /tmp/video_converter/ | Binary |

### 6.3 데이터 보존 정책

| 데이터 | 보존 기간 | 정리 방법 |
|--------|----------|----------|
| 변환 기록 | 무기한 | 수동 삭제 |
| 실행 로그 | 30일 | 자동 로테이션 |
| 임시 파일 | 24시간 | 자동 삭제 |
| 원본 (processed) | 사용자 설정 | 수동 삭제 |

---

## 7. 시스템 제약사항

### 7.1 기술적 제약

| 제약 | 영향 | 대응 방안 |
|------|------|----------|
| Photos 라이브러리 직접 수정 불가 | 변환 파일 별도 저장 | 출력 폴더 명확히 안내 |
| VideoToolbox 품질 제한 | SW 대비 약간 큰 파일 | 품질 프리셋 제공 |
| iCloud 동기화 지연 | 일부 영상 처리 불가 | 재시도, 대기 옵션 |
| launchd ThrottleInterval | 최소 30초 간격 실행 | 배치 처리로 효율화 |

### 7.2 운영 제약

| 제약 | 영향 | 대응 방안 |
|------|------|----------|
| 전원 연결 필요 (노트북) | 배터리 소모 | 전원 상태 확인 |
| 저장 공간 2배 필요 | 변환 중 공간 부족 가능 | 사전 공간 확인 |
| Mac 전원 켜짐 필요 | 스케줄 누락 가능 | 다음 실행 시 처리 |

### 7.3 규정 준수

| 항목 | 준수 사항 |
|------|----------|
| 개인정보 | 로컬 처리만, 외부 전송 없음 |
| 라이선스 | FFmpeg LGPL, ExifTool GPL, osxphotos MIT |
| 코덱 특허 | H.265는 Apple 기기에서 라이선스됨 |

---

## 8. 요구사항 추적 매트릭스 (RTM)

### 8.1 PRD → SRS 추적

| PRD ID | PRD 명칭 | SRS ID | SRS 명칭 | 상태 |
|--------|---------|--------|---------|------|
| **사용자 스토리 → 기능** |
| US-101 | 설치 스크립트 | SRS-701 | CLI install 명령 | 매핑 |
| US-201 | H.264 자동 찾기 | SRS-101, SRS-301 | 코덱 감지, Photos 스캔 | 매핑 |
| US-203 | 진행률 확인 | SRS-201 | 진행률 모니터링 | 매핑 |
| US-204 | 변환 중 성능 | SRS-NFR-103 | CPU 사용률 ≤30% | 매핑 |
| US-205 | 중복 변환 방지 | SRS-301 | 변환 기록 관리 | 매핑 |
| US-301 | 날짜 보존 | SRS-401, SRS-402 | 메타데이터 처리 | 매핑 |
| US-302 | GPS 보존 | SRS-401, SRS-402 | GPS 특수 처리 | 매핑 |
| US-401 | 스케줄 실행 | SRS-601 | launchd 스케줄 | 매핑 |
| US-402 | 폴더 감시 | SRS-602 | WatchPaths | 매핑 |
| US-403 | 완료 알림 | SRS-603 | macOS 알림 | 매핑 |
| US-501 | 원본 보존 | SRS-801 | 원본 보존 정책 | 매핑 |
| US-502 | 실패 시 원본 유지 | SRS-802 | 에러 복구 | 매핑 |
| **기능 요구사항 → 상세** |
| FR-001 | H.264 감지 | SRS-101 | 코덱 감지 | 매핑 |
| FR-002 | H.265 HW 변환 | SRS-201 | 하드웨어 변환 | 매핑 |
| FR-003 | H.265 SW 변환 | SRS-202 | 소프트웨어 변환 | 매핑 |
| FR-004 | 진행률 표시 | SRS-201 | 진행률 모니터링 | 매핑 |
| FR-101 | Photos 스캔 | SRS-301 | Photos 스캔 | 매핑 |
| FR-102 | 비디오 필터링 | SRS-301 | H.264 필터링 | 매핑 |
| FR-103 | 비디오 내보내기 | SRS-301 | export_video() | 매핑 |
| FR-104 | iCloud 다운로드 | SRS-302 | iCloud 다운로드 | 매핑 |
| FR-201 | 메타데이터 추출 | SRS-401 | 메타데이터 추출 | 매핑 |
| FR-202 | 메타데이터 적용 | SRS-401 | 메타데이터 적용 | 매핑 |
| FR-203 | GPS 보존 | SRS-401 | GPS 특수 처리 | 매핑 |
| FR-204 | 타임스탬프 동기화 | SRS-401 | sync_timestamps() | 매핑 |
| FR-301 | 무결성 검사 | SRS-501 | 파일 무결성 검사 | 매핑 |
| FR-302 | 속성 비교 | SRS-501 | 속성 비교 | 매핑 |
| FR-303 | 압축률 검사 | SRS-501 | 압축률 검사 | 매핑 |
| FR-304 | VMAF 측정 | SRS-501 | VMAF 측정 | 매핑 |
| FR-401 | 스케줄 실행 | SRS-601 | 스케줄 기반 실행 | 매핑 |
| FR-402 | 폴더 감시 | SRS-602 | 폴더 감시 실행 | 매핑 |
| FR-403 | 알림 발송 | SRS-603 | macOS 알림 | 매핑 |
| FR-404 | 서비스 관리 | SRS-601 | LaunchdManager | 매핑 |
| FR-501 | 단일 변환 CLI | SRS-701 | convert 명령 | 매핑 |
| FR-502 | 배치 변환 CLI | SRS-701 | run 명령 | 매핑 |
| FR-503 | 상태 조회 CLI | SRS-701 | status 명령 | 매핑 |
| FR-504 | 통계 조회 CLI | SRS-701 | stats 명령 | 매핑 |
| FR-505 | 서비스 설치 CLI | SRS-701 | install 명령 | 매핑 |
| FR-601 | 원본 보존 | SRS-801 | 원본 보존 | 매핑 |
| FR-602 | 재시도 로직 | SRS-802 | 에러 복구 | 매핑 |
| FR-603 | 실패 격리 | SRS-801 | failed 폴더 | 매핑 |
| **비기능 요구사항** |
| NFR-P01 | 4K 변환 시간 | SRS-NFR-101 | ≤5분 | 매핑 |
| NFR-P02 | 1080p 변환 시간 | SRS-NFR-102 | ≤30초 | 매핑 |
| NFR-P03 | CPU 사용률 | SRS-NFR-103 | ≤30% | 매핑 |
| NFR-P04 | 메모리 사용량 | SRS-NFR-104 | ≤1GB | 매핑 |
| NFR-R01 | 변환 성공률 | SRS-NFR-201 | ≥99% | 매핑 |
| NFR-R02 | 메타데이터 보존율 | SRS-NFR-202 | 100% | 매핑 |
| NFR-U01 | 초기 설정 시간 | SRS-NFR-301 | ≤5분 | 매핑 |
| NFR-C01 | macOS 버전 | SRS-NFR-401 | 12.0+ | 매핑 |
| NFR-C02 | Python 버전 | SRS-NFR-402 | 3.10+ | 매핑 |
| NFR-S01 | Photos 권한 | SRS-NFR-501 | 읽기 전용 | 매핑 |

### 8.2 SRS → 테스트 케이스 추적

| SRS ID | 테스트 케이스 ID | 테스트 유형 | 검증 방법 |
|--------|-----------------|------------|----------|
| SRS-101 | TC-101-01 | 단위 | H.264 코덱 감지 확인 |
| SRS-101 | TC-101-02 | 단위 | HEVC 코덱 감지 확인 |
| SRS-101 | TC-101-03 | 단위 | 알 수 없는 코덱 에러 처리 |
| SRS-201 | TC-201-01 | 통합 | HW 변환 성공 확인 |
| SRS-201 | TC-201-02 | 통합 | 품질 설정 적용 확인 |
| SRS-201 | TC-201-03 | 통합 | 재시도 로직 동작 확인 |
| SRS-301 | TC-301-01 | 통합 | Photos 스캔 동작 확인 |
| SRS-301 | TC-301-02 | 통합 | H.264 필터링 확인 |
| SRS-401 | TC-401-01 | 통합 | 메타데이터 추출 확인 |
| SRS-401 | TC-401-02 | 통합 | GPS 보존 확인 |
| SRS-402 | TC-402-01 | 통합 | 메타데이터 검증 확인 |
| SRS-501 | TC-501-01 | 통합 | 무결성 검사 확인 |
| SRS-501 | TC-501-02 | 통합 | 속성 비교 확인 |
| SRS-601 | TC-601-01 | E2E | 스케줄 실행 확인 |
| SRS-603 | TC-603-01 | E2E | 알림 발송 확인 |
| SRS-701 | TC-701-01 | E2E | CLI 전체 플로우 |
| SRS-NFR-101 | TC-NFR-01 | 성능 | 4K 변환 시간 측정 |
| SRS-NFR-103 | TC-NFR-03 | 성능 | CPU 사용률 측정 |
| SRS-NFR-201 | TC-NFR-11 | 안정성 | 변환 성공률 측정 |
| SRS-NFR-202 | TC-NFR-12 | 안정성 | 메타데이터 보존율 측정 |

---

## 9. 검증 및 유효성 확인

### 9.1 검증 방법

| 요구사항 유형 | 검증 방법 | 도구 |
|--------------|----------|------|
| 기능 요구사항 | 단위/통합 테스트 | pytest |
| 성능 요구사항 | 벤치마크 테스트 | custom scripts |
| 안정성 요구사항 | 장기 실행 테스트 | CI/CD |
| 사용성 요구사항 | 사용자 테스트 | 설문/관찰 |

### 9.2 수용 기준

#### 기능 수용 기준

| ID | 기준 | 검증 |
|----|------|------|
| AC-001 | H.264 코덱이 올바르게 감지됨 | 10개 샘플 100% 정확 |
| AC-002 | 변환된 파일이 HEVC 코덱임 | FFprobe 확인 |
| AC-003 | GPS 좌표가 소수점 6자리까지 일치 | ExifTool 비교 |
| AC-004 | 날짜가 1초 이내로 일치 | ExifTool 비교 |
| AC-005 | 재생 시간 차이 1초 이내 | FFprobe 비교 |

#### 성능 수용 기준

| ID | 기준 | 측정 |
|----|------|------|
| AC-P01 | 4K 30분 영상 HW 변환 ≤5분 | 3회 평균 |
| AC-P02 | CPU 사용률 ≤30% (HW 모드) | 변환 중 평균 |
| AC-P03 | 메모리 ≤1GB | 변환 중 최대 |

### 9.3 테스트 데이터 요구사항

| 샘플 ID | 해상도 | 길이 | 코덱 | 특성 | 용도 |
|--------|--------|------|------|------|------|
| SAMPLE-001 | 1080p | 10초 | H.264 | 표준 | 빠른 테스트 |
| SAMPLE-002 | 4K | 1분 | H.264 | 표준 | 성능 테스트 |
| SAMPLE-003 | 1080p | 30초 | H.264 | GPS 포함 | 메타데이터 테스트 |
| SAMPLE-004 | 1080p | 10초 | HEVC | 표준 | 스킵 테스트 |
| SAMPLE-005 | 4K | 30분 | H.264 | 표준 | 장시간 테스트 |
| SAMPLE-006 | 1080p | 10초 | H.264 | 손상됨 | 에러 처리 테스트 |

---

## 10. 부록

### 10.1 용어 정의

| 용어 | 정의 |
|------|------|
| H.264/AVC | Advanced Video Coding, 2003년 표준화된 비디오 코덱 |
| H.265/HEVC | High Efficiency Video Coding, H.264 대비 50% 향상 |
| VideoToolbox | Apple 하드웨어 비디오 인코딩/디코딩 프레임워크 |
| CRF | Constant Rate Factor, 품질 기반 인코딩 설정 |
| VMAF | Video Multimethod Assessment Fusion, 품질 지표 |
| launchd | macOS 서비스 관리 프레임워크 |
| osxphotos | Python Photos 라이브러리 접근 도구 |
| ExifTool | 메타데이터 읽기/쓰기 도구 |
| FFmpeg | 멀티미디어 처리 프레임워크 |
| FFprobe | FFmpeg 미디어 분석 도구 |

### 10.2 에러 코드 정의

| 코드 | 설명 | 재시도 | 사용자 메시지 |
|------|------|--------|--------------|
| E-101 | 파일 미존재 | No | 파일을 찾을 수 없습니다 |
| E-102 | FFprobe 실행 실패 | Yes | 미디어 분석 실패 |
| E-103 | 비디오 스트림 없음 | No | 비디오가 없는 파일입니다 |
| E-104 | 알 수 없는 코덱 | No | 지원하지 않는 코덱입니다 |
| E-201 | FFmpeg 실행 실패 | Yes | 변환 중 오류 발생 |
| E-202 | 디스크 공간 부족 | No | 저장 공간이 부족합니다 |
| E-203 | 입력 파일 손상 | No | 파일이 손상되었습니다 |
| E-204 | 출력 파일 생성 실패 | Yes | 출력 파일 생성 실패 |
| E-205 | 인코더 초기화 실패 | Yes | 인코더 오류 |
| E-301 | Photos 접근 거부 | No | Photos 접근 권한 필요 |
| E-302 | iCloud 다운로드 실패 | Yes | iCloud 다운로드 실패 |
| E-401 | 메타데이터 추출 실패 | Yes | 메타데이터 읽기 실패 |
| E-402 | 메타데이터 적용 실패 | Yes | 메타데이터 쓰기 실패 |
| E-501 | 검증 실패 | Yes | 변환 결과 검증 실패 |
| E-601 | launchd 등록 실패 | No | 서비스 설치 실패 |

### 10.3 참조 문서

- PRD.md - 제품 요구사항 정의서
- development-plan.md - 개발 계획서
- 01-system-architecture.md - 시스템 아키텍처
- 02-sequence-diagrams.md - 시퀀스 다이어그램
- 03-data-flow-and-states.md - 데이터 흐름 및 상태
- 04-processing-procedures.md - 처리 절차
- 01-codec-comparison.md - 코덱 비교
- 02-ffmpeg-hevc-encoding.md - FFmpeg 인코딩 가이드
- 03-videotoolbox-hardware-acceleration.md - 하드웨어 가속
- 04-macos-photos-access.md - Photos 접근 방법
- 05-macos-automation-methods.md - macOS 자동화

---

## 승인

| 역할 | 이름 | 서명 | 날짜 |
|------|------|------|------|
| Tech Lead | | | |
| Architect | | | |
| QA Lead | | | |

---

*이 문서는 개발 진행에 따라 업데이트됩니다.*
