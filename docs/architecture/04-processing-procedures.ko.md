# 처리 절차 정의서

## 1. 전체 처리 절차 개요

### 1.1 메인 워크플로우

```mermaid
flowchart TB
    START([시작]) --> INIT[시스템 초기화]
    INIT --> LOAD_CONFIG[설정 로드]
    LOAD_CONFIG --> CHECK_DEPS{의존성 확인}

    CHECK_DEPS -->|실패| ERROR_DEPS[의존성 오류 보고]
    ERROR_DEPS --> END_FAIL([종료 - 실패])

    CHECK_DEPS -->|성공| SCAN[Photos 라이브러리 스캔]

    SCAN --> FILTER[H.264 비디오 필터링]
    FILTER --> EXCLUDE[이미 변환된 항목 제외]

    EXCLUDE --> CHECK_QUEUE{처리 대상 있음?}
    CHECK_QUEUE -->|없음| LOG_EMPTY[변환 대상 없음 로깅]
    LOG_EMPTY --> END_SUCCESS([종료 - 성공])

    CHECK_QUEUE -->|있음| ESTIMATE[예상 소요 시간 계산]
    ESTIMATE --> PROCESS_LOOP[배치 처리 시작]

    subgraph "배치 처리 루프"
        PROCESS_LOOP --> NEXT_VIDEO{다음 비디오?}
        NEXT_VIDEO -->|있음| EXPORT[비디오 내보내기]
        EXPORT --> CONVERT[H.265 변환]
        CONVERT --> VALIDATE[품질 검증]
        VALIDATE --> RESTORE_META[메타데이터 복원]
        RESTORE_META --> MOVE_ORIG[원본 처리]
        MOVE_ORIG --> UPDATE_STATS[통계 업데이트]
        UPDATE_STATS --> NEXT_VIDEO
    end

    NEXT_VIDEO -->|없음| GENERATE_REPORT[보고서 생성]
    GENERATE_REPORT --> NOTIFY[알림 발송]
    NOTIFY --> CLEANUP[임시 파일 정리]
    CLEANUP --> END_SUCCESS
```

### 1.2 처리 단계별 상세

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        처리 절차 요약                                      │
├─────────┬───────────────────────────────────────────────────────────────┤
│ 단계    │ 설명                                                           │
├─────────┼───────────────────────────────────────────────────────────────┤
│ 1. 초기화 │ 설정 로드, 의존성 확인, 디렉토리 생성                            │
│ 2. 스캔   │ Photos 라이브러리에서 비디오 목록 수집                           │
│ 3. 필터링 │ H.264 코덱만 선택, 이미 변환된 항목 제외                         │
│ 4. 추출   │ Photos에서 임시 디렉토리로 원본 내보내기                         │
│ 5. 변환   │ FFmpeg으로 H.265 인코딩 실행                                   │
│ 6. 검증   │ 출력 파일 무결성 및 품질 확인                                   │
│ 7. 메타데이터│ GPS, 날짜 등 메타데이터 복원                                  │
│ 8. 정리   │ 원본 이동/삭제, 통계 기록, 알림                                │
└─────────┴───────────────────────────────────────────────────────────────┘
```

## 2. 단계별 상세 절차

### 2.1 시스템 초기화 절차

```mermaid
flowchart TB
    subgraph "1. 설정 로드"
        A1[기본 설정 로드] --> A2[사용자 설정 병합]
        A2 --> A3[환경 변수 오버라이드]
        A3 --> A4[CLI 인자 오버라이드]
        A4 --> A5[설정 유효성 검증]
    end

    subgraph "2. 의존성 확인"
        B1[FFmpeg 설치 확인] --> B2[버전 호환성 확인]
        B2 --> B3[VideoToolbox 지원 확인]
        B3 --> B4[ExifTool 설치 확인]
        B4 --> B5[osxphotos 설치 확인]
        B5 --> B6[Python 버전 확인]
    end

    subgraph "3. 디렉토리 준비"
        C1[입력 디렉토리 확인] --> C2[출력 디렉토리 생성]
        C2 --> C3[처리 완료 디렉토리 생성]
        C3 --> C4[실패 디렉토리 생성]
        C4 --> C5[로그 디렉토리 생성]
    end

    subgraph "4. 로깅 초기화"
        D1[로그 파일 설정] --> D2[로그 레벨 설정]
        D2 --> D3[로그 로테이션 설정]
    end

    A5 --> B1
    B6 --> C1
    C5 --> D1
```

#### 의존성 확인 스크립트

```bash
#!/bin/bash
# check_dependencies.sh

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed"
        return 1
    fi
    echo "OK: $1 found at $(which $1)"
    return 0
}

check_ffmpeg_hevc() {
    if ffmpeg -encoders 2>/dev/null | grep -q hevc_videotoolbox; then
        echo "OK: hevc_videotoolbox encoder available"
        return 0
    fi
    echo "ERROR: hevc_videotoolbox not available"
    return 1
}

echo "=== Checking Dependencies ==="

check_command ffmpeg
check_command ffprobe
check_command exiftool
check_command python3

python3 -c "import osxphotos" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "OK: osxphotos module available"
else
    echo "ERROR: osxphotos module not installed"
fi

check_ffmpeg_hevc

echo "=== Dependency Check Complete ==="
```

### 2.2 비디오 스캔 및 필터링 절차

```mermaid
flowchart TB
    subgraph "Photos 라이브러리 스캔"
        S1[PhotosDB 연결] --> S2[전체 미디어 쿼리]
        S2 --> S3[비디오만 필터링]
        S3 --> S4[VideoInfo 객체 생성]
    end

    subgraph "코덱 분석"
        F1[FFprobe로 코덱 확인] --> F2{H.264?}
        F2 -->|Yes| F3[변환 대상 추가]
        F2 -->|No| F4[건너뛰기]
    end

    subgraph "중복 제외"
        E1[변환 기록 로드] --> E2[출력 폴더 스캔]
        E2 --> E3[파일명 매칭]
        E3 --> E4{이미 변환됨?}
        E4 -->|Yes| E5[목록에서 제외]
        E4 -->|No| E6[최종 목록에 추가]
    end

    S4 --> F1
    F3 --> E1
```

#### 코덱 확인 함수

```python
def detect_codec(video_path: Path) -> str:
    """FFprobe를 사용하여 비디오 코덱 감지"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().lower()


def is_h264(video_path: Path) -> bool:
    """H.264 코덱 여부 확인"""
    codec = detect_codec(video_path)
    return codec in ('h264', 'avc', 'avc1')


def is_already_hevc(video_path: Path) -> bool:
    """이미 HEVC 코덱인지 확인"""
    codec = detect_codec(video_path)
    return codec in ('hevc', 'h265', 'hvc1', 'hev1')
```

### 2.3 비디오 변환 절차

```mermaid
flowchart TB
    subgraph "변환 준비"
        P1[입력 파일 검증] --> P2[출력 경로 생성]
        P2 --> P3[임시 파일 경로 설정]
        P3 --> P4[인코딩 옵션 결정]
    end

    subgraph "FFmpeg 실행"
        E1[FFmpeg 명령 구성] --> E2[프로세스 시작]
        E2 --> E3[진행률 모니터링]
        E3 --> E4{완료?}
        E4 -->|진행 중| E3
        E4 -->|완료| E5{성공?}
    end

    subgraph "결과 처리"
        R1[출력 파일 확인] --> R2[임시→최종 이동]
        R2 --> R3[결과 객체 생성]
    end

    subgraph "에러 처리"
        X1[에러 분석] --> X2{재시도?}
        X2 -->|Yes| X3[대기 후 재시도]
        X2 -->|No| X4[실패 처리]
    end

    P4 --> E1
    E5 -->|성공| R1
    E5 -->|실패| X1
    X3 --> E1
```

#### FFmpeg 명령 구성

```python
def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    config: EncodingConfig
) -> List[str]:
    """인코딩 설정에 따른 FFmpeg 명령 구성"""

    cmd = ['ffmpeg', '-y', '-i', str(input_path)]

    if config.mode == 'hardware':
        # VideoToolbox 하드웨어 인코딩
        cmd.extend([
            '-c:v', 'hevc_videotoolbox',
            '-q:v', str(config.quality),  # 1-100
            '-tag:v', 'hvc1',  # QuickTime 호환성
        ])
    else:
        # libx265 소프트웨어 인코딩
        cmd.extend([
            '-c:v', 'libx265',
            '-crf', str(config.crf),  # 0-51
            '-preset', config.preset,
        ])

    # 공통 옵션
    cmd.extend([
        '-c:a', 'copy',           # 오디오 스트림 복사
        '-map_metadata', '0',      # 메타데이터 복사
        '-movflags', 'use_metadata_tags',
        '-progress', 'pipe:1',     # 진행률 출력
        str(output_path)
    ])

    return cmd
```

### 2.4 메타데이터 복원 절차

```mermaid
flowchart TB
    subgraph "메타데이터 추출"
        M1[원본 파일 읽기] --> M2[ExifTool 실행]
        M2 --> M3[JSON 파싱]
        M3 --> M4[메타데이터 객체 생성]
    end

    subgraph "메타데이터 적용"
        A1[ExifTool -tagsFromFile] --> A2[GPS 좌표 확인]
        A2 --> A3[날짜/시간 확인]
        A3 --> A4[카메라 정보 확인]
    end

    subgraph "타임스탬프 동기화"
        T1[원본 타임스탬프 읽기] --> T2[생성일 설정]
        T2 --> T3[수정일 설정]
        T3 --> T4[접근일 설정]
    end

    subgraph "검증"
        V1[변환된 파일 메타데이터 읽기] --> V2{일치?}
        V2 -->|Yes| V3[성공]
        V2 -->|No| V4[경고 로깅]
    end

    M4 --> A1
    A4 --> T1
    T4 --> V1
```

#### 메타데이터 복원 스크립트

```bash
#!/bin/bash
# restore_metadata.sh

ORIGINAL="$1"
CONVERTED="$2"

echo "Restoring metadata from $ORIGINAL to $CONVERTED"

# 1. ExifTool로 모든 태그 복사
exiftool -overwrite_original \
    -tagsFromFile "$ORIGINAL" \
    -all:all \
    "$CONVERTED"

# 2. GPS 정보 명시적 복사 (일부 포맷에서 누락될 수 있음)
exiftool -overwrite_original \
    -tagsFromFile "$ORIGINAL" \
    "-GPS*" \
    "$CONVERTED"

# 3. 파일 타임스탬프 동기화
touch -r "$ORIGINAL" "$CONVERTED"

# 4. 결과 확인
echo "=== Original Metadata ==="
exiftool -CreateDate -GPSLatitude -GPSLongitude "$ORIGINAL"

echo "=== Converted Metadata ==="
exiftool -CreateDate -GPSLatitude -GPSLongitude "$CONVERTED"
```

### 2.5 품질 검증 절차

```mermaid
flowchart TB
    subgraph "기본 검증"
        B1[파일 존재 확인] --> B2[파일 크기 확인]
        B2 --> B3[FFprobe 무결성 검사]
        B3 --> B4{기본 검증 통과?}
    end

    subgraph "속성 비교"
        P1[해상도 비교] --> P2[프레임레이트 비교]
        P2 --> P3[재생 시간 비교]
        P3 --> P4{속성 일치?}
    end

    subgraph "화질 검증 (선택)"
        Q1[VMAF 계산] --> Q2{VMAF >= 93?}
        Q2 -->|Yes| Q3[통과]
        Q2 -->|No| Q4[경고/실패]
    end

    subgraph "압축률 확인"
        C1[원본 크기 / 변환 크기] --> C2{정상 범위?}
        C2 -->|20-80%| C3[정상]
        C2 -->|범위 초과| C4[경고]
    end

    B4 -->|Yes| P1
    B4 -->|No| FAIL[검증 실패]

    P4 -->|Yes| Q1
    P4 -->|No| FAIL

    Q3 --> C1
    Q4 --> C1

    C3 --> SUCCESS[검증 성공]
    C4 --> SUCCESS
```

#### 품질 검증 함수

```python
def validate_conversion(
    original: Path,
    converted: Path,
    config: ValidationConfig
) -> ValidationResult:
    """변환 결과 검증"""

    errors = []
    warnings = []

    # 1. 파일 존재 및 크기 확인
    if not converted.exists():
        return ValidationResult(valid=False, errors=["Output file not found"])

    if converted.stat().st_size == 0:
        return ValidationResult(valid=False, errors=["Output file is empty"])

    # 2. FFprobe 무결성 검사
    probe_result = run_ffprobe(converted)
    if probe_result.get('error'):
        return ValidationResult(valid=False, errors=["File integrity check failed"])

    # 3. 속성 비교
    orig_info = get_video_info(original)
    conv_info = get_video_info(converted)

    if abs(orig_info.duration - conv_info.duration) > 1.0:
        errors.append(f"Duration mismatch: {orig_info.duration} vs {conv_info.duration}")

    if orig_info.resolution != conv_info.resolution:
        errors.append(f"Resolution mismatch: {orig_info.resolution} vs {conv_info.resolution}")

    # 4. 압축률 확인
    compression = converted.stat().st_size / original.stat().st_size
    if compression < 0.2 or compression > 0.8:
        warnings.append(f"Unusual compression ratio: {compression:.2%}")

    # 5. VMAF 계산 (설정된 경우)
    vmaf_score = None
    if config.validate_quality:
        vmaf_score = calculate_vmaf(original, converted)
        if vmaf_score < config.min_vmaf:
            errors.append(f"VMAF score too low: {vmaf_score}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        vmaf_score=vmaf_score,
        compression_ratio=compression
    )
```

## 3. 자동화 절차

### 3.1 launchd 서비스 설정 절차

```mermaid
flowchart TB
    subgraph "설치"
        I1[plist 파일 생성] --> I2[LaunchAgents 디렉토리에 복사]
        I2 --> I3[launchctl load 실행]
        I3 --> I4[서비스 상태 확인]
    end

    subgraph "실행 흐름"
        R1[트리거 발생] --> R2[launchd가 스크립트 실행]
        R2 --> R3[스크립트 완료]
        R3 --> R4[ThrottleInterval 대기]
        R4 --> R1
    end

    subgraph "모니터링"
        M1[launchctl list로 상태 확인] --> M2[로그 파일 확인]
        M2 --> M3[시스템 로그 확인]
    end

    subgraph "제거"
        U1[launchctl unload] --> U2[plist 파일 삭제]
        U2 --> U3[로그 정리]
    end
```

### 3.2 완전한 설치 스크립트

```bash
#!/bin/bash
# install.sh - Video Converter 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin/video_converter"
CONFIG_DIR="$HOME/.config/video_converter"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.videoconverter.plist"

echo "=== Video Converter 설치 ==="

# 1. 의존성 설치
echo "1. 의존성 설치 중..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew가 필요합니다. 설치해주세요."
    exit 1
fi

brew install ffmpeg exiftool python@3.12

# 2. Python 패키지 설치
echo "2. Python 패키지 설치 중..."
pip3 install osxphotos

# 3. 애플리케이션 설치
echo "3. 애플리케이션 설치 중..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/src/"* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/"*.sh

# 4. 설정 파일 생성
echo "4. 설정 파일 생성 중..."
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "version": "1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "schedule": "daily",
    "time": "03:00"
  }
}
EOF
fi

# 5. 디렉토리 생성
echo "5. 작업 디렉토리 생성 중..."
mkdir -p ~/Videos/{ToConvert,Converted,Processed,Failed}
mkdir -p ~/Library/Logs/video_converter

# 6. launchd 서비스 설치
echo "6. 자동화 서비스 설치 중..."
mkdir -p "$LAUNCH_AGENTS"

cat > "$LAUNCH_AGENTS/$PLIST_NAME" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/video_converter/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/video_converter/stderr.log</string>
</dict>
</plist>
EOF

launchctl load "$LAUNCH_AGENTS/$PLIST_NAME"

echo ""
echo "=== 설치 완료 ==="
echo "- 설치 위치: $INSTALL_DIR"
echo "- 설정 파일: $CONFIG_DIR/config.json"
echo "- 로그 위치: ~/Library/Logs/video_converter/"
echo ""
echo "매일 새벽 3시에 자동 실행됩니다."
echo "수동 실행: python3 $INSTALL_DIR/main.py"
```

## 4. 운영 절차

### 4.1 일일 운영 체크리스트

```
□ 1. 서비스 상태 확인
    $ launchctl list | grep videoconverter

□ 2. 최근 로그 확인
    $ tail -100 ~/Library/Logs/video_converter/stdout.log

□ 3. 에러 로그 확인
    $ cat ~/Library/Logs/video_converter/stderr.log

□ 4. 디스크 공간 확인
    $ df -h ~/Videos

□ 5. 대기 중인 파일 확인
    $ ls ~/Videos/ToConvert/

□ 6. 실패한 파일 확인
    $ ls ~/Videos/Failed/
```

### 4.2 문제 해결 절차

```mermaid
flowchart TB
    PROBLEM[문제 발생] --> CHECK_SERVICE{서비스 실행 중?}

    CHECK_SERVICE -->|No| START_SERVICE[서비스 시작]
    START_SERVICE --> RECHECK{해결됨?}
    RECHECK -->|Yes| DONE[완료]
    RECHECK -->|No| CHECK_LOGS

    CHECK_SERVICE -->|Yes| CHECK_LOGS[로그 확인]

    CHECK_LOGS --> IDENTIFY{에러 유형?}

    IDENTIFY -->|권한 오류| FIX_PERM[권한 설정]
    IDENTIFY -->|디스크 공간| CLEANUP[공간 확보]
    IDENTIFY -->|FFmpeg 오류| CHECK_FFMPEG[FFmpeg 확인]
    IDENTIFY -->|Photos 오류| CHECK_PHOTOS[Photos 접근 확인]

    FIX_PERM --> RETRY[재시도]
    CLEANUP --> RETRY
    CHECK_FFMPEG --> RETRY
    CHECK_PHOTOS --> RETRY

    RETRY --> DONE
```

## 5. 요약 다이어그램

### 5.1 전체 시스템 흐름 요약

```mermaid
graph LR
    subgraph "입력"
        A[Photos Library]
        B[Watch Folder]
    end

    subgraph "처리"
        C[Extractor]
        D[Detector]
        E[Converter]
        F[Validator]
        G[Metadata]
    end

    subgraph "출력"
        H[Converted Videos]
        I[Reports]
        J[Notifications]
    end

    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    G --> J
```

### 5.2 핵심 처리 단계

```
┌──────────────────────────────────────────────────────────────────┐
│                    Video Converter 처리 파이프라인                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐          │
│  │ SCAN    │ → │ FILTER  │ → │ EXPORT  │ → │ CONVERT │          │
│  │ Photos  │   │ H.264   │   │ to Temp │   │ H.265   │          │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘          │
│       ↓                                          ↓                │
│  ┌─────────┐                              ┌─────────┐            │
│  │ REPORT  │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ← │VALIDATE │            │
│  │ & NOTIFY│                              │ Quality │            │
│  └─────────┘                              └─────────┘            │
│       ↓                                          ↓                │
│  ┌─────────┐                              ┌─────────┐            │
│  │ CLEANUP │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ← │METADATA │            │
│  │ Originals│                             │ Restore │            │
│  └─────────┘                              └─────────┘            │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```
