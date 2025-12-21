# 데이터 흐름 및 상태 다이어그램

## 1. 데이터 흐름 다이어그램 (DFD)

### 1.1 Context Diagram (Level 0)

```mermaid
graph LR
    USER((사용자))
    SYSTEM[Video Converter<br/>System]
    PHOTOS[(macOS Photos)]
    STORAGE[(File Storage)]
    ICLOUD[(iCloud)]

    USER -->|설정, 명령| SYSTEM
    SYSTEM -->|상태, 알림| USER

    PHOTOS -->|원본 비디오| SYSTEM
    SYSTEM -->|변환된 비디오| STORAGE

    ICLOUD -->|클라우드 비디오| PHOTOS
```

### 1.2 Level 1 DFD

```mermaid
graph TB
    subgraph ExternalEntities["External Entities"]
        USER((사용자))
        PHOTOS[(Photos Library)]
        FS[(File System)]
    end

    subgraph Processes["Processes"]
        P1["1.0<br/>비디오 추출"]
        P2["2.0<br/>코덱 분석"]
        P3["3.0<br/>비디오 변환"]
        P4["4.0<br/>메타데이터 처리"]
        P5["5.0<br/>품질 검증"]
        P6["6.0<br/>결과 보고"]
    end

    subgraph DataStores["Data Stores"]
        D1[(설정 파일)]
        D2[(변환 로그)]
        D3[(처리 큐)]
        D4[(통계 DB)]
    end

    USER -->|설정| D1
    D1 -->|설정값| P1
    D1 -->|인코딩 옵션| P3

    PHOTOS -->|비디오 목록| P1
    P1 -->|추출된 비디오| D3
    D3 -->|대기 비디오| P2

    P2 -->|H.264 비디오| P3
    P2 -->|이미 HEVC| P6

    P3 -->|변환된 비디오| P4
    P3 -->|진행 상황| P6

    P4 -->|메타데이터 복원| P5

    P5 -->|검증 완료| FS
    P5 -->|검증 실패| P3

    P6 -->|알림| USER
    P6 -->|로그| D2
    P6 -->|통계| D4
```

### 1.3 Level 2 DFD - 비디오 변환 프로세스 상세

```mermaid
graph TB
    subgraph VideoConversion["3.0 비디오 변환"]
        P3_1["3.1<br/>입력 검증"]
        P3_2["3.2<br/>FFmpeg 명령 구성"]
        P3_3["3.3<br/>인코딩 실행"]
        P3_4["3.4<br/>진행률 모니터링"]
        P3_5["3.5<br/>오류 처리"]
    end

    INPUT[입력 비디오] --> P3_1
    CONFIG[인코딩 설정] --> P3_2

    P3_1 -->|유효한 입력| P3_2
    P3_1 -->|무효한 입력| ERROR[오류 큐]

    P3_2 -->|FFmpeg 명령| P3_3
    P3_3 -->|진행 데이터| P3_4
    P3_3 -->|오류| P3_5

    P3_4 -->|진행률| PROGRESS[진행률 표시]
    P3_5 -->|재시도| P3_3
    P3_5 -->|실패| ERROR

    P3_3 -->|성공| OUTPUT[출력 비디오]
```

## 2. 데이터 변환 흐름

### 2.1 비디오 파일 변환 경로

```mermaid
flowchart LR
    subgraph PhotosLibrary["Photos Library"]
        ORIG["원본 H.264<br/>video.mov<br/>1.5GB"]
    end

    subgraph TempDirectory["Temp Directory"]
        EXPORT["내보낸 복사본<br/>video_export.mov<br/>1.5GB"]
    end

    subgraph Processing["Processing"]
        DECODE["H.264 디코딩<br/>Raw Frames"]
        ENCODE["H.265 인코딩<br/>VideoToolbox"]
    end

    subgraph OutputDirectory["Output Directory"]
        HEVC["변환된 H.265<br/>video_hevc.mp4<br/>~750MB"]
    end

    subgraph ProcessedDirectory["Processed Directory"]
        BACKUP["원본 백업<br/>video.mov"]
    end

    ORIG -->|osxphotos export| EXPORT
    EXPORT -->|FFmpeg 입력| DECODE
    DECODE -->|프레임 데이터| ENCODE
    ENCODE -->|FFmpeg 출력| HEVC
    EXPORT -->|변환 성공 후| BACKUP
```

### 2.2 메타데이터 흐름

```mermaid
flowchart TB
    subgraph SourceMetadata["Source Metadata"]
        M1["QuickTime Metadata"]
        M2["EXIF/XMP Tags"]
        M3["GPS Coordinates"]
        M4["Creation Date"]
        M5["Camera Info"]
    end

    subgraph Extraction["Extraction"]
        FFPROBE["FFprobe<br/>기본 메타데이터"]
        EXIFTOOL_R["ExifTool<br/>상세 메타데이터"]
    end

    subgraph TransferMethods["Transfer Methods"]
        MAP_META["FFmpeg<br/>-map_metadata 0"]
        TAG_COPY["ExifTool<br/>-tagsFromFile"]
        TOUCH["touch -r<br/>타임스탬프"]
    end

    subgraph TargetMetadata["Target Metadata"]
        T1["QuickTime Metadata"]
        T2["EXIF/XMP Tags"]
        T3["GPS Coordinates"]
        T4["File Timestamps"]
    end

    M1 --> FFPROBE
    M2 --> EXIFTOOL_R
    M3 --> EXIFTOOL_R
    M4 --> EXIFTOOL_R
    M5 --> EXIFTOOL_R

    FFPROBE --> MAP_META
    EXIFTOOL_R --> TAG_COPY
    M4 --> TOUCH

    MAP_META --> T1
    TAG_COPY --> T2
    TAG_COPY --> T3
    TOUCH --> T4
```

## 3. 상태 다이어그램

### 3.1 비디오 처리 상태

```mermaid
stateDiagram-v2
    [*] --> Discovered: 비디오 발견

    Discovered --> Queued: 변환 대상 확인
    Discovered --> Skipped: 이미 HEVC

    Queued --> Exporting: 내보내기 시작
    Exporting --> Exported: 내보내기 완료
    Exporting --> ExportFailed: 내보내기 실패

    ExportFailed --> Queued: 재시도
    ExportFailed --> Failed: 최대 재시도 초과

    Exported --> Converting: 변환 시작
    Converting --> Converted: 변환 성공
    Converting --> ConvertFailed: 변환 실패

    ConvertFailed --> Converting: 재시도
    ConvertFailed --> Failed: 최대 재시도 초과

    Converted --> Validating: 품질 검증
    Validating --> Validated: 검증 통과
    Validating --> ConvertFailed: 검증 실패

    Validated --> Finalizing: 메타데이터 복원
    Finalizing --> Completed: 완료

    Completed --> [*]
    Skipped --> [*]
    Failed --> [*]

    note right of Converting
        진행률 업데이트
        0% → 100%
    end note

    note right of Failed
        failed 폴더로 이동
        에러 로그 기록
    end note
```

### 3.2 시스템 운영 상태

```mermaid
stateDiagram-v2
    [*] --> Idle: 시스템 시작

    Idle --> Triggered: 트리거 발생
    note right of Triggered
        - 스케줄 시간 도달
        - 폴더 변경 감지
        - 수동 실행
    end note

    Triggered --> Initializing: 초기화 시작
    Initializing --> Scanning: 스캔 시작

    Scanning --> Processing: 처리 대상 있음
    Scanning --> Idle: 처리 대상 없음

    Processing --> BatchRunning: 배치 실행

    state BatchRunning {
        [*] --> ExtractingBatch
        ExtractingBatch --> ConvertingBatch
        ConvertingBatch --> FinalizingBatch
        FinalizingBatch --> [*]
    }

    BatchRunning --> Reporting: 배치 완료

    Reporting --> Notifying: 보고서 생성 완료
    Notifying --> Cleaning: 알림 발송 완료

    Cleaning --> Idle: 정리 완료

    Idle --> Shutdown: 종료 요청
    Processing --> Shutdown: 강제 종료
    Shutdown --> [*]

    note right of Idle
        ThrottleInterval 대기
        (기본 30초)
    end note
```

### 3.3 FFmpeg 프로세스 상태

```mermaid
stateDiagram-v2
    [*] --> Ready: 명령 준비됨

    Ready --> Spawning: 프로세스 생성
    Spawning --> Running: 프로세스 시작됨

    Running --> Running: 프레임 처리 중
    note right of Running
        - 진행률 업데이트
        - CPU/메모리 모니터링
    end note

    Running --> Succeeded: exit code 0
    Running --> Failed: exit code != 0
    Running --> Timeout: 시간 초과
    Running --> Cancelled: 사용자 취소

    Failed --> Analyzing: 에러 분석
    Analyzing --> Retryable: 재시도 가능
    Analyzing --> NonRetryable: 재시도 불가

    Retryable --> Ready: 재시도 대기 후

    Succeeded --> [*]
    NonRetryable --> [*]
    Timeout --> [*]
    Cancelled --> [*]
```

## 4. 처리 큐 관리

### 4.1 큐 상태 전이

```mermaid
stateDiagram-v2
    direction LR

    state PendingQueue {
        [*] --> Waiting
        Waiting --> Ready: 리소스 사용 가능
    }

    state ProcessingQueue {
        Ready --> InProgress: 워커 할당
        InProgress --> Completing: 처리 완료
    }

    state CompletedQueue {
        Completing --> Success
        Completing --> Failure
    }

    PendingQueue --> ProcessingQueue: dequeue
    ProcessingQueue --> CompletedQueue: finish
    CompletedQueue --> PendingQueue: retry (on failure)
```

### 4.2 동시 처리 관리

```mermaid
graph TB
    subgraph QueueManager["Queue Manager"]
        PENDING[("Pending Queue<br/>최대 1000")]
        ACTIVE[("Active Queue<br/>최대 2")]
        DONE[("Completed Queue")]
        FAILED[("Failed Queue")]
    end

    subgraph Workers["Workers"]
        W1["Worker 1<br/>하드웨어"]
        W2["Worker 2<br/>하드웨어"]
    end

    PENDING -->|dequeue| W1
    PENDING -->|dequeue| W2

    W1 -->|success| DONE
    W1 -->|failure| FAILED

    W2 -->|success| DONE
    W2 -->|failure| FAILED

    FAILED -->|retry < 3| PENDING
```

## 5. 에러 상태 및 복구

### 5.1 에러 분류 및 처리

```mermaid
stateDiagram-v2
    [*] --> Error: 오류 발생

    Error --> Analyzing: 오류 분석

    state Analyzing {
        [*] --> Classify
        Classify --> Transient: 일시적 오류
        Classify --> Permanent: 영구적 오류
        Classify --> Unknown: 알 수 없는 오류
    }

    Transient --> RetryWithBackoff: 재시도 가능
    note right of Transient
        - 네트워크 타임아웃
        - 리소스 부족
        - iCloud 동기화 지연
    end note

    Permanent --> LogAndSkip: 건너뛰기
    note right of Permanent
        - 손상된 파일
        - 지원하지 않는 형식
        - 권한 없음
    end note

    Unknown --> LogAndRetry: 로깅 후 재시도
    LogAndRetry --> RetryWithBackoff

    RetryWithBackoff --> Wait: 대기
    Wait --> [*]: 재처리

    LogAndSkip --> MoveToFailed
    MoveToFailed --> [*]

    note right of Wait
        Backoff 전략:
        attempt 1: 5초
        attempt 2: 10초
        attempt 3: 20초
    end note
```

### 5.2 복구 워크플로우

```mermaid
flowchart TB
    START[에러 발생] --> CHECK_TYPE{에러 유형?}

    CHECK_TYPE -->|파일 없음| FILE_ERROR[FileNotFound]
    CHECK_TYPE -->|권한 없음| PERM_ERROR[PermissionDenied]
    CHECK_TYPE -->|디스크 공간| DISK_ERROR[DiskSpace]
    CHECK_TYPE -->|FFmpeg 오류| FFMPEG_ERROR[FFmpegError]
    CHECK_TYPE -->|iCloud| ICLOUD_ERROR[iCloudError]

    FILE_ERROR --> SKIP[건너뛰기]
    PERM_ERROR --> REQUEST_PERM[권한 요청 안내]

    DISK_ERROR --> CLEANUP[임시 파일 정리]
    CLEANUP --> RETRY{공간 확보?}
    RETRY -->|Yes| PROCESS[재처리]
    RETRY -->|No| NOTIFY_USER[사용자 알림]

    FFMPEG_ERROR --> ANALYZE_CODE{종료 코드}
    ANALYZE_CODE -->|1| RETRY_SIMPLE[단순 재시도]
    ANALYZE_CODE -->|137| KILLED[메모리 부족]
    ANALYZE_CODE -->|Other| LOG_ERROR[에러 로깅]

    KILLED --> REDUCE_QUALITY[품질 설정 낮춤]
    REDUCE_QUALITY --> PROCESS

    ICLOUD_ERROR --> WAIT_SYNC[동기화 대기]
    WAIT_SYNC --> PROCESS

    RETRY_SIMPLE --> PROCESS
    LOG_ERROR --> SKIP

    SKIP --> MOVE_FAILED[failed 폴더로 이동]
    NOTIFY_USER --> END[종료]
    PROCESS --> END
    REQUEST_PERM --> END
    MOVE_FAILED --> END
```

## 6. 설정 데이터 구조

### 6.1 설정 계층 구조

```mermaid
graph TB
    subgraph ConfigHierarchy["Configuration Hierarchy"]
        DEFAULT["defaults.json<br/>기본 설정"]
        USER["사용자 설정<br/>~/.config/video_converter/"]
        PROJECT["프로젝트 설정<br/>./video_converter.json"]
        CLI["CLI Arguments<br/>명령줄 인자"]
        ENV["Environment Variables<br/>환경 변수"]
    end

    DEFAULT --> MERGED["병합된 설정"]
    USER --> MERGED
    PROJECT --> MERGED
    CLI --> MERGED
    ENV --> MERGED

    MERGED --> VALIDATED["검증된 설정"]
    VALIDATED --> APP["Application"]
```

**우선순위**: CLI > ENV > PROJECT > USER > DEFAULT

### 6.2 런타임 상태 저장

```mermaid
erDiagram
    CONVERSION_STATE {
        string session_id PK
        datetime started_at
        datetime updated_at
        string status
        int total_videos
        int completed
        int failed
        int skipped
    }

    VIDEO_STATE {
        string video_id PK
        string session_id FK
        string original_path
        string output_path
        string status
        int attempt_count
        string last_error
        float progress
    }

    CHECKPOINT {
        string checkpoint_id PK
        string session_id FK
        datetime created_at
        blob state_snapshot
    }

    CONVERSION_STATE ||--o{ VIDEO_STATE : contains
    CONVERSION_STATE ||--o{ CHECKPOINT : has
```

## 7. 로깅 데이터 흐름

### 7.1 로그 수집 및 저장

```mermaid
flowchart LR
    subgraph LogSources["Log Sources"]
        APP_LOG["Application Logs"]
        FFMPEG_LOG["FFmpeg Output"]
        SYSTEM_LOG["System Events"]
    end

    subgraph LogProcessor["Log Processor"]
        FORMATTER["Log Formatter"]
        FILTER["Log Filter"]
        ROUTER["Log Router"]
    end

    subgraph Destinations["Destinations"]
        FILE[("Log Files<br/>~/Library/Logs/")]
        CONSOLE["Console Output"]
        NOTIF["Notification Center"]
    end

    APP_LOG --> FORMATTER
    FFMPEG_LOG --> FORMATTER
    SYSTEM_LOG --> FORMATTER

    FORMATTER --> FILTER
    FILTER --> ROUTER

    ROUTER -->|DEBUG+| FILE
    ROUTER -->|INFO+| CONSOLE
    ROUTER -->|ERROR+| NOTIF
```
