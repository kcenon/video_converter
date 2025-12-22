# H.264→H.265 자동 변환 시스템 아키텍처 개요

## 시스템 목표

macOS Photos에 저장된 H.264 동영상을 H.265(HEVC)로 자동 변환하여:

1. **저장 공간 절약**: 50% 이상 파일 크기 감소
2. **화질 유지**: 시각적 무손실 변환
3. **메타데이터 보존**: GPS, 날짜, 앨범 정보 유지
4. **완전 자동화**: 사용자 개입 최소화

## 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                    macOS Photos Library                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │
│  │ H.264 Videos  │  │   Metadata    │  │    Albums     │        │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘        │
└──────────┼──────────────────┼──────────────────┼────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Video Extractor                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  osxphotos / PhotoKit                                     │  │
│  │  - H.264 비디오 감지                                       │  │
│  │  - 원본 파일 내보내기                                       │  │
│  │  - 메타데이터 추출                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Video Converter Engine                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FFmpeg + VideoToolbox                                    │  │
│  │  - hevc_videotoolbox (하드웨어 가속)                       │  │
│  │  - CRF/Quality 설정                                       │  │
│  │  - 메타데이터 매핑                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Post-Processing                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ExifTool / Metadata Restoration                          │  │
│  │  - GPS 정보 복원                                           │  │
│  │  - 생성 날짜 복원                                           │  │
│  │  - 파일 타임스탬프 동기화                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Output Management                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  H.265 Videos   │  │   Backup Dir    │  │   Logs/Reports  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 핵심 컴포넌트

### 1. Video Extractor (비디오 추출기)

**역할**: Photos 라이브러리에서 변환 대상 비디오 식별 및 추출

**기술 스택**:
- **osxphotos** (권장): Python 기반, CLI 및 API 제공
- **PhotoKit**: Swift 네이티브, 앱 개발 시

**주요 기능**:
```python
# osxphotos 예시
import osxphotos

def get_h264_videos(photosdb):
    """H.264 코덱 비디오만 필터링"""
    videos = []
    for photo in photosdb.photos():
        if photo.ismovie and photo.path:
            # 코덱 확인 로직
            if is_h264(photo.path):
                videos.append(photo)
    return videos
```

### 2. Codec Detector (코덱 감지기)

**역할**: 비디오의 현재 코덱 확인

**구현**:
```bash
#!/bin/bash
# FFprobe로 코덱 확인
get_video_codec() {
    ffprobe -v error \
        -select_streams v:0 \
        -show_entries stream=codec_name \
        -of default=noprint_wrappers=1:nokey=1 \
        "$1"
}

# 사용 예
codec=$(get_video_codec "video.mp4")
if [ "$codec" = "h264" ]; then
    echo "변환 대상"
fi
```

### 3. Video Converter Engine (변환 엔진)

**역할**: H.264 → H.265 변환 수행

**두 가지 모드**:

| 모드 | 인코더 | 속도 | 품질 | 권장 상황 |
|------|--------|------|------|-----------|
| 빠른 모드 | hevc_videotoolbox | 매우 빠름 | 양호 | 대량 변환 |
| 고품질 모드 | libx265 | 느림 | 최고 | 중요 영상 |

**핵심 설정**:
```bash
# 빠른 모드 (하드웨어)
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 45 \
  -tag:v hvc1 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4

# 고품질 모드 (소프트웨어)
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 20 \
  -preset slow \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### 4. Metadata Manager (메타데이터 관리자)

**역할**: GPS, 날짜 등 메타데이터 보존

**처리 흐름**:
```
원본 비디오 → 메타데이터 추출 → 변환 → 메타데이터 복원 → 타임스탬프 동기화
```

**구현**:
```bash
# 메타데이터 복원
restore_metadata() {
    original="$1"
    converted="$2"

    # FFmpeg 메타데이터 (기본)
    # -map_metadata 0 옵션으로 처리

    # ExifTool로 추가 메타데이터 복원
    exiftool -tagsFromFile "$original" \
        -all:all \
        -overwrite_original \
        "$converted"

    # 파일 타임스탬프 동기화
    touch -r "$original" "$converted"
}
```

### 5. Automation Controller (자동화 컨트롤러)

**역할**: 전체 변환 프로세스 자동화

**구현 옵션**:

| 방법 | 트리거 | 권장 시나리오 |
|------|--------|---------------|
| launchd + WatchPaths | 폴더 변경 감지 | 실시간 처리 |
| launchd + StartCalendarInterval | 일정 시간 | 배치 처리 |
| Folder Actions | 파일 추가 | 간단한 자동화 |

## 디렉토리 구조

```
~/Videos/VideoConverter/
├── input/              # 변환 대기 비디오
├── output/             # 변환 완료 비디오
├── processed/          # 처리된 원본 백업
├── failed/             # 실패한 변환
├── logs/               # 변환 로그
│   ├── conversion.log
│   └── errors.log
└── config/             # 설정 파일
    └── settings.json
```

## 설정 파일 구조

```json
{
  "version": "0.1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "preset": "slow",
    "crf": 22
  },
  "paths": {
    "input": "~/Videos/VideoConverter/input",
    "output": "~/Videos/VideoConverter/output",
    "processed": "~/Videos/VideoConverter/processed",
    "failed": "~/Videos/VideoConverter/failed"
  },
  "automation": {
    "method": "launchd",
    "schedule": "daily",
    "time": "03:00"
  },
  "photos": {
    "autoExport": true,
    "skipEdited": true,
    "downloadFromICloud": true
  },
  "notification": {
    "enabled": true,
    "onComplete": true,
    "onError": true
  }
}
```

## 워크플로우

### 전체 처리 흐름

```
1. 트리거 발생
   ├─ 수동 실행
   ├─ 일정 시간 도달
   └─ 폴더 변경 감지

2. Photos 라이브러리 스캔
   ├─ 모든 비디오 목록 조회
   ├─ H.264 코덱 필터링
   └─ 이미 변환된 항목 제외

3. 비디오 내보내기
   ├─ 원본 파일 복사
   ├─ 메타데이터 추출
   └─ iCloud에서 다운로드 (필요시)

4. 변환 실행
   ├─ FFmpeg 실행
   ├─ 진행 상황 모니터링
   └─ 에러 처리

5. 후처리
   ├─ 메타데이터 복원
   ├─ 타임스탬프 동기화
   └─ 품질 검증 (선택)

6. 정리
   ├─ 원본 백업/삭제
   ├─ 로그 기록
   └─ 알림 발송
```

### 에러 처리 전략

```python
class ConversionError(Exception):
    pass

def convert_with_retry(input_path, output_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = run_ffmpeg(input_path, output_path)
            if validate_output(output_path):
                return True
        except Exception as e:
            log_error(f"Attempt {attempt + 1} failed: {e}")

            if attempt == max_retries - 1:
                move_to_failed(input_path)
                raise ConversionError(f"Failed after {max_retries} attempts")

            time.sleep(5 * (attempt + 1))  # 지수 백오프

    return False
```

## 성능 최적화

### 병렬 처리

```bash
# GNU Parallel 사용
find "$INPUT_DIR" -name "*.mp4" | \
    parallel -j 2 ~/Scripts/convert_single.sh {}
```

### 리소스 관리

```python
import os
import multiprocessing

def get_optimal_workers():
    """시스템 리소스에 따른 최적 워커 수"""
    cpu_count = multiprocessing.cpu_count()

    # 하드웨어 인코딩: CPU 영향 적음
    if use_hardware_encoding:
        return min(3, cpu_count)

    # 소프트웨어 인코딩: CPU 집약적
    return max(1, cpu_count // 4)
```

## 모니터링 및 로깅

### 로그 형식

```
[2024-12-21 03:00:00] INFO  Starting batch conversion
[2024-12-21 03:00:01] INFO  Found 15 videos to convert
[2024-12-21 03:00:05] INFO  Converting: vacation_2024.mov (1/15)
[2024-12-21 03:02:30] INFO  Completed: vacation_2024.mov (2.5 GB → 1.1 GB)
[2024-12-21 03:02:31] ERROR Failed: corrupted_video.mp4 - Invalid data found
[2024-12-21 03:45:00] INFO  Batch completed: 14 success, 1 failed
```

### 통계 보고서

```json
{
  "date": "2024-12-21",
  "totalVideos": 15,
  "successful": 14,
  "failed": 1,
  "originalSize": "35.2 GB",
  "convertedSize": "15.8 GB",
  "savedSpace": "19.4 GB (55%)",
  "totalDuration": "45m 32s",
  "averageSpeed": "3.2x realtime"
}
```

## 기술 요구 사항

### 필수 소프트웨어

| 소프트웨어 | 버전 | 용도 |
|------------|------|------|
| macOS | 10.15+ | 운영 체제 |
| Python | 3.10+ | osxphotos 실행 |
| FFmpeg | 5.0+ | 비디오 변환 |
| ExifTool | 12.0+ | 메타데이터 처리 |
| osxphotos | 0.70+ | Photos 접근 |

### 설치 명령어

```bash
# Homebrew 패키지
brew install ffmpeg exiftool python@3.12

# Python 패키지
pip install osxphotos
```

### 하드웨어 권장 사양

| 항목 | 최소 | 권장 |
|------|------|------|
| CPU | M1 | M2 Pro / M3 |
| RAM | 8GB | 16GB+ |
| 저장 공간 | 변환 대상의 2배 | 변환 대상의 3배 |

## 다음 단계

이 아키텍처를 기반으로 구현 시 다음 순서를 권장합니다:

1. **환경 설정**: 필수 소프트웨어 설치 및 권한 설정
2. **코어 스크립트 개발**: 변환 엔진 및 메타데이터 처리
3. **자동화 설정**: launchd 또는 선호하는 방법 구성
4. **테스트**: 소규모 비디오로 검증
5. **모니터링 추가**: 로깅 및 알림 시스템
6. **점진적 배포**: 전체 라이브러리로 확대

## 참고 자료

- [01-codec-comparison.ko.md](01-codec-comparison.ko.md) - 코덱 비교
- [02-ffmpeg-hevc-encoding.ko.md](02-ffmpeg-hevc-encoding.ko.md) - FFmpeg 인코딩 가이드
- [03-videotoolbox-hardware-acceleration.ko.md](03-videotoolbox-hardware-acceleration.ko.md) - 하드웨어 가속
- [04-macos-photos-access.ko.md](04-macos-photos-access.ko.md) - Photos 접근 방법
- [05-macos-automation-methods.ko.md](05-macos-automation-methods.ko.md) - 자동화 방법
