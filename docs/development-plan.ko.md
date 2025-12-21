# Video Converter 개발 계획서

**버전**: 1.0.0
**작성일**: 2025-12-21
**상태**: 계획 단계

### 관련 문서

| 문서 | 설명 |
|------|------|
| [PRD.ko.md](PRD.ko.md) | 제품 요구사항 정의서 |
| [SRS.ko.md](SRS.ko.md) | 소프트웨어 요구사항 명세서 |
| [SDS.ko.md](SDS.ko.md) | 소프트웨어 설계 명세서 |
| [architecture/](architecture/) | 아키텍처 다이어그램 및 설계 |

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

macOS Photos 라이브러리에 저장된 H.264 코덱 동영상을 H.265(HEVC)로 자동 변환하여 저장 공간을 절약하는 시스템을 개발합니다.

### 1.2 핵심 가치

| 항목 | 목표 |
|------|------|
| **저장 공간 절약** | 50% 이상 파일 크기 감소 |
| **화질 유지** | VMAF 93+ (시각적 무손실) |
| **메타데이터 보존** | GPS, 날짜, 앨범 정보 100% 보존 |
| **완전 자동화** | 사용자 개입 최소화 |

### 1.3 대상 사용자

- macOS 환경에서 많은 동영상을 관리하는 개인 사용자
- Apple Photos 앱을 주로 사용하는 사용자
- 저장 공간 최적화가 필요한 사용자

---

## 2. 기술 스택

### 2.1 개발 언어 및 프레임워크

| 구성 요소 | 기술 | 버전 요구 사항 |
|----------|------|---------------|
| 주 개발 언어 | Python | 3.10+ |
| Photos 접근 | osxphotos | 0.70+ |
| 비디오 변환 | FFmpeg + VideoToolbox | 5.0+ |
| 메타데이터 처리 | ExifTool | 12.0+ |
| 자동화 | launchd | macOS 내장 |

### 2.2 시스템 요구 사항

| 항목 | 최소 | 권장 |
|------|------|------|
| macOS | 12.0 (Monterey) | 14.0+ (Sonoma) |
| CPU | Apple M1 | Apple M2 Pro 이상 |
| RAM | 8GB | 16GB+ |
| 저장 공간 | 변환 대상의 2배 | 변환 대상의 3배 |

### 2.3 프로젝트 구조

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── __main__.py              # CLI 엔트리포인트
│       ├── core/                    # 핵심 로직
│       │   ├── orchestrator.py
│       │   ├── config.py
│       │   └── logger.py
│       ├── extractors/              # 비디오 추출
│       │   ├── base.py
│       │   ├── photos_extractor.py
│       │   └── folder_extractor.py
│       ├── converters/              # 변환 엔진
│       │   ├── base.py
│       │   ├── hardware.py
│       │   └── software.py
│       ├── processors/              # 후처리
│       │   ├── codec_detector.py
│       │   ├── metadata.py
│       │   └── validator.py
│       ├── automation/              # 자동화
│       │   ├── launchd.py
│       │   └── folder_action.py
│       ├── reporters/               # 보고/알림
│       │   ├── statistics.py
│       │   └── notifier.py
│       └── utils/                   # 유틸리티
│           ├── file_utils.py
│           └── command_utils.py
├── config/
│   ├── default.json
│   └── launchd/
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 3. 개발 마일스톤

### 3.1 전체 일정 개요

```
Phase 1: Foundation (2주)
    ├── M1: 프로젝트 설정 및 핵심 유틸리티 (Week 1)
    └── M2: 코덱 감지 및 기본 변환 (Week 2)

Phase 2: Core Features (3주)
    ├── M3: Photos 라이브러리 통합 (Week 3)
    ├── M4: 메타데이터 처리 (Week 4)
    └── M5: 품질 검증 시스템 (Week 5)

Phase 3: Automation (2주)
    ├── M6: 배치 처리 및 큐 관리 (Week 6)
    └── M7: launchd 자동화 (Week 7)

Phase 4: Polish (1주)
    └── M8: CLI, 알림, 최종 테스트 (Week 8)
```

### 3.2 마일스톤별 상세 계획

---

#### Milestone 1: 프로젝트 설정 및 핵심 유틸리티 (Week 1)

**목표**: 프로젝트 기반 구조 확립 및 기본 유틸리티 구현

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 1.1 | 프로젝트 구조 생성 및 pyproject.toml 설정 | High | 2h |
| 1.2 | 설정 관리 시스템 (config.py) 구현 | High | 4h |
| 1.3 | 로깅 시스템 (logger.py) 구현 | High | 3h |
| 1.4 | 파일 유틸리티 (file_utils.py) 구현 | Medium | 4h |
| 1.5 | 커맨드 실행 유틸리티 (command_utils.py) 구현 | Medium | 4h |
| 1.6 | 의존성 확인 스크립트 작성 | Medium | 2h |

**산출물**:
- [x] 프로젝트 디렉토리 구조
- [x] pyproject.toml 및 개발 환경 설정
- [x] 설정 파일 로드/저장 기능
- [x] 구조화된 로깅 시스템
- [x] 파일 및 커맨드 유틸리티

**완료 기준**:
```python
# 설정 로드 테스트
from video_converter.core.config import Config
config = Config.load("~/.config/video_converter/config.json")
assert config.encoding.mode in ("hardware", "software")

# 커맨드 실행 테스트
from video_converter.utils.command_utils import run_command
result = run_command(["ffmpeg", "-version"])
assert result.success
```

---

#### Milestone 2: 코덱 감지 및 기본 변환 (Week 2)

**목표**: FFprobe를 통한 코덱 감지 및 기본 FFmpeg 변환 구현

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 2.1 | 코덱 감지기 (codec_detector.py) 구현 | High | 6h |
| 2.2 | 변환기 베이스 클래스 (converters/base.py) 설계 | High | 4h |
| 2.3 | 하드웨어 변환기 (hardware.py) 구현 | High | 8h |
| 2.4 | 소프트웨어 변환기 (software.py) 구현 | Medium | 6h |
| 2.5 | 변환 진행률 모니터링 구현 | Medium | 4h |
| 2.6 | 단일 파일 변환 CLI 명령 구현 | Medium | 3h |

**산출물**:
- [x] H.264/H.265 코덱 감지 기능
- [x] VideoToolbox 하드웨어 인코딩 변환
- [x] libx265 소프트웨어 인코딩 변환
- [x] 실시간 진행률 콜백

**완료 기준**:
```bash
# 단일 파일 변환 테스트
python -m video_converter convert input.mp4 output.mp4 --mode hardware

# 코덱 확인
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name \
  -of default=noprint_wrappers=1:nokey=1 output.mp4
# 출력: hevc
```

---

#### Milestone 3: Photos 라이브러리 통합 (Week 3)

**목표**: osxphotos를 통한 Photos 라이브러리 접근 및 비디오 추출

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 3.1 | 추출기 베이스 클래스 (extractors/base.py) 설계 | High | 3h |
| 3.2 | Photos 추출기 (photos_extractor.py) 구현 | High | 10h |
| 3.3 | H.264 비디오 필터링 로직 구현 | High | 4h |
| 3.4 | iCloud 다운로드 처리 구현 | Medium | 6h |
| 3.5 | 폴더 추출기 (folder_extractor.py) 구현 | Medium | 4h |
| 3.6 | 변환 기록 관리 (중복 변환 방지) | Medium | 4h |

**산출물**:
- [x] Photos 라이브러리 비디오 목록 조회
- [x] H.264 코덱 비디오만 필터링
- [x] 원본 비디오 내보내기
- [x] iCloud 비디오 다운로드 처리
- [x] 변환 기록 저장/조회

**완료 기준**:
```python
from video_converter.extractors.photos_extractor import PhotosExtractor

extractor = PhotosExtractor()
videos = extractor.extract_videos(filter_codec="h264")

for video in videos[:5]:
    print(f"{video.original_name}: {video.codec}, {video.size/1e6:.1f}MB")
```

---

#### Milestone 4: 메타데이터 처리 (Week 4)

**목표**: ExifTool을 활용한 완전한 메타데이터 보존

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 4.1 | 메타데이터 관리자 (metadata.py) 설계 | High | 4h |
| 4.2 | 메타데이터 추출 구현 | High | 6h |
| 4.3 | 메타데이터 적용 구현 | High | 6h |
| 4.4 | GPS 좌표 보존 특수 처리 | High | 4h |
| 4.5 | 파일 타임스탬프 동기화 | Medium | 2h |
| 4.6 | 메타데이터 검증 로직 | Medium | 4h |

**산출물**:
- [x] 원본 → 변환 파일 메타데이터 복사
- [x] GPS, 날짜, 카메라 정보 보존
- [x] 파일 시스템 타임스탬프 동기화
- [x] 메타데이터 무결성 검증

**완료 기준**:
```bash
# 원본과 변환 파일의 메타데이터 비교
exiftool -CreateDate -GPSLatitude -GPSLongitude original.mp4
exiftool -CreateDate -GPSLatitude -GPSLongitude converted.mp4
# 두 출력이 동일해야 함
```

---

#### Milestone 5: 품질 검증 시스템 (Week 5)

**목표**: 변환 품질 보장을 위한 검증 시스템 구현

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 5.1 | 검증기 (validator.py) 설계 | High | 4h |
| 5.2 | 파일 무결성 검사 구현 | High | 4h |
| 5.3 | 속성 비교 검사 (해상도, 프레임레이트, 재생시간) | High | 4h |
| 5.4 | 압축률 검사 구현 | Medium | 2h |
| 5.5 | VMAF 품질 측정 구현 (선택적) | Low | 8h |
| 5.6 | 검증 실패 시 재시도 로직 | Medium | 4h |

**산출물**:
- [x] 변환 파일 무결성 검증
- [x] 원본 대비 속성 일치 확인
- [x] 압축률 정상 범위 확인
- [x] (선택) VMAF 점수 계산

**완료 기준**:
```python
from video_converter.processors.validator import QualityValidator

validator = QualityValidator()
result = validator.validate(original_path, converted_path)

assert result.valid
assert result.compression_ratio > 0.2  # 20% 이상
assert result.compression_ratio < 0.8  # 80% 이하
```

---

#### Milestone 6: 배치 처리 및 큐 관리 (Week 6)

**목표**: 다수 비디오의 효율적인 배치 처리 시스템

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 6.1 | 오케스트레이터 (orchestrator.py) 설계 | High | 6h |
| 6.2 | 처리 큐 관리 구현 | High | 6h |
| 6.3 | 병렬 처리 지원 (선택적) | Medium | 6h |
| 6.4 | 재시도 로직 및 지수 백오프 구현 | High | 4h |
| 6.5 | 실패 파일 격리 처리 | Medium | 3h |
| 6.6 | 세션 상태 저장/복구 | Medium | 4h |

**산출물**:
- [x] 전체 변환 워크플로우 오케스트레이션
- [x] 처리 큐 관리
- [x] 에러 복구 및 재시도
- [x] 세션 체크포인트

**완료 기준**:
```python
from video_converter.core.orchestrator import Orchestrator

orchestrator = Orchestrator(config)
result = orchestrator.run()

print(f"성공: {result.successful}")
print(f"실패: {result.failed}")
print(f"건너뜀: {result.skipped}")
print(f"절약된 공간: {result.saved_space / 1e9:.2f}GB")
```

---

#### Milestone 7: launchd 자동화 (Week 7)

**목표**: macOS launchd를 통한 완전 자동화

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 7.1 | launchd plist 템플릿 생성 | High | 4h |
| 7.2 | launchd 관리자 (launchd.py) 구현 | High | 6h |
| 7.3 | 설치/제거 스크립트 작성 | High | 4h |
| 7.4 | WatchPaths 폴더 감시 설정 | Medium | 3h |
| 7.5 | StartCalendarInterval 스케줄 설정 | Medium | 3h |
| 7.6 | Folder Action 스크립트 (대안) | Low | 4h |

**산출물**:
- [x] launchd 서비스 plist 파일
- [x] 자동 설치/제거 스크립트
- [x] 폴더 감시 기반 자동 실행
- [x] 스케줄 기반 자동 실행

**완료 기준**:
```bash
# 설치
./scripts/install.sh

# 서비스 상태 확인
launchctl list | grep videoconverter
# 출력: -    0    com.user.videoconverter

# 수동 트리거 테스트
launchctl start com.user.videoconverter
```

---

#### Milestone 8: CLI, 알림, 최종 테스트 (Week 8)

**목표**: 사용자 인터페이스 완성 및 전체 시스템 테스트

**작업 항목**:

| # | 작업 | 우선순위 | 예상 시간 |
|---|------|---------|----------|
| 8.1 | CLI 인터페이스 완성 (__main__.py) | High | 8h |
| 8.2 | 통계 리포터 (statistics.py) 구현 | Medium | 4h |
| 8.3 | macOS 알림 시스템 (notifier.py) 구현 | Medium | 4h |
| 8.4 | 통합 테스트 작성 | High | 8h |
| 8.5 | 문서화 (README.md, 사용 가이드) | Medium | 4h |
| 8.6 | 최종 버그 수정 및 최적화 | High | 8h |

**산출물**:
- [x] 완전한 CLI 인터페이스
- [x] 변환 통계 보고서
- [x] macOS 알림 연동
- [x] 사용자 문서

**완료 기준**:
```bash
# CLI 도움말
python -m video_converter --help

# 전체 실행
python -m video_converter run --mode photos

# 상태 확인
python -m video_converter status

# 통계 보기
python -m video_converter stats --last-week
```

---

## 4. 모듈별 구현 상세

### 4.1 Core 모듈

#### config.py

```python
@dataclass
class EncodingConfig:
    mode: Literal["hardware", "software"]
    quality: int = 45      # hardware mode (1-100)
    crf: int = 22          # software mode (0-51)
    preset: str = "slow"

@dataclass
class PathsConfig:
    input_dir: Path
    output_dir: Path
    processed_dir: Path
    failed_dir: Path
    log_dir: Path

@dataclass
class Config:
    version: str
    encoding: EncodingConfig
    paths: PathsConfig
    automation: AutomationConfig
    photos: PhotosConfig
    processing: ProcessingConfig
    notification: NotificationConfig

    @classmethod
    def load(cls, path: Path) -> "Config": ...
    def save(self, path: Path) -> None: ...
```

#### orchestrator.py

```python
class Orchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.extractor = self._create_extractor()
        self.converter = self._create_converter()
        self.validator = QualityValidator(config.processing)

    def run(self) -> BatchResult:
        """전체 변환 배치 실행"""
        videos = self.extractor.extract_videos(filter_codec="h264")
        results = []

        for video in videos:
            result = self._process_single(video)
            results.append(result)

        return self._generate_summary(results)

    def run_single(self, video_path: Path) -> ConversionResult:
        """단일 비디오 변환"""
        ...
```

### 4.2 Converters 모듈

#### hardware.py (VideoToolbox)

```python
class HardwareConverter(VideoConverter):
    def build_command(self, input: Path, output: Path) -> List[str]:
        return [
            "ffmpeg", "-y", "-i", str(input),
            "-c:v", "hevc_videotoolbox",
            "-q:v", str(self.config.quality),
            "-tag:v", "hvc1",
            "-c:a", "copy",
            "-map_metadata", "0",
            "-movflags", "use_metadata_tags",
            "-progress", "pipe:1",
            str(output)
        ]
```

#### software.py (libx265)

```python
class SoftwareConverter(VideoConverter):
    def build_command(self, input: Path, output: Path) -> List[str]:
        return [
            "ffmpeg", "-y", "-i", str(input),
            "-c:v", "libx265",
            "-crf", str(self.config.crf),
            "-preset", self.config.preset,
            "-c:a", "copy",
            "-map_metadata", "0",
            str(output)
        ]
```

### 4.3 Processors 모듈

#### metadata.py

```python
class MetadataManager:
    def extract(self, path: Path) -> dict:
        """ExifTool로 메타데이터 추출"""
        result = subprocess.run(
            ["exiftool", "-json", str(path)],
            capture_output=True, text=True
        )
        return json.loads(result.stdout)[0]

    def apply(self, source: Path, target: Path) -> None:
        """소스에서 타겟으로 메타데이터 복사"""
        subprocess.run([
            "exiftool", "-overwrite_original",
            "-tagsFromFile", str(source),
            "-all:all",
            str(target)
        ])

    def sync_timestamps(self, source: Path, target: Path) -> None:
        """파일 시스템 타임스탬프 동기화"""
        stat = source.stat()
        os.utime(target, (stat.st_atime, stat.st_mtime))
```

---

## 5. 테스트 계획

### 5.1 테스트 전략

| 테스트 유형 | 커버리지 목표 | 도구 |
|------------|--------------|------|
| 단위 테스트 | 80%+ | pytest |
| 통합 테스트 | 핵심 워크플로우 | pytest |
| E2E 테스트 | 주요 시나리오 | 수동/자동화 |

### 5.2 테스트 케이스

#### 단위 테스트

```python
# tests/test_codec_detector.py
def test_detect_h264():
    detector = CodecDetector()
    result = detector.detect(Path("samples/h264_sample.mp4"))
    assert result == "h264"

def test_detect_hevc():
    detector = CodecDetector()
    result = detector.detect(Path("samples/hevc_sample.mp4"))
    assert result == "hevc"

def test_is_h264():
    detector = CodecDetector()
    assert detector.is_h264(Path("samples/h264_sample.mp4")) is True
    assert detector.is_h264(Path("samples/hevc_sample.mp4")) is False
```

#### 통합 테스트

```python
# tests/test_conversion_workflow.py
def test_full_conversion_workflow(tmp_path):
    config = Config.load_default()
    config.paths.output_dir = tmp_path / "output"

    orchestrator = Orchestrator(config)
    result = orchestrator.run_single(Path("samples/test_video.mp4"))

    assert result.success
    assert result.output_path.exists()
    assert result.compression_ratio < 0.7
```

### 5.3 테스트 데이터

| 샘플 | 해상도 | 길이 | 코덱 | 용도 |
|------|--------|------|------|------|
| short_h264.mp4 | 1080p | 10초 | H.264 | 빠른 테스트 |
| long_h264.mp4 | 4K | 1분 | H.264 | 성능 테스트 |
| with_gps.mp4 | 1080p | 30초 | H.264 | 메타데이터 테스트 |
| already_hevc.mp4 | 1080p | 10초 | HEVC | 스킵 테스트 |

---

## 6. 배포 계획

### 6.1 배포 방식

| 방식 | 대상 | 우선순위 |
|------|------|---------|
| pip install | 개발자/고급 사용자 | Phase 1 |
| Homebrew Formula | macOS 사용자 | Phase 2 |
| 독립 실행형 앱 | 일반 사용자 | Phase 3 (미래) |

### 6.2 설치 스크립트

```bash
#!/bin/bash
# scripts/install.sh

# 1. 의존성 설치
brew install ffmpeg exiftool python@3.12
pip3 install osxphotos

# 2. 패키지 설치
pip3 install video-converter

# 3. 설정 디렉토리 생성
mkdir -p ~/.config/video_converter
mkdir -p ~/Videos/{ToConvert,Converted,Processed,Failed}

# 4. launchd 서비스 등록
video-converter install-service

echo "설치 완료!"
```

### 6.3 릴리스 프로세스

1. 버전 태그 생성
2. CHANGELOG 업데이트
3. PyPI 배포
4. GitHub Release 생성
5. Homebrew Formula 업데이트 (해당 시)

---

## 7. 위험 요소 및 대응 방안

### 7.1 기술적 위험

| 위험 | 가능성 | 영향 | 대응 방안 |
|------|--------|------|----------|
| Photos 라이브러리 스키마 변경 | 중간 | 높음 | osxphotos 업데이트 모니터링, 폴백 구현 |
| FFmpeg 호환성 문제 | 낮음 | 중간 | 버전 고정, 대안 인코더 지원 |
| iCloud 동기화 충돌 | 중간 | 중간 | 안전한 파일 잠금, 재시도 로직 |
| 대용량 파일 메모리 이슈 | 중간 | 중간 | 스트리밍 처리, 메모리 모니터링 |

### 7.2 사용자 경험 위험

| 위험 | 가능성 | 영향 | 대응 방안 |
|------|--------|------|----------|
| 변환 품질 불만 | 중간 | 높음 | 품질 프리셋 제공, VMAF 검증 옵션 |
| 메타데이터 손실 | 낮음 | 높음 | 3단계 메타데이터 복원, 검증 로직 |
| 저장 공간 부족 | 중간 | 중간 | 사전 공간 확인, 점진적 처리 |
| 권한 문제 | 중간 | 중간 | 명확한 권한 안내, 자동 권한 요청 |

### 7.3 대응 전략

**품질 보장 전략**:
1. 기본 설정으로 VMAF 93+ 보장
2. 변환 후 자동 검증
3. 검증 실패 시 소프트웨어 인코딩으로 폴백

**데이터 안전 전략**:
1. 원본 파일 즉시 삭제하지 않음 (processed 폴더로 이동)
2. 메타데이터 복원 후 검증
3. 사용자 확인 후 원본 정리 옵션

---

## 8. 성공 지표

### 8.1 기능적 지표

| 지표 | 목표 |
|------|------|
| 변환 성공률 | 99%+ |
| 메타데이터 보존율 | 100% |
| 평균 압축률 | 50%+ |
| VMAF 점수 | 93+ |

### 8.2 성능 지표

| 지표 | 목표 |
|------|------|
| 4K 30분 영상 변환 시간 (HW) | 5분 이내 |
| 1080p 10분 영상 변환 시간 (HW) | 30초 이내 |
| 메모리 사용량 | 1GB 이하 |
| CPU 사용률 (HW 모드) | 30% 이하 |

### 8.3 사용자 경험 지표

| 지표 | 목표 |
|------|------|
| 초기 설정 시간 | 5분 이내 |
| 일일 자동 실행 신뢰성 | 99.9%+ |
| 에러 복구 성공률 | 95%+ |

---

## 9. 참고 문서

- [01-system-architecture.ko.md](architecture/01-system-architecture.ko.md) - 시스템 아키텍처
- [02-sequence-diagrams.ko.md](architecture/02-sequence-diagrams.ko.md) - 시퀀스 다이어그램
- [03-data-flow-and-states.ko.md](architecture/03-data-flow-and-states.ko.md) - 데이터 흐름
- [04-processing-procedures.ko.md](architecture/04-processing-procedures.ko.md) - 처리 절차
- [01-codec-comparison.ko.md](reference/01-codec-comparison.ko.md) - 코덱 비교
- [02-ffmpeg-hevc-encoding.ko.md](reference/02-ffmpeg-hevc-encoding.ko.md) - FFmpeg 가이드
- [03-videotoolbox-hardware-acceleration.ko.md](reference/03-videotoolbox-hardware-acceleration.ko.md) - 하드웨어 가속
- [04-macos-photos-access.ko.md](reference/04-macos-photos-access.ko.md) - Photos 접근
- [05-macos-automation-methods.ko.md](reference/05-macos-automation-methods.ko.md) - 자동화 방법

---

## 10. 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2025-12-21 | - | 최초 작성 |

---

*이 문서는 프로젝트 진행에 따라 업데이트됩니다.*
