# H.264 vs H.265 (HEVC) 코덱 비교

## 개요

이 문서는 H.264(AVC)와 H.265(HEVC) 비디오 코덱의 기술적 차이점과 변환 시 고려사항을 정리합니다.

## 기술 사양 비교

| 특성 | H.264 (AVC) | H.265 (HEVC) |
|------|-------------|--------------|
| 출시 연도 | 2003 | 2013 |
| 블록 크기 | 4×4, 8×8, 16×16 | 최대 64×64 (CTU) |
| 압축 효율 | 기준 | ~50% 향상 |
| 인코딩 복잡도 | 낮음 | 높음 (2-10배) |
| 하드웨어 지원 | 거의 모든 장치 | 최신 장치 위주 |
| 라이선스 | 명확한 특허 풀 | 복잡한 특허 상황 |

## 압축 효율성

### 동일 비트레이트에서의 품질 비교

H.265는 H.264 대비 동일한 비트레이트에서 더 높은 화질을 제공합니다:

- **PSNR 기준**: H.265가 평균 2-3dB 향상
- **SSIM 기준**: H.265가 약 0.01-0.02 향상
- **VMAF 기준**: H.265가 5-10점 향상

### 동일 품질에서의 파일 크기

> "1GB H.264 비디오는 화질 손실 없이 H.265로 변환 시 약 500MB로 줄어들 수 있습니다."
> — [codestudy.net](https://www.codestudy.net/blog/convert-videos-from-264-to-265-hevc-with-ffmpeg/)

## 화질 측정 지표

### VMAF (Video Multimethod Assessment Fusion)

- Netflix가 개발한 기계 학습 기반 품질 지표
- 인간의 시각적 인식과 가장 유사한 결과
- 점수 범위: 0-100 (95+ 권장)

### PSNR (Peak Signal-to-Noise Ratio)

- 전통적인 객관적 품질 지표
- 일반적으로 40dB 이상이면 우수한 품질
- 세부 디테일 손실 측정에 유용

### SSIM (Structural Similarity Index)

- 구조적 유사성 측정
- 범위: 0-1 (0.99+ 권장)
- 주관적 화질 손실 측정에 효과적

## H.264가 H.265보다 나은 경우

연구 결과에 따르면 다음 상황에서 H.264가 더 나은 결과를 보일 수 있습니다:

1. **노이즈가 많은 소스**: H.265의 큰 블록 크기가 노이즈 디테일을 잃을 수 있음
2. **매우 높은 비트레이트**: 충분한 비트레이트에서는 차이가 미미함
3. **빠른 움직임 콘텐츠**: H.264의 작은 블록이 미세한 움직임 보존에 유리
4. **이미 압축된 콘텐츠**: 재압축 시 추가 손실 발생

> "QP=27에서 H.265와 H.264의 비트레이트는 유사(9.66Mbps vs 9.96Mbps)하지만, H.265의 PSNR이 더 낮을 수 있습니다(40.19 vs 41.8)."
> — [NETINT Technologies](https://www.netint.cn/case-study/is-h-264-avc-better-than-h265-hevc-under-what-conditions-can-h-264-outperform-h-265/)

## 변환 시 화질 유지 전략

### 권장 CRF 값

| 사용 목적 | H.264 CRF | H.265 CRF | 설명 |
|-----------|-----------|-----------|------|
| 시각적 무손실 | 17-18 | 20-22 | 원본과 구분 불가 |
| 고품질 보관 | 20-21 | 23-25 | 권장 설정 |
| 일반 시청 | 23 | 26-28 | 기본값 |
| 저용량 우선 | 26-28 | 30-32 | 눈에 띄는 열화 가능 |

### VMAF 95 달성을 위한 권장 설정 (2025 벤치마크)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -preset slow \
  -crf 20.6 \
  -g 600 \
  -keyint_min 600 \
  -tune fastdecode \
  output.mp4
```

> 2025년 3월 벤치마크에서 VMAF 95를 달성하는 최적 설정
> — [scottstuff.net](https://scottstuff.net/posts/2025/03/17/benchmarking-ffmpeg-h265/)

## 무손실 변환의 한계

**중요**: H.264에서 H.265로의 "무손실" 변환은 기술적으로 불가능합니다.

- 두 코덱 모두 손실 압축 알고리즘 사용
- 재인코딩은 필연적으로 추가 품질 손실 발생
- "시각적 무손실(visually lossless)"이 현실적인 목표

### 세대 손실 최소화 방법

1. **높은 품질 설정 사용**: CRF 20-22 권장
2. **slow/slower 프리셋 사용**: 더 나은 압축 효율
3. **원본 해상도 유지**: 업스케일링/다운스케일링 금지
4. **원본 프레임레이트 유지**: 프레임 보간 금지

## 호환성 고려사항

### macOS/iOS 지원

| 기능 | H.264 | H.265 |
|------|-------|-------|
| macOS 재생 | 모든 버전 | High Sierra+ |
| iOS 재생 | 모든 버전 | iOS 11+ |
| Photos 앱 | 완전 지원 | 완전 지원 |
| iCloud 동기화 | 완전 지원 | 완전 지원 |

### 하드웨어 디코딩

- **Intel Mac**: 6세대 이후 (Skylake)
- **Apple Silicon**: 모든 M 시리즈 (M1, M2, M3, M4)

## 참고 자료

- [TekMedia - H.264/H.265 Video Quality Matrix](https://tekmediasoft.com/h-264-and-h-265-video-analyzer/)
- [Visionular - Making Sense of PSNR, SSIM, VMAF](https://visionular.ai/vmaf-ssim-psnr-quality-metrics/)
- [Bitmovin - HEVC vs VP9 Comparison](https://bitmovin.com/blog/vp9-vs-hevc-h265/)
- [OTTVerse - HEVC Encoding Guide](https://ottverse.com/hevc-encoding-using-ffmpeg-crf-cbr-2-pass-lossless/)
