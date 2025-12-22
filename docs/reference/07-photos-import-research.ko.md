# Photos 라이브러리 Import API 연구

## 개요

이 문서는 변환된 비디오를 메타데이터를 보존하면서 macOS Photos 라이브러리로 다시 가져오기 위해 사용 가능한 API와 방법에 대한 연구 결과를 제시합니다.

**관련 이슈**: #100 - Photos 라이브러리 import API 및 제한사항 조사

## 연구 질문 요약

| 질문 | 답변 |
|------|------|
| osxphotos로 사진/비디오 import 가능? | 가능, CLI `osxphotos import` 명령어 |
| PhotoScript가 import 지원? | 가능, `PhotosLibrary.import_photos()` |
| 앨범 멤버십 보존 가능? | 가능, import 후 AppleScript로 |
| 즐겨찾기/메타데이터 보존 가능? | 부분적 - EXIF 자동 보존, 즐겨찾기는 AppleScript로 |
| 주요 제한사항? | 속도(AppleScript), 공유 앨범 접근, macOS 버전 호환성 |

## API 평가

### 1. osxphotos

> "OSXPhotos는 macOS의 Apple Photos에서 사진과 관련 메타데이터를 작업하기 위한 Python 앱입니다."
> — [GitHub - RhetTbull/osxphotos](https://github.com/RhetTbull/osxphotos)

#### Import 기능

"Importapalooza 릴리스"에서 import 기능 추가:

```bash
# CLI import
osxphotos import /path/to/video.mp4 --album "Converted Videos"

# export 데이터베이스의 메타데이터로 import
osxphotos import /path/to/videos --exportdb /path/to/export.db
```

#### 제한사항

- Import는 주로 osxphotos export에서 라이브러리 재생성용으로 설계
- import 작업을 위한 직접적인 Python API 제한적
- 내부적으로 AppleScript 사용

#### 권장 사항

**용도**: 메타데이터 추출, 라이브러리 쿼리, import 후 검증

### 2. PhotoScript

> "Python으로 Apple/MacOS Photos 앱 자동화. AppleScript 호출을 Python으로 래핑."
> — [GitHub - RhetTbull/PhotoScript](https://github.com/RhetTbull/PhotoScript)

#### Import 기능

```python
import photoscript

photoslib = photoscript.PhotosLibrary()
new_album = photoslib.create_album("Converted Videos")
photoslib.import_photos(["/path/to/video.mp4"], album=new_album)
```

#### 사용 가능한 메타데이터 작업

| 속성 | 읽기 | 쓰기 |
|------|------|------|
| title | 가능 | 가능 |
| description | 가능 | 가능 |
| keywords | 가능 | 가능 |
| favorite | 가능 | 가능 (AppleScript) |
| albums | 가능 | 가능 (앨범에 추가) |
| date | 가능 | 불가 (import 전 ExifTool 사용) |
| location | 가능 | 불가 (import 전 ExifTool 사용) |

#### 제한사항

- Python -> Objective-C -> AppleScript 왕복으로 인한 느린 성능
- Photos의 AppleScript 딕셔너리에 의해 제한
- 앨범에서 사진 제거 불가 (우회 필요)

#### 권장 사항

**용도**: 주요 import 방법, 앨범 할당, 즐겨찾기 설정

### 3. photokit (개발 중)

> "Apple의 네이티브 PhotoKit 프레임워크를 통해 macOS Photos.app 라이브러리에 접근하기 위한 Python 패키지."
> — [GitHub - RhetTbull/photokit](https://github.com/RhetTbull/photokit)

#### Import 기능

```python
import photokit

# 안정화 시 사용 가능한 메서드
photokit.add_video("/path/to/video.mp4")  # UUID 반환
photokit.add_live_photo(photo_path, video_path)
```

#### 상태

- **현재 프로덕션 준비 안됨**
- osxphotos 코드베이스에서 추출 중
- 비공개, 문서화되지 않은 PhotoKit API 사용
- macOS Monterey (12.0) 이상 필요

#### 권장 사항

**사용 금지**: 안정 릴리스 대기, 프로젝트 진행 상황 모니터링

### 4. 직접 AppleScript

#### Import 문법

```applescript
tell application "Photos"
    -- 비디오 파일 import
    set importedItems to import POSIX file "/path/to/video.mp4"

    -- import된 항목 UUID 가져오기
    if (count of importedItems) > 0 then
        set importedPhoto to item 1 of importedItems
        set photoUUID to id of importedPhoto

        -- 즐겨찾기 설정
        set favorite of importedPhoto to true

        -- 앨범에 추가
        if exists album "Converted Videos" then
            add importedItems to album "Converted Videos"
        else
            set newAlbum to make new album named "Converted Videos"
            add importedItems to newAlbum
        end if

        return photoUUID
    end if
end tell
```

#### 핵심 사항

1. **`POSIX file` 사용**: 문자열 경로는 샌드박싱으로 실패
2. **메타데이터 처리**: Photos가 파일에서 EXIF 자동 읽기
3. **앨범 할당**: import 후 수행해야 함
4. **UUID 검색**: `id of importedPhoto`로 가능

#### Subprocess 통합 (Python)

```python
import subprocess

def import_video_applescript(video_path: str, album_name: str) -> str:
    """AppleScript subprocess로 비디오 import."""
    script = f'''
    tell application "Photos"
        set importedItems to import POSIX file "{video_path}" skip check duplicates yes
        if (count of importedItems) > 0 then
            set importedPhoto to item 1 of importedItems
            set photoUUID to id of importedPhoto

            if not (exists album "{album_name}") then
                make new album named "{album_name}"
            end if
            add importedItems to album "{album_name}"

            return photoUUID
        end if
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"AppleScript 실패: {result.stderr}")

    return result.stdout.strip()
```

## 에지 케이스 및 제한사항

### iCloud 사진 보관함

| 시나리오 | 동작 |
|----------|------|
| iCloud 라이브러리로 import | 작동, iCloud로 자동 업로드 |
| 오프라인 상태에서 import | 로컬에서 작동, 온라인 시 동기화 |
| iCloud에만 있는 원본 | import에 해당 없음 (새 파일은 로컬 우선) |

**완화**: import 시도 전 항상 로컬 파일 존재 확인.

### 공유 앨범

> "OSXPhotos는 macOS 26.x (Tahoe)에서 공유 앨범을 읽을 수 없습니다."
> — [osxphotos 문서](https://github.com/RhetTbull/osxphotos)

| 제한사항 | 영향 |
|----------|------|
| AppleScript로 공유 앨범에 추가 불가 | 네이티브 Photos.app 사용 필요 |
| 공유 앨범 내용 안정적으로 읽기 불가 | 검증에서 공유 앨범 건너뛰기 |
| 배치당 1000장 다운로드 제한 | import 작업에는 해당 없음 |

**완화**: 개인 앨범에만 할당; 공유 앨범 제한사항 문서화.

### 라이브 포토

| 측면 | 상태 |
|------|------|
| 비디오 컴포넌트만 import | 작동 |
| 라이브 포토로 import | 쌍으로 된 HEIC + MOV 필요 |
| photokit `add_live_photo()` | 아직 안정화 안됨 |

**완화**: 현재는 변환된 비디오를 일반 비디오로 import; 라이브 포토 재생성은 범위 외.

### 폴더와 스마트 앨범

> "Catalina 이후, 폴더 내의 앨범은 더 이상 AppleScript의 앨범 배열/목록을 통해 볼 수 없습니다."
> — [Apple Community](https://discussions.apple.com/thread/253467)

| 유형 | AppleScript 접근 |
|------|------------------|
| 최상위 앨범 | 전체 접근 |
| 폴더 내 앨범 | macOS Catalina 이후 제한/고장 |
| 스마트 앨범 | 항목 추가 불가 (자동 채워짐) |

**완화**: 최상위 앨범에만 할당; 폴더 제한사항 사용자에게 경고.

### HDR 비디오

| 측면 | 상태 |
|------|------|
| HDR 비디오 import | 작동 |
| HDR 메타데이터 보존 | FFmpeg 인코딩에 따름 |
| Photos에서 표시 | 적절한 태그 필요 |

**완화**: 변환 중 FFmpeg가 HDR 메타데이터 보존하도록 보장.

## 성능 고려사항

### AppleScript 오버헤드

| 작업 | 예상 시간 |
|------|----------|
| 단일 비디오 import | 2-5초 |
| 앨범에 추가 | 0.5-1초 |
| 즐겨찾기 설정 | 0.5-1초 |
| 배치 import (10개 비디오) | 20-50초 |

> "모든 메서드 호출은 python->Objective C->AppleScript 왕복을 해야 하므로 네이티브 Python 코드보다 훨씬 느립니다."
> — [PhotoScript README](https://github.com/RhetTbull/PhotoScript)

### 배치 Import 전략

```python
# 권장: 파일은 개별 import하되 메타데이터 작업은 배치로
def batch_import(videos: list[Path], album_name: str) -> list[str]:
    uuids = []
    for video in videos:
        uuid = import_single(video)
        uuids.append(uuid)

    # 배치 앨범 할당
    add_to_album_batch(uuids, album_name)
    return uuids
```

## 권장 구현 접근법

### 하이브리드 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                 Photos Re-Import 워크플로우                  │
├─────────────────────────────────────────────────────────────┤
│  1. 메타데이터 캡처 (osxphotos)                              │
│     └─ 앨범, 즐겨찾기, 날짜, 위치 읽기                       │
│                                                              │
│  2. 메타데이터 임베딩 (ExifTool)                             │
│     └─ 파일에 날짜, 위치, 설명 쓰기                          │
│                                                              │
│  3. Import (subprocess를 통한 AppleScript)                   │
│     └─ import POSIX file, UUID 가져오기                      │
│                                                              │
│  4. 메타데이터 적용 (PhotoScript 또는 AppleScript)           │
│     ├─ 앨범에 추가                                           │
│     ├─ 즐겨찾기 설정                                         │
│     └─ 필요시 제목/설명 설정                                 │
│                                                              │
│  5. 검증 (osxphotos)                                         │
│     └─ 메타데이터가 예상 값과 일치하는지 확인                │
└─────────────────────────────────────────────────────────────┘
```

### 의존성 선택

| 컴포넌트 | 권장 라이브러리 | 이유 |
|----------|----------------|------|
| 메타데이터 캡처 | osxphotos | 가장 완전한 메타데이터 접근 |
| 메타데이터 임베딩 | ExifTool | 산업 표준, 신뢰성 |
| 비디오 import | AppleScript (subprocess) | 직접 제어, UUID 검색 |
| 앨범/즐겨찾기 할당 | PhotoScript 또는 AppleScript | Python 통합 |
| 검증 | osxphotos | 포괄적인 메타데이터 읽기 |

### 에러 처리 전략

```python
class PhotosImportError(Exception):
    """import 작업의 기본 예외."""
    pass

class ImportTimeoutError(PhotosImportError):
    """import가 타임아웃을 초과할 때 발생."""
    pass

class AlbumNotFoundError(PhotosImportError):
    """대상 앨범이 존재하지 않을 때 발생."""
    pass

class VerificationFailedError(PhotosImportError):
    """import 후 검증이 실패할 때 발생."""
    pass
```

## 개념 증명

### 최소 Import 예제

```python
import subprocess
from pathlib import Path

def proof_of_concept_import(video_path: Path) -> str:
    """Photos import를 위한 최소 개념 증명."""
    script = f'''
    tell application "Photos"
        set importedItems to import POSIX file "{video_path}"
        if (count of importedItems) > 0 then
            return id of item 1 of importedItems
        else
            error "Import returned no items"
        end if
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode == 0:
        return result.stdout.strip()
    else:
        raise RuntimeError(f"Import 실패: {result.stderr}")

# 테스트
# uuid = proof_of_concept_import(Path("/path/to/test.mp4"))
# print(f"Imported with UUID: {uuid}")
```

## 위험 평가

| 위험 | 확률 | 영향 | 완화 |
|------|------|------|------|
| AppleScript API 변경 | 낮음 | 높음 | 버전 확인, 폴백 핸들러 |
| import 중 Photos.app 충돌 | 중간 | 중간 | 재시도 로직, 검증 |
| import 중 메타데이터 손실 | 낮음 | 높음 | 파일에 메타데이터 사전 임베드 |
| 대량 배치 시 느린 성능 | 높음 | 중간 | 진행 상황 보고, 배치 제한 |
| iCloud 동기화 충돌 | 낮음 | 중간 | import 전 로컬 파일 확인 |
| 공유 앨범 제한 | 높음 | 낮음 | 제한사항 문서화, 공유 건너뛰기 |

## 결론

### 실현 가능성: 확인됨

연구 결과 Photos 라이브러리 re-import 구현이 다음을 사용하여 가능함을 확인:

1. **AppleScript** (subprocess 또는 PhotoScript) - import 작업용
2. **osxphotos** - 메타데이터 캡처 및 검증용
3. **ExifTool** - import 전 메타데이터 임베딩용

### 권장 다음 단계

1. **PhotosImporter 클래스 구현** (#101) - AppleScript subprocess 사용
2. **메타데이터 보존 구현** (#103) - ExifTool + AppleScript 사용
3. **원본 처리 추가** (#102) - AppleScript 삭제/보관 사용
4. **포괄적 테스트 작성** (#104) - 모킹된 AppleScript로

### 문서화할 알려진 제한사항

- 공유 앨범은 AppleScript를 통해 접근 불가
- 폴더 내 앨범은 macOS Catalina 이후 접근 불가능할 수 있음
- 라이브 포토 재생성 미지원 (범위 외)
- AppleScript 왕복으로 인한 성능 제한

## 참고 자료

- [osxphotos GitHub](https://github.com/RhetTbull/osxphotos)
- [PhotoScript GitHub](https://github.com/RhetTbull/PhotoScript)
- [photokit GitHub](https://github.com/RhetTbull/photokit)
- [Apple Photos AppleScript Dictionary](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide)
- [AppleScript for Photos Community Discussion](https://discussions.apple.com/thread/252917619)
- [MacScripter Photos Import Thread](https://www.macscripter.net/t/help-importing-photos-to-specific-album-in-photos-app/68736)
