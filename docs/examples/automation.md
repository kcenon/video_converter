# Automation Examples

Examples for automated video conversion workflows.

## launchd Automation

### Install Daily Automation

```bash
# Install service to run daily at 3 AM
video-converter install --time 03:00
```

### Custom Schedule

```bash
# Weekdays only at 2:30 AM
video-converter install --time 02:30 --days weekdays

# Every Sunday at 4 AM
video-converter install --time 04:00 --day sunday
```

### Configuration File

Create `~/.config/video_converter/automation.json`:

```json
{
  "schedule": {
    "enabled": true,
    "time": "03:00",
    "days": ["monday", "wednesday", "friday"]
  },
  "conversion": {
    "mode": "photos",
    "encoder": "hardware",
    "quality": 45,
    "concurrent": 2
  },
  "notification": {
    "on_complete": true,
    "on_error": true
  },
  "filters": {
    "min_size_mb": 50,
    "exclude_albums": ["Screenshots", "Bursts"]
  }
}
```

## Python Automation

### Scheduled Task with Python

```python
import asyncio
from datetime import datetime, time
from video_converter.core.orchestrator import Orchestrator
from video_converter.core.config import Config

async def run_daily_conversion():
    """Run conversion at scheduled time."""
    target_time = time(3, 0)  # 3:00 AM

    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), target_time)

        if now.time() > target_time:
            # Already past target time, schedule for tomorrow
            target = target + timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"Next run scheduled for {target}")

        await asyncio.sleep(wait_seconds)

        # Run conversion
        config = Config.load()
        orchestrator = Orchestrator(config)
        result = await orchestrator.run_batch(mode="photos")

        print(f"Completed: {result.successful}/{result.total} videos")

if __name__ == "__main__":
    asyncio.run(run_daily_conversion())
```

### Event-Driven Automation

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class VideoHandler(FileSystemEventHandler):
    """Watch folder for new videos."""

    def __init__(self, converter):
        self.converter = converter
        self.pending = []

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in {'.mp4', '.mov', '.avi'}:
            print(f"New video detected: {path}")
            self.pending.append(path)
            asyncio.create_task(self.process_video(path))

    async def process_video(self, path: Path):
        # Wait for file to be fully written
        await asyncio.sleep(5)

        output = path.with_stem(f"{path.stem}_hevc")
        result = await self.converter.convert_single(path, output)

        if result.success:
            print(f"Converted: {path} -> {output}")

# Setup watcher
watch_path = Path("~/Videos/Incoming").expanduser()
observer = Observer()
observer.schedule(VideoHandler(converter), str(watch_path), recursive=True)
observer.start()
```

## Shell Scripts

### Nightly Conversion Script

```bash
#!/bin/bash
# nightly_convert.sh

LOG_DIR="$HOME/.local/share/video_converter/logs"
LOG_FILE="$LOG_DIR/nightly_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "=== Starting nightly conversion $(date) ===" >> "$LOG_FILE"

# Run conversion
video-converter run --mode photos \
    --concurrent 2 \
    --exclude-album "Screenshots" \
    --exclude-album "Bursts" \
    >> "$LOG_FILE" 2>&1

status=$?

if [ $status -eq 0 ]; then
    osascript -e 'display notification "Nightly conversion complete" with title "Video Converter"'
else
    osascript -e 'display notification "Conversion failed - check logs" with title "Video Converter"'
fi

echo "=== Completed $(date) with status $status ===" >> "$LOG_FILE"

# Cleanup old logs (keep 30 days)
find "$LOG_DIR" -name "nightly_*.log" -mtime +30 -delete
```

### Add to crontab

```bash
# Edit crontab
crontab -e

# Add line for 3 AM daily
0 3 * * * /path/to/nightly_convert.sh
```

## Integration Examples

### Slack Notification

```python
import httpx
from video_converter.core.orchestrator import Orchestrator

async def convert_with_slack_notification():
    """Convert and send Slack notification."""
    orchestrator = Orchestrator(Config.load())
    result = await orchestrator.run_batch(mode="photos")

    # Send Slack notification
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if webhook_url:
        message = {
            "text": f"Video Conversion Complete\n"
                    f"• Processed: {result.successful}/{result.total}\n"
                    f"• Space saved: {format_size(result.space_saved)}"
        }
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=message)
```

### Email Report

```python
import smtplib
from email.mime.text import MIMEText

def send_email_report(result):
    """Send conversion report via email."""
    msg = MIMEText(f"""
    Video Conversion Report
    ========================

    Total videos: {result.total}
    Successful: {result.successful}
    Failed: {result.failed}

    Original size: {format_size(result.original_size)}
    Converted size: {format_size(result.converted_size)}
    Space saved: {format_size(result.space_saved)} ({result.compression_ratio:.1%})

    Duration: {result.duration}
    """)

    msg['Subject'] = f"Video Conversion Report - {datetime.now().date()}"
    msg['From'] = os.environ.get("EMAIL_FROM")
    msg['To'] = os.environ.get("EMAIL_TO")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(os.environ.get("EMAIL_FROM"), os.environ.get("EMAIL_PASSWORD"))
        smtp.send_message(msg)
```

### Home Assistant Integration

```yaml
# configuration.yaml
shell_command:
  convert_videos: '/path/to/video-converter run --mode photos --quiet'

automation:
  - alias: "Nightly Video Conversion"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: shell_command.convert_videos
```

## Monitoring

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

# Check if service is loaded
if launchctl list | grep -q "videoconverter"; then
    echo "Service: Active"
else
    echo "Service: Not Running"
    exit 1
fi

# Check last run
last_log=$(ls -t ~/.local/share/video_converter/logs/*.log | head -1)
if [ -n "$last_log" ]; then
    last_run=$(stat -f "%Sm" "$last_log")
    echo "Last run: $last_run"
else
    echo "No logs found"
fi

# Check disk space
available=$(df -h ~ | awk 'NR==2 {print $4}')
echo "Available disk space: $available"
```
