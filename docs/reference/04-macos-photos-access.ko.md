# macOS Photos 라이브러리 접근 방법

## 개요

macOS Photos 앱에 저장된 동영상에 프로그래밍 방식으로 접근하는 다양한 방법을 정리합니다.

## Photos 라이브러리 구조

### 기본 위치

```
~/Pictures/Photos Library.photoslibrary/
├── database/
│   ├── Photos.sqlite          # 메인 데이터베이스
│   ├── Photos.sqlite-wal
│   └── Photos.sqlite-shm
├── originals/                 # 원본 파일
│   ├── 0/
│   ├── 1/
│   └── ...
├── resources/
│   └── derivatives/           # 편집된 버전
└── private/
```

> "Photos에 가져온 사진과 비디오는 Pictures 폴더의 photo library에 저장됩니다."
> — [Apple Support](https://support.apple.com/guide/photos/photo-library-overview-pht211de786/mac)

### System Photo Library

System Photo Library는 다음 기능과 연동됩니다:

- iCloud Photos
- My Photo Stream
- Shared Albums
- iMovie, Pages, Keynote 등 다른 앱과의 통합

## 접근 방법 1: osxphotos (권장)

### 소개

osxphotos는 Python 기반의 Photos 라이브러리 접근 도구입니다:

> "OSXPhotos는 macOS에서 Apple Photos의 사진 및 관련 메타데이터를 다루는 Python 앱입니다. Photos 라이브러리, 사진, 메타데이터에 프로그래밍 방식으로 접근할 수 있는 패키지도 포함합니다."
> — [GitHub - RhetTbull/osxphotos](https://github.com/RhetTbull/osxphotos)

### 설치

```bash
# uv 사용 (권장)
uv tool install osxphotos

# pip 사용
pip install osxphotos
```

### 시스템 요구 사항

- macOS Sierra (10.12.6) ~ macOS Sequoia (15.7.2)
- Python >= 3.10, <= 3.14
- x86 및 Apple Silicon (M1/M2/M3/M4) 지원

### CLI 사용법

#### 비디오만 내보내기

```bash
# 모든 비디오 내보내기
osxphotos export ~/exported_videos --only-movies

# 특정 앨범의 비디오만
osxphotos export ~/exported_videos --only-movies --album "휴가 2024"

# 특정 기간의 비디오
osxphotos export ~/exported_videos --only-movies \
  --from-date "2024-01-01" \
  --to-date "2024-12-31"
```

#### H.264 코덱 비디오만 필터링

```bash
# 쿼리로 비디오 목록 확인
osxphotos query --only-movies --json | \
  jq '.[] | select(.path | contains(".MOV") or contains(".mp4"))'
```

#### 원본 파일 경로 가져오기

```bash
# 원본 경로 출력
osxphotos query --only-movies --print "{original_filename}: {path}"
```

### Python API 사용법

```python
import osxphotos

# Photos 라이브러리 열기
photosdb = osxphotos.PhotosDB()

# 모든 비디오 가져오기
videos = [p for p in photosdb.photos() if p.ismovie]

for video in videos:
    print(f"이름: {video.original_filename}")
    print(f"경로: {video.path}")
    print(f"생성일: {video.date}")
    print(f"위치: {video.location}")
    print(f"앨범: {video.albums}")
    print(f"코덱: {video.exif_info}")
    print("---")
```

#### 비디오 내보내기 예시

```python
import osxphotos
from pathlib import Path

photosdb = osxphotos.PhotosDB()
export_dir = Path.home() / "exported_videos"
export_dir.mkdir(exist_ok=True)

for video in photosdb.photos():
    if video.ismovie and video.path:
        # 원본 비디오 내보내기
        exported = video.export(str(export_dir))
        print(f"내보냄: {exported}")
```

## 접근 방법 2: PhotoKit Framework (Swift/Objective-C)

### 소개

PhotoKit은 Apple의 공식 프레임워크로 Photos 라이브러리에 접근합니다:

> "PhotoKit을 사용하면 iCloud Photos 및 Live Photos를 포함하여 Photos 앱이 관리하는 이미지 및 비디오 에셋과 작업할 수 있습니다."
> — [Apple Developer Documentation](https://developer.apple.com/documentation/photokit)

### Swift 예시: 비디오 목록 가져오기

```swift
import Photos

func fetchAllVideos() {
    let fetchOptions = PHFetchOptions()
    fetchOptions.sortDescriptors = [
        NSSortDescriptor(key: "creationDate", ascending: false)
    ]

    let videos = PHAsset.fetchAssets(
        with: .video,
        options: fetchOptions
    )

    videos.enumerateObjects { (asset, index, stop) in
        print("비디오: \(asset.localIdentifier)")
        print("생성일: \(asset.creationDate ?? Date())")
        print("길이: \(asset.duration) 초")
        print("---")
    }
}
```

### Swift 예시: 비디오 내보내기

```swift
import Photos
import AVFoundation

func exportVideo(asset: PHAsset, to outputURL: URL) {
    let options = PHVideoRequestOptions()
    options.version = .original
    options.deliveryMode = .highQualityFormat
    options.isNetworkAccessAllowed = true  // iCloud 다운로드 허용

    PHImageManager.default().requestExportSession(
        forVideo: asset,
        options: options,
        exportPreset: AVAssetExportPresetPassthrough
    ) { exportSession, info in
        guard let session = exportSession else { return }

        session.outputURL = outputURL
        session.outputFileType = .mp4

        session.exportAsynchronously {
            switch session.status {
            case .completed:
                print("내보내기 완료: \(outputURL)")
            case .failed:
                print("실패: \(session.error?.localizedDescription ?? "")")
            default:
                break
            }
        }
    }
}
```

### 권한 요청

```swift
import Photos

func requestPhotoLibraryAccess() {
    PHPhotoLibrary.requestAuthorization(for: .readWrite) { status in
        switch status {
        case .authorized:
            print("전체 접근 권한 획득")
        case .limited:
            print("제한된 접근 권한")
        case .denied, .restricted:
            print("접근 거부됨")
        default:
            break
        }
    }
}
```

## 접근 방법 3: 직접 데이터베이스 접근 (고급)

### SQLite 데이터베이스 쿼리

⚠️ **주의**: 직접 DB 접근은 권장하지 않습니다. Apple이 스키마를 변경할 수 있습니다.

```bash
# Photos 라이브러리 DB 복사 (읽기 전용으로 작업)
cp ~/Pictures/Photos\ Library.photoslibrary/database/Photos.sqlite /tmp/

# SQLite로 쿼리
sqlite3 /tmp/Photos.sqlite

# 비디오 에셋 조회
SELECT
    ZASSET.ZUUID,
    ZASSET.ZFILENAME,
    ZASSET.ZDATECREATED,
    ZASSET.ZDURATION
FROM ZASSET
WHERE ZASSET.ZKIND = 1  -- 1 = 비디오
LIMIT 10;
```

## 접근 방법 4: Finder/Spotlight 활용

### Spotlight 쿼리로 비디오 찾기

```bash
# Photos 라이브러리 내 비디오 검색
mdfind -onlyin ~/Pictures/Photos\ Library.photoslibrary \
  'kMDItemContentType == "public.movie"'
```

### AppleScript 활용

```applescript
tell application "Photos"
    set allVideos to every media item whose type description is "Movie"

    repeat with v in allVideos
        set vidName to filename of v
        set vidDate to date of v
        log "비디오: " & vidName & " - " & vidDate
    end repeat
end tell
```

## iCloud 고려 사항

### 로컬 저장 vs iCloud

> "PhotoKit API는 기기에서 사용 가능한 사진과 클라우드에서 사용 가능한 사진을 반드시 구분하지 않습니다."
> — [objc.io](https://www.objc.io/issues/21-camera-and-photos/the-photos-framework/)

### 네트워크 접근 제어

```swift
// PhotoKit에서 네트워크 접근 비활성화 (로컬 파일만)
let options = PHVideoRequestOptions()
options.isNetworkAccessAllowed = false
```

### osxphotos에서 iCloud 처리

```bash
# iCloud 비디오 다운로드 포함
osxphotos export ~/Videos --only-movies --download-missing

# 로컬에 있는 비디오만
osxphotos export ~/Videos --only-movies --skip-missing
```

## 메타데이터 접근

### osxphotos로 메타데이터 추출

```python
import osxphotos

photosdb = osxphotos.PhotosDB()

for video in photosdb.photos():
    if video.ismovie:
        metadata = {
            "filename": video.original_filename,
            "date": video.date,
            "location": video.location,  # (위도, 경도)
            "duration": video.duration,
            "albums": video.albums,
            "keywords": video.keywords,
            "persons": video.persons,
            "favorite": video.favorite,
            "hidden": video.hidden,
        }
        print(metadata)
```

### PhotoKit으로 메타데이터

```swift
let asset: PHAsset = // ...

// 기본 메타데이터
let creationDate = asset.creationDate
let location = asset.location  // CLLocation
let duration = asset.duration
let isFavorite = asset.isFavorite

// EXIF 데이터 (PHAssetResource 사용)
let resources = PHAssetResource.assetResources(for: asset)
for resource in resources {
    print("파일명: \(resource.originalFilename)")
    print("UTI: \(resource.uniformTypeIdentifier)")
}
```

## 권장 접근 방식

| 사용 목적 | 권장 방법 |
|-----------|-----------|
| 빠른 스크립팅/자동화 | osxphotos CLI |
| Python 통합 | osxphotos Python API |
| Swift/macOS 앱 개발 | PhotoKit Framework |
| 일회성 작업 | AppleScript |
| 고급 커스터마이징 | PhotoKit + osxphotos 조합 |

## 참고 자료

- [osxphotos GitHub](https://github.com/RhetTbull/osxphotos)
- [osxphotos Documentation](https://rhettbull.github.io/osxphotos/overview.html)
- [Apple PhotoKit Documentation](https://developer.apple.com/documentation/photokit)
- [Apple - System Photo Library](https://support.apple.com/en-us/104946)
- [objc.io - The Photos Framework](https://www.objc.io/issues/21-camera-and-photos/the-photos-framework/)
