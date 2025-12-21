# FFmpeg H.265/HEVC 인코딩 가이드

## 개요

FFmpeg을 사용한 H.264에서 H.265(HEVC)로의 비디오 변환 방법과 최적 설정을 정리합니다.

## 기본 명령어

### 가장 간단한 변환

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -c:a copy output.mp4
```

### 권장 변환 (화질 우선)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -preset slow \
  -profile:v main \
  -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -map_metadata 0 \
  -movflags use_metadata_tags \
  output.mp4
```

## CRF (Constant Rate Factor) 설정

### CRF 범위

| CRF 값 | 품질 | 용도 |
|--------|------|------|
| 0 | 무손실 | 아카이빙 (파일 크기 매우 큼) |
| 18-20 | 시각적 무손실 | 고품질 보관 |
| 23 | 기본값 | 일반적인 사용 |
| 28 | 양호 | 파일 크기 절약 |
| 35+ | 저품질 | 권장하지 않음 |

### H.264 ↔ H.265 CRF 변환 공식

> H.265 CRF ≈ H.264 CRF + 4~6
>
> 예: H.264 CRF 23 ≈ H.265 CRF 27-29

```bash
# H.264 품질 유지하려면 H.265에서 CRF를 4-6 낮춤
# 예: H.264 CRF 23과 동등한 H.265 품질
ffmpeg -i input_h264.mp4 -c:v libx265 -crf 19 output.mp4
```

## 프리셋 (Preset) 옵션

### 속도 vs 품질 트레이드오프

| 프리셋 | 속도 | 파일 크기 | 권장 용도 |
|--------|------|-----------|-----------|
| ultrafast | 가장 빠름 | 가장 큼 | 테스트용 |
| superfast | 매우 빠름 | 매우 큼 | 빠른 변환 필요시 |
| veryfast | 빠름 | 큼 | 실시간 인코딩 |
| faster | 빠름 | 큼 | 빠른 배치 작업 |
| fast | 보통 | 보통 | 일반 사용 |
| medium | 보통 | 보통 | 기본값 |
| slow | 느림 | 작음 | **권장** |
| slower | 매우 느림 | 매우 작음 | 최종 출력 |
| veryslow | 가장 느림 | 가장 작음 | 최대 압축 필요시 |

```bash
# 권장: slow 프리셋으로 좋은 품질/크기 비율 달성
ffmpeg -i input.mp4 -c:v libx265 -crf 23 -preset slow output.mp4
```

## 메타데이터 보존

### 기본 메타데이터 복사

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### 전체 메타데이터 보존 (GPS 포함)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a copy \
  -map 0 \
  -map_metadata 0 \
  -movflags use_metadata_tags \
  output.mp4
```

### ExifTool을 사용한 완전한 메타데이터 복원

```bash
# 1. 먼저 FFmpeg으로 변환
ffmpeg -i original.mp4 -c:v libx265 -crf 23 converted.mp4

# 2. ExifTool로 메타데이터 복사
exiftool -tagsFromFile original.mp4 converted.mp4

# 3. 파일 타임스탬프 복원
touch -r original.mp4 converted.mp4
```

## 오디오 처리

### 오디오 스트림 복사 (권장)

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 23 -c:a copy output.mp4
```

### 오디오 재인코딩 (필요시)

```bash
# AAC 인코딩
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4

# 원본 오디오 품질 유지 (libfdk_aac 필요)
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a libfdk_aac -vbr 5 \
  output.mp4
```

## 고급 설정

### VMAF 95 달성 설정 (2025 벤치마크 기준)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -preset slow \
  -crf 20.6 \
  -g 600 \
  -keyint_min 600 \
  -tune fastdecode \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### 10비트 인코딩 (HDR 호환)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 22 \
  -preset slow \
  -profile:v main10 \
  -pix_fmt yuv420p10le \
  output.mp4
```

### 2-Pass 인코딩 (고정 비트레이트)

```bash
# Pass 1
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -b:v 5M \
  -preset slow \
  -pass 1 \
  -an \
  -f null /dev/null

# Pass 2
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -b:v 5M \
  -preset slow \
  -pass 2 \
  -c:a copy \
  output.mp4
```

## 배치 변환 스크립트

### 단일 폴더 내 모든 MP4 변환

```bash
#!/bin/bash
INPUT_DIR="./input"
OUTPUT_DIR="./output"
CRF=23

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.mp4; do
    filename=$(basename "$file" .mp4)
    echo "Converting: $file"

    ffmpeg -i "$file" \
        -c:v libx265 \
        -crf $CRF \
        -preset slow \
        -c:a copy \
        -map_metadata 0 \
        -movflags use_metadata_tags \
        "$OUTPUT_DIR/${filename}_hevc.mp4"

    # 메타데이터 복원
    exiftool -tagsFromFile "$file" "$OUTPUT_DIR/${filename}_hevc.mp4" 2>/dev/null
    touch -r "$file" "$OUTPUT_DIR/${filename}_hevc.mp4"
done
```

### 진행 상황 표시 포함

```bash
#!/bin/bash
# 진행률 표시를 위해 pv 또는 ffmpeg의 -progress 옵션 사용

ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 -preset slow \
  -c:a copy \
  -progress pipe:1 \
  output.mp4 2>&1 | \
  while read line; do
    if [[ "$line" == *"out_time="* ]]; then
      echo "Progress: ${line#*=}"
    fi
  done
```

## 인코딩 품질 검증

### VMAF 점수 계산

```bash
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi libvmaf="model=version=vmaf_v0.6.1" \
  -f null -
```

### PSNR/SSIM 계산

```bash
# PSNR
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi psnr="stats_file=psnr.log" \
  -f null -

# SSIM
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi ssim="stats_file=ssim.log" \
  -f null -
```

## 문제 해결

### QuickTime 호환성 문제

```bash
# QuickTime 호환 설정 추가
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -tag:v hvc1 \
  -c:a aac \
  output.mp4
```

### 색상 공간 유지

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -color_primaries bt709 \
  -color_trc bt709 \
  -colorspace bt709 \
  output.mp4
```

## macOS에서 FFmpeg 설치

```bash
# Homebrew 사용
brew install ffmpeg

# 모든 코덱 포함 설치
brew install ffmpeg --with-libvpx --with-libvorbis
```

## 참고 자료

- [OTTVerse - HEVC Encoding Guide](https://ottverse.com/hevc-encoding-using-ffmpeg-crf-cbr-2-pass-lossless/)
- [scottstuff.net - 2025 H.265 Benchmarks](https://scottstuff.net/posts/2025/03/17/benchmarking-ffmpeg-h265/)
- [slhck.info - CRF Guide](https://slhck.info/video/2017/02/24/crf-guide.html)
- [Mux - Video Compression Guide](https://www.mux.com/articles/how-to-compress-video-files-while-maintaining-quality-with-ffmpeg)
- [FFmpeg Documentation](https://www.ffmpeg.org/ffmpeg.html)
