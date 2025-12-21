# H.264 vs H.265 (HEVC) Codec Comparison

## Overview

This document summarizes the technical differences between H.264 (AVC) and H.265 (HEVC) video codecs and considerations for conversion.

## Technical Specifications Comparison

| Characteristic | H.264 (AVC) | H.265 (HEVC) |
|---------------|-------------|--------------|
| Release Year | 2003 | 2013 |
| Block Size | 4×4, 8×8, 16×16 | Up to 64×64 (CTU) |
| Compression Efficiency | Baseline | ~50% improvement |
| Encoding Complexity | Low | High (2-10x) |
| Hardware Support | Almost all devices | Primarily newer devices |
| Licensing | Clear patent pool | Complex patent situation |

## Compression Efficiency

### Quality Comparison at Same Bitrate

H.265 provides higher quality at the same bitrate compared to H.264:

- **PSNR Basis**: H.265 averages 2-3dB improvement
- **SSIM Basis**: H.265 approximately 0.01-0.02 improvement
- **VMAF Basis**: H.265 5-10 points improvement

### File Size at Same Quality

> "A 1GB H.264 video can be reduced to about 500MB when converted to H.265 without visible quality loss."
> — [codestudy.net](https://www.codestudy.net/blog/convert-videos-from-264-to-265-hevc-with-ffmpeg/)

## Quality Measurement Metrics

### VMAF (Video Multimethod Assessment Fusion)

- Machine learning-based quality metric developed by Netflix
- Results most similar to human visual perception
- Score range: 0-100 (95+ recommended)

### PSNR (Peak Signal-to-Noise Ratio)

- Traditional objective quality metric
- Generally 40dB or higher indicates excellent quality
- Useful for measuring fine detail loss

### SSIM (Structural Similarity Index)

- Measures structural similarity
- Range: 0-1 (0.99+ recommended)
- Effective for measuring subjective quality loss

## When H.264 is Better Than H.265

According to research, H.264 can produce better results in the following situations:

1. **Noisy Sources**: H.265's larger block size can lose noise detail
2. **Very High Bitrate**: Differences are minimal with sufficient bitrate
3. **Fast Motion Content**: H.264's smaller blocks are better at preserving fine motion
4. **Already Compressed Content**: Re-compression causes additional loss

> "At QP=27, H.265 and H.264 have similar bitrates (9.66Mbps vs 9.96Mbps), but H.265's PSNR may be lower (40.19 vs 41.8)."
> — [NETINT Technologies](https://www.netint.cn/case-study/is-h-264-avc-better-than-h265-hevc-under-what-conditions-can-h-264-outperform-h-265/)

## Quality Preservation Strategies During Conversion

### Recommended CRF Values

| Use Case | H.264 CRF | H.265 CRF | Description |
|----------|-----------|-----------|-------------|
| Visually Lossless | 17-18 | 20-22 | Indistinguishable from original |
| High Quality Archive | 20-21 | 23-25 | Recommended setting |
| General Viewing | 23 | 26-28 | Default value |
| Size Priority | 26-28 | 30-32 | Visible degradation possible |

### Recommended Settings to Achieve VMAF 95 (2025 Benchmark)

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

> Optimal settings achieving VMAF 95 in March 2025 benchmark
> — [scottstuff.net](https://scottstuff.net/posts/2025/03/17/benchmarking-ffmpeg-h265/)

## Limitations of Lossless Conversion

**Important**: "Lossless" conversion from H.264 to H.265 is technically impossible.

- Both codecs use lossy compression algorithms
- Re-encoding inevitably causes additional quality loss
- "Visually lossless" is the realistic goal

### Methods to Minimize Generation Loss

1. **Use High Quality Settings**: CRF 20-22 recommended
2. **Use slow/slower Preset**: Better compression efficiency
3. **Maintain Original Resolution**: No upscaling/downscaling
4. **Maintain Original Framerate**: No frame interpolation

## Compatibility Considerations

### macOS/iOS Support

| Feature | H.264 | H.265 |
|---------|-------|-------|
| macOS Playback | All versions | High Sierra+ |
| iOS Playback | All versions | iOS 11+ |
| Photos App | Full support | Full support |
| iCloud Sync | Full support | Full support |

### Hardware Decoding

- **Intel Mac**: 6th generation and later (Skylake)
- **Apple Silicon**: All M-series (M1, M2, M3, M4)

## References

- [TekMedia - H.264/H.265 Video Quality Matrix](https://tekmediasoft.com/h-264-and-h-265-video-analyzer/)
- [Visionular - Making Sense of PSNR, SSIM, VMAF](https://visionular.ai/vmaf-ssim-psnr-quality-metrics/)
- [Bitmovin - HEVC vs VP9 Comparison](https://bitmovin.com/blog/vp9-vs-hevc-h265/)
- [OTTVerse - HEVC Encoding Guide](https://ottverse.com/hevc-encoding-using-ffmpeg-crf-cbr-2-pass-lossless/)
