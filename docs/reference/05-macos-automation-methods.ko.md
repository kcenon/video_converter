# macOS 자동화 방법 가이드

## 개요

macOS에서 비디오 변환 자동화를 구현하는 다양한 방법을 정리합니다.

## 자동화 방법 비교

| 방법 | 복잡도 | 신뢰성 | 유연성 | 권장 용도 |
|------|--------|--------|--------|-----------|
| Folder Actions | 낮음 | 중간 | 낮음 | 간단한 자동화 |
| Automator | 낮음 | 중간 | 중간 | GUI 기반 워크플로우 |
| launchd | 중간 | 높음 | 높음 | 데몬/백그라운드 작업 |
| Shell Script + cron | 낮음 | 높음 | 높음 | 주기적 작업 |
| Hazel (서드파티) | 낮음 | 높음 | 높음 | 고급 폴더 감시 |

## 방법 1: Folder Actions

### 소개

> "폴더를 감시하고 들어오는 항목에 대해 조치를 취하는 기능은 완전히 무인으로 작동하는 워크플로우를 만들 수 있는 강력한 자동화 기술입니다."
> — [Apple Developer](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)

### 설정 방법

1. Finder에서 대상 폴더를 Control-클릭
2. **Services** → **Folder Actions Setup** 선택
3. 스크립트 연결

### AppleScript 예시: 비디오 변환 트리거

```applescript
-- ~/Library/Scripts/Folder Action Scripts/ConvertToHEVC.scpt

on adding folder items to this_folder after receiving added_items
    repeat with this_item in added_items
        set item_path to POSIX path of this_item
        set file_ext to name extension of (info for this_item)

        if file_ext is in {"mp4", "mov", "m4v", "MP4", "MOV", "M4V"} then
            -- FFmpeg 변환 실행
            set output_path to item_path & "_hevc.mp4"
            set cmd to "/opt/homebrew/bin/ffmpeg -i " & quoted form of item_path
            set cmd to cmd & " -c:v hevc_videotoolbox -q:v 50 -c:a copy "
            set cmd to cmd & quoted form of output_path

            do shell script cmd
        end if
    end repeat
end adding folder items to
```

### 제한 사항

> "Folder Actions는 수동으로 파일을 추가할 때는 잘 작동하지만, iCloud를 통해 다른 기기에서 동기화된 파일이 '나타나는' 경우에는 작동하지 않을 수 있습니다."
> — [Automators Talk](https://talk.automators.fm/t/watch-folder-with-automator-and-icloud/7864)

## 방법 2: Automator Folder Action

### 설정 단계

1. **Automator** 앱 실행 (⌘ + Space → "Automator")
2. **새 문서** → **Folder Action** 선택
3. 상단에서 대상 폴더 지정
4. **Run Shell Script** 액션 추가

### Automator 워크플로우 예시

```bash
#!/bin/bash
# Automator "Run Shell Script" 액션
# "Pass input: as arguments" 선택

for file in "$@"; do
    # 파일 확장자 확인
    ext="${file##*.}"
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    if [[ "$ext_lower" == "mp4" || "$ext_lower" == "mov" || "$ext_lower" == "m4v" ]]; then
        # 출력 경로 설정
        dir=$(dirname "$file")
        name=$(basename "$file" ".$ext")
        output="${dir}/${name}_hevc.mp4"

        # FFmpeg 변환
        /opt/homebrew/bin/ffmpeg -i "$file" \
            -c:v hevc_videotoolbox \
            -q:v 50 \
            -c:a copy \
            -map_metadata 0 \
            "$output" 2>&1

        # 메타데이터 복원
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$output" 2>/dev/null
    fi
done
```

### 저장 위치

워크플로우 저장 위치:
- 모든 사용자: `/Library/Workflows/Applications/Folder Actions/`
- 현재 사용자: `~/Library/Workflows/Applications/Folder Actions/`

## 방법 3: launchd (권장)

### 소개

launchd는 macOS의 서비스 관리 프레임워크로, 가장 신뢰성 있는 자동화 방법입니다.

> "launchd 작업에 WatchPaths 속성을 설정하면 폴더 감시를 할 수 있습니다. 설정이 조금 번거롭지만 더 안정적입니다."
> — [Automators Talk](https://talk.automators.fm/t/watch-folder-with-automator-and-icloud/7864)

### WatchPaths를 사용한 폴더 감시

#### 1. 변환 스크립트 생성

```bash
#!/bin/bash
# ~/Scripts/convert_to_hevc.sh

WATCH_DIR="$HOME/Videos/ToConvert"
OUTPUT_DIR="$HOME/Videos/Converted"
PROCESSED_DIR="$HOME/Videos/Processed"
LOG_FILE="$HOME/Videos/conversion.log"

mkdir -p "$OUTPUT_DIR" "$PROCESSED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

for file in "$WATCH_DIR"/*.{mp4,mov,m4v,MP4,MOV,M4V} 2>/dev/null; do
    [ -f "$file" ] || continue

    filename=$(basename "$file")
    name="${filename%.*}"
    output="$OUTPUT_DIR/${name}_hevc.mp4"

    log "Converting: $filename"

    /opt/homebrew/bin/ffmpeg -i "$file" \
        -c:v hevc_videotoolbox \
        -q:v 45 \
        -tag:v hvc1 \
        -c:a copy \
        -map_metadata 0 \
        -movflags use_metadata_tags \
        "$output" 2>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        # 메타데이터 복원
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$output" 2>/dev/null
        touch -r "$file" "$output"

        # 원본 이동
        mv "$file" "$PROCESSED_DIR/"
        log "Completed: $filename"
    else
        log "Failed: $filename"
    fi
done
```

#### 2. launchd plist 생성

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/username/Scripts/convert_to_hevc.sh</string>
    </array>

    <key>WatchPaths</key>
    <array>
        <string>/Users/username/Videos/ToConvert</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/username/Videos/launchd_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/username/Videos/launchd_stderr.log</string>

    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
```

#### 3. 서비스 등록 및 시작

```bash
# plist 복사
cp com.user.videoconverter.plist ~/Library/LaunchAgents/

# 서비스 로드
launchctl load ~/Library/LaunchAgents/com.user.videoconverter.plist

# 상태 확인
launchctl list | grep videoconverter

# 서비스 언로드 (필요시)
launchctl unload ~/Library/LaunchAgents/com.user.videoconverter.plist
```

### 주기적 실행 (StartInterval)

```xml
<!-- 매 시간마다 실행 -->
<key>StartInterval</key>
<integer>3600</integer>
```

### 특정 시간에 실행 (StartCalendarInterval)

```xml
<!-- 매일 새벽 2시에 실행 -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

### Python API를 사용한 Plist 생성

video_converter 패키지는 launchd plist 파일을 프로그래밍 방식으로 생성하는 Python API를 제공합니다:

```python
from video_converter.automation import (
    LaunchdPlistGenerator,
    generate_daily_plist,
    generate_watch_plist,
)
from pathlib import Path

# 매일 새벽 3시에 실행하는 plist 생성
generator = LaunchdPlistGenerator()
plist = generator.generate_plist(hour=3, minute=0)
generator.write_plist(plist)

# 또는 편의 함수 사용
plist = generate_daily_plist(hour=3, minute=0)

# 폴더 감시 plist 생성
plist = generate_watch_plist([Path("~/Videos/Import")])
```

주요 기능:
- Python 경로 자동 감지
- 환경 변수 설정 (PATH, PYTHONUNBUFFERED)
- `~/Library/Logs/video_converter/`로 로그 파일 리다이렉션
- 시간 기반 및 폴더 기반 트리거 모두 지원
- macOS `plutil`을 사용한 plist 유효성 검사

## 방법 4: Shell Script + Cron

### crontab 설정

```bash
# crontab 편집
crontab -e

# 매 시간마다 변환 스크립트 실행
0 * * * * /Users/username/Scripts/convert_to_hevc.sh

# 매일 밤 11시에 실행
0 23 * * * /Users/username/Scripts/convert_to_hevc.sh
```

### fswatch를 사용한 실시간 감시

```bash
# fswatch 설치
brew install fswatch

# 실시간 폴더 감시
fswatch -0 ~/Videos/ToConvert | xargs -0 -n 1 ~/Scripts/convert_single.sh
```

## 방법 5: Hazel (서드파티)

### 소개

> "Hazel은 Noodlesoft의 서드파티 앱으로, Folder Actions의 강화된 버전입니다. $42에 구매 가능합니다."
> — [Macworld](https://www.macworld.com/article/634271/attach-action-mac-folder.html)

### 장점

- 복잡한 조건 설정 가능
- GUI로 쉽게 규칙 생성
- 파일 속성 기반 필터링
- iCloud 동기화 파일도 감지

### 규칙 예시

1. **조건**: 확장자가 mp4, mov, m4v
2. **조건**: 파일명에 "_hevc"가 없음
3. **동작**: Shell 스크립트 실행

## Photos 라이브러리 자동 변환 워크플로우

### osxphotos + launchd 통합

```bash
#!/bin/bash
# ~/Scripts/photos_to_hevc.sh

EXPORT_DIR="$HOME/Videos/PhotosExport"
CONVERTED_DIR="$HOME/Videos/Converted"
LOG_FILE="$HOME/Videos/photos_conversion.log"

mkdir -p "$EXPORT_DIR" "$CONVERTED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 1. 아직 변환되지 않은 비디오 내보내기
log "Exporting new videos from Photos..."

osxphotos export "$EXPORT_DIR" \
    --only-movies \
    --skip-edited \
    --update \
    --download-missing \
    2>> "$LOG_FILE"

# 2. 내보낸 비디오 변환
for file in "$EXPORT_DIR"/*.{mp4,mov,m4v,MP4,MOV,M4V} 2>/dev/null; do
    [ -f "$file" ] || continue

    filename=$(basename "$file")
    name="${filename%.*}"

    # 이미 변환된 파일 건너뛰기
    if [ -f "$CONVERTED_DIR/${name}_hevc.mp4" ]; then
        continue
    fi

    log "Converting: $filename"

    /opt/homebrew/bin/ffmpeg -i "$file" \
        -c:v hevc_videotoolbox \
        -q:v 45 \
        -tag:v hvc1 \
        -c:a copy \
        -map_metadata 0 \
        "$CONVERTED_DIR/${name}_hevc.mp4" 2>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$CONVERTED_DIR/${name}_hevc.mp4" 2>/dev/null
        log "Completed: $filename"
    else
        log "Failed: $filename"
    fi
done

log "Batch conversion completed"
```

### launchd로 매일 실행

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.photos-hevc-converter</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/username/Scripts/photos_to_hevc.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

## 보안 고려 사항

### macOS Mojave 이후 권한

> "macOS Mojave부터 AppleScript/JavaScript를 포함한 워크플로우는 처음 실행할 때 사용자의 보안 승인이 필요합니다."
> — [Apple Developer](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)

### Full Disk Access 권한

Photos 라이브러리에 접근하려면:

1. **시스템 설정** → **개인 정보 보호 및 보안** → **전체 디스크 접근 권한**
2. 터미널 또는 스크립트 추가

## 디버깅 및 모니터링

### launchd 로그 확인

```bash
# 서비스 상태 확인
launchctl list | grep videoconverter

# 시스템 로그 확인
log show --predicate 'subsystem == "com.apple.launchd"' --last 1h

# 스크립트 로그 확인
tail -f ~/Videos/conversion.log
```

### 알림 추가

```bash
# 변환 완료 시 macOS 알림
osascript -e 'display notification "비디오 변환 완료" with title "Video Converter"'
```

## 참고 자료

- [Apple - Mac Automation Scripting Guide](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)
- [macosxautomation.com - Folder Actions](http://www.macosxautomation.com/automator/folder-action/index.html)
- [Six Colors - Shortcuts with Folder Actions](https://sixcolors.com/post/2023/08/generation-gap-using-shortcuts-with-folder-actions/)
- [Simple Help - Folder Actions Explained](https://www.simplehelp.net/2007/01/30/folder-actions-for-os-x-explained-with-real-world-examples/)
