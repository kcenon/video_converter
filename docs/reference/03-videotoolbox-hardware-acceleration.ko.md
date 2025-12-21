# Apple Silicon VideoToolbox 하드웨어 가속 가이드

## 개요

Apple Silicon (M1, M2, M3, M4) Mac에서 VideoToolbox를 활용한 하드웨어 가속 HEVC 인코딩 방법을 정리합니다.

## VideoToolbox란?

VideoToolbox는 Apple의 저수준 비디오 인코딩/디코딩 프레임워크입니다:

- macOS 및 iOS에서 하드웨어 가속 비디오 처리 제공
- H.264, H.265/HEVC, ProRes, AV1(M3+) 지원
- FFmpeg에서 `hevc_videotoolbox` 인코더로 접근 가능

## 칩 세대별 지원 기능

| 기능 | M1 | M2 | M3 | M4 |
|------|:--:|:--:|:--:|:--:|
| H.264 인코딩/디코딩 | ✓ | ✓ | ✓ | ✓ |
| HEVC 인코딩/디코딩 | ✓ | ✓ | ✓ | ✓ |
| ProRes 인코딩/디코딩 | ✓ | ✓ | ✓ | ✓ |
| AV1 디코딩 | ✗ | ✗ | ✓ | ✓ |
| ProRes RAW | ✗ | ✓ | ✓ | ✓ |
| 10비트 HEVC | ✓ | ✓ | ✓ | ✓ |

### Pro/Max 칩의 추가 기능

> "Max 칩에는 추가 비디오 인코딩 엔진이 있습니다. VideoToolbox는 단일 트랜스코딩 세션에서도 이 추가 엔진을 활용하여 4K 120fps 트랜스코딩을 지원합니다."
> — [Jellyfin Documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)

## 성능 비교

### 소프트웨어 vs 하드웨어 인코딩

| 인코더 | 30초 4K 영상 처리 시간 | 파일 크기 | 화질 |
|--------|------------------------|-----------|------|
| libx265 (소프트웨어) | 287초 | 기준 | 최고 |
| hevc_videotoolbox | 12초 | +20-30% | 양호 |

> "M2 Pro (10코어 CPU/16코어 GPU)에서 287초 vs 12초로 VideoToolbox가 **24배 빠릅니다**."
> — [b.27p.de](https://b.27p.de/p/00016-ffmpeg-apple-silicon-h265-encoding/)

### 동시 트랜스코딩 능력

> "엔트리급 M1도 세 개의 4K 24fps Dolby Vision HEVC 10비트 트랜스코딩 작업을 동시에 처리할 수 있습니다."
> — [Jellyfin Documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)

## FFmpeg 명령어

### 기본 하드웨어 인코딩

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 50 \
  -c:a copy \
  output.mp4
```

### 권장 설정 (화질 우선)

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 45 \
  -profile:v main \
  -tag:v hvc1 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

## 품질 설정 가이드

### `-q:v` 옵션 (1-100)

| 값 | 품질 | 용도 |
|----|------|------|
| 1-30 | 최고 | 아카이빙, 원본급 |
| 40-55 | **권장** | 일반 사용 |
| 60-75 | 보통 | 스토리지 절약 |
| 80+ | 낮음 | 권장하지 않음 |

> "hevc_videotoolbox의 quality 45-55가 최적의 지점입니다. 기본 품질 설정은 좋지 않습니다."
> — [Hardware Encoding Guide](https://b.27p.de/p/00016-ffmpeg-apple-silicon-h265-encoding/)

### 비트레이트 설정 (대안)

```bash
# 고정 비트레이트 (VBR이 더 권장됨)
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -b:v 10M \
  output.mp4

# 평균 비트레이트
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -b:v 8M \
  -maxrate 12M \
  -bufsize 16M \
  output.mp4
```

## 소프트웨어 vs 하드웨어: 선택 가이드

### 하드웨어 인코딩 (hevc_videotoolbox) 권장 상황

✅ 대량 배치 변환
✅ 빠른 처리가 필요한 경우
✅ 실시간에 가까운 변환 필요
✅ 전력 효율이 중요한 경우 (노트북)

### 소프트웨어 인코딩 (libx265) 권장 상황

✅ 최고 품질 필요 (아카이빙)
✅ 최소 파일 크기 필요
✅ 시간 제약 없음
✅ 고급 인코딩 옵션 필요

## 하이브리드 접근법

### 1단계: 하드웨어로 빠른 변환

```bash
# 먼저 빠르게 하드웨어 인코딩
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 40 \
  -c:a copy \
  quick_output.mp4
```

### 2단계: 중요 파일만 소프트웨어 재인코딩

```bash
# 중요한 파일은 고품질 소프트웨어 인코딩
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 20 \
  -preset slow \
  -c:a copy \
  high_quality_output.mp4
```

## 10비트 HEVC 인코딩

### Apple Silicon의 10비트 지원

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -profile:v main10 \
  -q:v 45 \
  output_10bit.mp4
```

## VideoToolbox 디코딩 활용

### 하드웨어 디코딩 + 소프트웨어 인코딩 조합

```bash
# 디코딩만 하드웨어 가속 (최고 품질 인코딩 유지)
ffmpeg -hwaccel videotoolbox \
  -i input.mp4 \
  -c:v libx265 \
  -crf 22 \
  -preset slow \
  output.mp4
```

## 제한 사항 및 주의 사항

### 지원되지 않는 옵션

하드웨어 인코더는 소프트웨어 인코더의 모든 옵션을 지원하지 않습니다:

❌ `-preset` (slow, medium 등)
❌ `-tune`
❌ `-x265-params`
❌ 일부 고급 GOP 설정

### 파일 크기 트레이드오프

> "대부분의 경우 하드웨어 인코딩은 소프트웨어 라이브러리보다 더 큰 출력 파일을 생성합니다. 그러나 하드웨어 인코딩은 훨씬 빠릅니다."
> — [Martin Riedl](https://www.martin-riedl.de/2020/12/06/using-hardware-acceleration-on-macos-with-ffmpeg/)

### 품질 논란

> "일부 사용자들은 VideoToolbox의 품질이 낮다고 생각합니다 (하지만 엄청나게 빠릅니다)."
> — [MacRumors Forums](https://forums.macrumors.com/threads/apple-silicon-video-converter.2269415/page-3)

## 벤치마크 스크립트

```bash
#!/bin/bash
# 하드웨어 vs 소프트웨어 인코딩 비교

INPUT="test_video.mp4"

echo "=== 소프트웨어 인코딩 (libx265) ==="
time ffmpeg -i "$INPUT" \
  -c:v libx265 -crf 23 -preset medium \
  -c:a copy \
  software_output.mp4 2>/dev/null

echo ""
echo "=== 하드웨어 인코딩 (VideoToolbox) ==="
time ffmpeg -i "$INPUT" \
  -c:v hevc_videotoolbox -q:v 50 \
  -c:a copy \
  hardware_output.mp4 2>/dev/null

echo ""
echo "=== 파일 크기 비교 ==="
ls -lh software_output.mp4 hardware_output.mp4
```

## FFmpeg 설치 확인

```bash
# VideoToolbox 지원 확인
ffmpeg -encoders 2>/dev/null | grep videotoolbox

# 예상 출력:
# V....D hevc_videotoolbox    VideoToolbox H.265 Encoder
# V....D h264_videotoolbox    VideoToolbox H.264 Encoder
```

## 참고 자료

- [CodeTV - Hardware Acceleration on Apple Silicon](https://codetv.dev/blog/hardware-acceleration-ffmpeg-apple-silicon)
- [Jellyfin - Apple Hardware Acceleration](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)
- [Martin Riedl - Hardware Acceleration on macOS](https://www.martin-riedl.de/2020/12/06/using-hardware-acceleration-on-macos-with-ffmpeg/)
- [originell.org - FFmpeg Apple Hardware Acceleration](https://www.originell.org/til/ffmpeg-apple-hardware-accelerated/)
- [Codec Wiki - VideoToolbox](https://wiki.x266.mov/docs/encoders_hw/videotoolbox)
