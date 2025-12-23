"""Session state management for resumable conversions.

This module implements persistent session state tracking to enable
resuming interrupted video conversions.

SDS Reference: SDS-C01-003
SRS Reference: SRS-603 (Session State Management)

Example:
    >>> from video_converter.core.session import SessionStateManager
    >>> from pathlib import Path
    >>>
    >>> manager = SessionStateManager()
    >>>
    >>> # Create a new session
    >>> session = manager.create_session(
    ...     video_paths=[Path("video1.mov"), Path("video2.mov")],
    ...     output_dir=Path("converted"),
    ... )
    >>>
    >>> # Update session progress
    >>> manager.mark_completed(session.pending_videos[0])
    >>> manager.save()
    >>>
    >>> # Resume an interrupted session
    >>> if manager.has_resumable_session():
    ...     session = manager.load_session()
    ...     # Continue processing pending_videos
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.core.types import (
    ConversionStatus,
    SessionState,
    SessionStatus,
    VideoEntry,
)

if TYPE_CHECKING:
    from video_converter.core.orchestrator import OrchestratorConfig

logger = logging.getLogger(__name__)

# Default paths for session state storage
DEFAULT_STATE_DIR = Path.home() / ".local" / "share" / "video_converter" / "sessions"
DEFAULT_STATE_FILE = "current_session.json"
SESSION_HISTORY_DIR = "history"


class SessionStateError(Exception):
    """Base exception for session state errors."""

    pass


class SessionNotFoundError(SessionStateError):
    """Raised when a session cannot be found."""

    pass


class SessionCorruptedError(SessionStateError):
    """Raised when session data is corrupted."""

    pass


class SessionStateManager:
    """Manages persistent session state for video conversion.

    Provides functionality to:
    - Create and track conversion sessions
    - Save session state to disk periodically
    - Resume from saved state after restart
    - Handle orphaned temporary files
    - Query session status

    Attributes:
        state_dir: Directory for session state files.
        current_session: The currently active session, if any.
    """

    def __init__(
        self,
        state_dir: Path | None = None,
        auto_save_interval: int = 30,
    ) -> None:
        """Initialize the session state manager.

        Args:
            state_dir: Directory for session state files.
                      Defaults to ~/.local/share/video_converter/sessions
            auto_save_interval: Seconds between auto-saves. 0 disables auto-save.
        """
        self.state_dir = state_dir or DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self._current_session: SessionState | None = None
        self._lock = threading.RLock()
        self._auto_save_interval = auto_save_interval
        self._last_save_time: datetime | None = None
        self._dirty = False

        # Check for interrupted sessions on startup
        self._check_interrupted_sessions()

    @property
    def current_session(self) -> SessionState | None:
        """Get the current session."""
        return self._current_session

    @property
    def state_file_path(self) -> Path:
        """Get the path to the current session state file."""
        return self.state_dir / DEFAULT_STATE_FILE

    @property
    def history_dir(self) -> Path:
        """Get the path to the session history directory."""
        return self.state_dir / SESSION_HISTORY_DIR

    def _generate_session_id(self) -> str:
        """Generate a unique session ID.

        Returns:
            A UUID string (first 8 characters).
        """
        return str(uuid.uuid4())[:8]

    def _check_interrupted_sessions(self) -> None:
        """Check for and mark any interrupted sessions from previous runs."""
        state_file = self.state_file_path
        if not state_file.exists():
            return

        try:
            with open(state_file, encoding="utf-8") as f:
                data = json.load(f)

            status = SessionStatus(data.get("status", "active"))
            if status == SessionStatus.ACTIVE:
                # Previous session was interrupted (crash/shutdown)
                data["status"] = SessionStatus.INTERRUPTED.value
                data["updated_at"] = datetime.now().isoformat()

                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                logger.warning(f"Found interrupted session: {data.get('session_id')}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not check interrupted sessions: {e}")

    def create_session(
        self,
        video_paths: list[Path],
        output_dir: Path | None = None,
        config: OrchestratorConfig | None = None,
    ) -> SessionState:
        """Create a new conversion session.

        Args:
            video_paths: List of video files to convert.
            output_dir: Directory for output files.
            config: Orchestrator configuration to snapshot.

        Returns:
            A new SessionState instance.

        Raises:
            SessionStateError: If a session is already active.
        """
        with self._lock:
            if self._current_session and self._current_session.status == SessionStatus.ACTIVE:
                raise SessionStateError(
                    f"Session {self._current_session.session_id} is already active. "
                    "Complete or cancel it before starting a new session."
                )

            session_id = self._generate_session_id()

            # Create video entries
            pending_videos = []
            for path in video_paths:
                output_path = self._create_output_path(path, output_dir, config)
                pending_videos.append(
                    VideoEntry(
                        path=path,
                        output_path=output_path,
                        status=ConversionStatus.PENDING,
                    )
                )

            # Snapshot config
            config_snapshot = {}
            if config:
                config_snapshot = {
                    "mode": config.mode.value,
                    "quality": config.quality,
                    "crf": config.crf,
                    "preset": config.preset,
                    "output_suffix": config.output_suffix,
                    "preserve_metadata": config.preserve_metadata,
                    "validate_output": config.validate_output,
                }

            self._current_session = SessionState(
                session_id=session_id,
                status=SessionStatus.ACTIVE,
                started_at=datetime.now(),
                updated_at=datetime.now(),
                current_index=0,
                pending_videos=pending_videos,
                output_dir=output_dir,
                config_snapshot=config_snapshot,
            )

            self._dirty = True
            self.save()

            logger.info(f"Created session {session_id} with {len(pending_videos)} videos")
            return self._current_session

    def _create_output_path(
        self,
        input_path: Path,
        output_dir: Path | None,
        config: OrchestratorConfig | None,
    ) -> Path:
        """Create output path for a video file.

        Args:
            input_path: Path to the input video.
            output_dir: Output directory (or None to use input directory).
            config: Configuration with output suffix.

        Returns:
            Path for the output file.
        """
        if output_dir is None:
            output_dir = input_path.parent

        suffix = "_h265"
        if config and config.output_suffix:
            suffix = config.output_suffix

        stem = input_path.stem
        if not stem.endswith(suffix):
            stem = f"{stem}{suffix}"

        return output_dir / f"{stem}.mp4"

    def save(self, force: bool = False) -> None:
        """Save current session state to disk.

        Args:
            force: If True, save even if not dirty or interval not reached.
        """
        with self._lock:
            if self._current_session is None:
                return

            # Check if we should save based on interval
            if not force and not self._dirty:
                return

            now = datetime.now()
            if not force and self._last_save_time is not None and self._auto_save_interval > 0:
                elapsed = (now - self._last_save_time).total_seconds()
                if elapsed < self._auto_save_interval:
                    return

            try:
                state_file = self.state_file_path
                self._current_session.updated_at = now

                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(self._current_session.to_dict(), f, indent=2)

                self._last_save_time = now
                self._dirty = False
                logger.debug(f"Saved session state to {state_file}")
            except OSError as e:
                logger.error(f"Failed to save session state: {e}")

    def load_session(self, session_id: str | None = None) -> SessionState:
        """Load a session from disk.

        Args:
            session_id: Specific session ID to load, or None for current.

        Returns:
            The loaded SessionState.

        Raises:
            SessionNotFoundError: If the session does not exist.
            SessionCorruptedError: If the session data is corrupted.
        """
        with self._lock:
            if session_id:
                state_file = self.history_dir / f"{session_id}.json"
            else:
                state_file = self.state_file_path

            if not state_file.exists():
                raise SessionNotFoundError(f"Session file not found: {state_file}")

            try:
                with open(state_file, encoding="utf-8") as f:
                    data = json.load(f)

                session = SessionState.from_dict(data)
                self._current_session = session
                self._dirty = False
                logger.info(f"Loaded session {session.session_id}")
                return session
            except json.JSONDecodeError as e:
                raise SessionCorruptedError(f"Invalid session data: {e}") from e
            except KeyError as e:
                raise SessionCorruptedError(f"Missing session field: {e}") from e

    def has_resumable_session(self) -> bool:
        """Check if there is a resumable session available.

        Returns:
            True if a session can be resumed, False otherwise.
        """
        state_file = self.state_file_path
        if not state_file.exists():
            return False

        try:
            with open(state_file, encoding="utf-8") as f:
                data = json.load(f)

            status = SessionStatus(data.get("status", "active"))
            return status in (SessionStatus.PAUSED, SessionStatus.INTERRUPTED)
        except (json.JSONDecodeError, ValueError):
            return False

    def get_resumable_sessions(self) -> list[dict]:
        """Get list of all resumable sessions.

        Returns:
            List of session info dictionaries with id, status, and progress.
        """
        sessions = []

        # Check current session
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, encoding="utf-8") as f:
                    data = json.load(f)

                status = SessionStatus(data.get("status", "active"))
                if status in (SessionStatus.PAUSED, SessionStatus.INTERRUPTED):
                    total = (
                        len(data.get("pending_videos", []))
                        + len(data.get("completed_videos", []))
                        + len(data.get("failed_videos", []))
                    )
                    completed = len(data.get("completed_videos", []))
                    sessions.append(
                        {
                            "session_id": data.get("session_id"),
                            "status": status.value,
                            "started_at": data.get("started_at"),
                            "total_videos": total,
                            "completed_videos": completed,
                            "progress": completed / total if total > 0 else 0.0,
                        }
                    )
            except (json.JSONDecodeError, ValueError):
                pass

        # Check history directory
        if self.history_dir.exists():
            for session_file in self.history_dir.glob("*.json"):
                try:
                    with open(session_file, encoding="utf-8") as f:
                        data = json.load(f)

                    status = SessionStatus(data.get("status", "active"))
                    if status in (SessionStatus.PAUSED, SessionStatus.INTERRUPTED):
                        total = (
                            len(data.get("pending_videos", []))
                            + len(data.get("completed_videos", []))
                            + len(data.get("failed_videos", []))
                        )
                        completed = len(data.get("completed_videos", []))
                        sessions.append(
                            {
                                "session_id": data.get("session_id"),
                                "status": status.value,
                                "started_at": data.get("started_at"),
                                "total_videos": total,
                                "completed_videos": completed,
                                "progress": completed / total if total > 0 else 0.0,
                            }
                        )
                except (json.JSONDecodeError, ValueError):
                    continue

        return sessions

    def mark_video_completed(
        self,
        video: VideoEntry,
        original_size: int = 0,
        converted_size: int = 0,
    ) -> None:
        """Mark a video as successfully completed.

        Args:
            video: The video entry to mark complete.
            original_size: Size of original file in bytes.
            converted_size: Size of converted file in bytes.
        """
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.mark_video_completed(video, original_size, converted_size)
            self._current_session.current_index += 1
            self._dirty = True
            self.save()

    def mark_video_failed(self, video: VideoEntry, error: str) -> None:
        """Mark a video as failed.

        Args:
            video: The video entry to mark failed.
            error: Error message describing the failure.
        """
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.mark_video_failed(video, error)
            self._current_session.current_index += 1
            self._dirty = True
            self.save()

    def add_temporary_file(self, path: Path) -> None:
        """Track a temporary file.

        Args:
            path: Path to the temporary file.
        """
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.add_temporary_file(path)
            self._dirty = True

    def remove_temporary_file(self, path: Path) -> None:
        """Stop tracking a temporary file.

        Args:
            path: Path to the temporary file.
        """
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.remove_temporary_file(path)
            self._dirty = True

    def pause_session(self) -> bool:
        """Pause the current session.

        Returns:
            True if paused successfully, False if no active session.
        """
        with self._lock:
            if self._current_session is None:
                return False
            if self._current_session.status != SessionStatus.ACTIVE:
                return False

            self._current_session.status = SessionStatus.PAUSED
            self._current_session.updated_at = datetime.now()
            self._dirty = True
            self.save(force=True)

            logger.info(f"Paused session {self._current_session.session_id}")
            return True

    def resume_session(self) -> SessionState | None:
        """Resume a paused or interrupted session.

        Returns:
            The resumed SessionState, or None if no resumable session.
        """
        with self._lock:
            if self._current_session is None:
                try:
                    self.load_session()
                except SessionNotFoundError:
                    return None

            if self._current_session is None:
                return None

            if not self._current_session.is_resumable:
                return None

            self._current_session.status = SessionStatus.ACTIVE
            self._current_session.updated_at = datetime.now()
            self._dirty = True
            self.save(force=True)

            logger.info(f"Resumed session {self._current_session.session_id}")
            return self._current_session

    def complete_session(self) -> None:
        """Mark the current session as completed and archive it."""
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.status = SessionStatus.COMPLETED
            self._current_session.updated_at = datetime.now()

            # Archive to history
            self._archive_session()

            # Remove current session file
            if self.state_file_path.exists():
                self.state_file_path.unlink()

            logger.info(f"Completed session {self._current_session.session_id}")
            self._current_session = None
            self._dirty = False

    def cancel_session(self) -> None:
        """Cancel the current session and archive it."""
        with self._lock:
            if self._current_session is None:
                return

            self._current_session.status = SessionStatus.CANCELLED
            self._current_session.updated_at = datetime.now()

            # Clean up temporary files
            self._cleanup_temporary_files()

            # Archive to history
            self._archive_session()

            # Remove current session file
            if self.state_file_path.exists():
                self.state_file_path.unlink()

            logger.info(f"Cancelled session {self._current_session.session_id}")
            self._current_session = None
            self._dirty = False

    def _archive_session(self) -> None:
        """Archive the current session to history directory."""
        if self._current_session is None:
            return

        self.history_dir.mkdir(parents=True, exist_ok=True)
        archive_file = self.history_dir / f"{self._current_session.session_id}.json"

        try:
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(self._current_session.to_dict(), f, indent=2)
            logger.debug(f"Archived session to {archive_file}")
        except OSError as e:
            logger.error(f"Failed to archive session: {e}")

    def cleanup_orphaned_temp_files(self) -> list[Path]:
        """Clean up orphaned temporary files from interrupted sessions.

        Returns:
            List of files that were cleaned up.
        """
        cleaned = []

        with self._lock:
            if self._current_session is None:
                try:
                    self.load_session()
                except SessionNotFoundError:
                    return cleaned

            if self._current_session is None:
                return cleaned

            cleaned = self._cleanup_temporary_files()

        return cleaned

    def _cleanup_temporary_files(self) -> list[Path]:
        """Clean up temporary files for current session.

        Returns:
            List of files that were cleaned up.
        """
        if self._current_session is None:
            return []

        cleaned = []
        for temp_file in list(self._current_session.temporary_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    cleaned.append(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                self._current_session.temporary_files.remove(temp_file)
            except OSError as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")

        if cleaned:
            self._dirty = True

        return cleaned

    def get_session_status(self) -> dict | None:
        """Get status summary for the current session.

        Returns:
            Dictionary with session status info, or None if no session.
        """
        with self._lock:
            if self._current_session is None:
                return None

            return {
                "session_id": self._current_session.session_id,
                "status": self._current_session.status.value,
                "started_at": self._current_session.started_at.isoformat(),
                "updated_at": self._current_session.updated_at.isoformat(),
                "current_index": self._current_session.current_index,
                "total_videos": self._current_session.total_videos,
                "pending": len(self._current_session.pending_videos),
                "completed": len(self._current_session.completed_videos),
                "failed": len(self._current_session.failed_videos),
                "progress": self._current_session.progress,
                "temporary_files": len(self._current_session.temporary_files),
            }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from history.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            # Check history
            session_file = self.history_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Deleted session {session_id}")
                return True

            # Check current
            if self.state_file_path.exists():
                try:
                    with open(self.state_file_path, encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("session_id") == session_id:
                        self.state_file_path.unlink()
                        if self._current_session and self._current_session.session_id == session_id:
                            self._current_session = None
                        logger.info(f"Deleted current session {session_id}")
                        return True
                except (json.JSONDecodeError, OSError):
                    pass

            return False

    def clear_history(self, keep_days: int = 30) -> int:
        """Clear old sessions from history.

        Args:
            keep_days: Number of days of history to keep.

        Returns:
            Number of sessions deleted.
        """
        deleted = 0
        cutoff = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)

        if not self.history_dir.exists():
            return 0

        for session_file in self.history_dir.glob("*.json"):
            try:
                if session_file.stat().st_mtime < cutoff:
                    session_file.unlink()
                    deleted += 1
            except OSError:
                continue

        if deleted > 0:
            logger.info(f"Cleared {deleted} old sessions from history")

        return deleted


# Module-level convenience functions
_default_manager: SessionStateManager | None = None
_manager_lock = threading.Lock()


def get_session_manager(state_dir: Path | None = None) -> SessionStateManager:
    """Get or create the default session state manager.

    Args:
        state_dir: Optional state directory. Only used on first call.

    Returns:
        The default SessionStateManager instance.
    """
    global _default_manager
    with _manager_lock:
        if _default_manager is None:
            _default_manager = SessionStateManager(state_dir=state_dir)
        return _default_manager
