"""Unit tests for session state management module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from video_converter.core.session import (
    SessionCorruptedError,
    SessionNotFoundError,
    SessionStateError,
    SessionStateManager,
)
from video_converter.core.types import (
    ConversionStatus,
    SessionState,
    SessionStatus,
    VideoEntry,
)


class TestVideoEntry:
    """Tests for VideoEntry dataclass."""

    def test_default_values(self) -> None:
        """Test default field values."""
        entry = VideoEntry(
            path=Path("/videos/test.mov"),
            output_path=Path("/videos/test_h265.mp4"),
        )
        assert entry.status == ConversionStatus.PENDING
        assert entry.error_message is None
        assert entry.original_size == 0
        assert entry.converted_size == 0

    def test_string_path_normalization(self) -> None:
        """Test string paths are converted to Path objects."""
        entry = VideoEntry(
            path="/videos/test.mov",  # type: ignore
            output_path="/videos/test_h265.mp4",  # type: ignore
        )
        assert isinstance(entry.path, Path)
        assert isinstance(entry.output_path, Path)

    def test_string_status_normalization(self) -> None:
        """Test string status is converted to enum."""
        entry = VideoEntry(
            path=Path("/videos/test.mov"),
            output_path=Path("/videos/test_h265.mp4"),
            status="completed",  # type: ignore
        )
        assert entry.status == ConversionStatus.COMPLETED

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        entry = VideoEntry(
            path=Path("/videos/test.mov"),
            output_path=Path("/videos/test_h265.mp4"),
            status=ConversionStatus.COMPLETED,
            original_size=1000,
            converted_size=500,
        )
        data = entry.to_dict()

        assert data["path"] == "/videos/test.mov"
        assert data["output_path"] == "/videos/test_h265.mp4"
        assert data["status"] == "completed"
        assert data["original_size"] == 1000
        assert data["converted_size"] == 500

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "path": "/videos/test.mov",
            "output_path": "/videos/test_h265.mp4",
            "status": "failed",
            "error_message": "Test error",
            "original_size": 1000,
            "converted_size": 0,
        }
        entry = VideoEntry.from_dict(data)

        assert entry.path == Path("/videos/test.mov")
        assert entry.status == ConversionStatus.FAILED
        assert entry.error_message == "Test error"


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_values(self) -> None:
        """Test default field values."""
        session = SessionState(session_id="test123")

        assert session.status == SessionStatus.ACTIVE
        assert session.current_index == 0
        assert session.pending_videos == []
        assert session.completed_videos == []
        assert session.failed_videos == []
        assert session.temporary_files == []
        assert session.output_dir is None
        assert session.config_snapshot == {}

    def test_total_videos(self) -> None:
        """Test total_videos property."""
        session = SessionState(
            session_id="test123",
            pending_videos=[
                VideoEntry(Path("a.mov"), Path("a.mp4")),
                VideoEntry(Path("b.mov"), Path("b.mp4")),
            ],
            completed_videos=[
                VideoEntry(Path("c.mov"), Path("c.mp4")),
            ],
            failed_videos=[
                VideoEntry(Path("d.mov"), Path("d.mp4")),
            ],
        )
        assert session.total_videos == 4

    def test_progress(self) -> None:
        """Test progress property calculation."""
        session = SessionState(
            session_id="test123",
            pending_videos=[VideoEntry(Path("a.mov"), Path("a.mp4"))],
            completed_videos=[
                VideoEntry(Path("b.mov"), Path("b.mp4")),
                VideoEntry(Path("c.mov"), Path("c.mp4")),
            ],
            failed_videos=[VideoEntry(Path("d.mov"), Path("d.mp4"))],
        )
        # 3 of 4 processed = 0.75
        assert session.progress == 0.75

    def test_progress_empty(self) -> None:
        """Test progress returns 0 for empty session."""
        session = SessionState(session_id="test123")
        assert session.progress == 0.0

    def test_is_resumable_paused(self) -> None:
        """Test is_resumable for paused session."""
        session = SessionState(
            session_id="test123",
            status=SessionStatus.PAUSED,
        )
        assert session.is_resumable is True

    def test_is_resumable_interrupted(self) -> None:
        """Test is_resumable for interrupted session."""
        session = SessionState(
            session_id="test123",
            status=SessionStatus.INTERRUPTED,
        )
        assert session.is_resumable is True

    def test_is_resumable_completed(self) -> None:
        """Test is_resumable for completed session."""
        session = SessionState(
            session_id="test123",
            status=SessionStatus.COMPLETED,
        )
        assert session.is_resumable is False

    def test_mark_video_completed(self) -> None:
        """Test marking a video as completed."""
        video = VideoEntry(Path("test.mov"), Path("test.mp4"))
        session = SessionState(
            session_id="test123",
            pending_videos=[video],
        )

        session.mark_video_completed(video, original_size=1000, converted_size=500)

        assert video not in session.pending_videos
        assert video in session.completed_videos
        assert video.status == ConversionStatus.COMPLETED
        assert video.original_size == 1000
        assert video.converted_size == 500

    def test_mark_video_failed(self) -> None:
        """Test marking a video as failed."""
        video = VideoEntry(Path("test.mov"), Path("test.mp4"))
        session = SessionState(
            session_id="test123",
            pending_videos=[video],
        )

        session.mark_video_failed(video, "Encoder error")

        assert video not in session.pending_videos
        assert video in session.failed_videos
        assert video.status == ConversionStatus.FAILED
        assert video.error_message == "Encoder error"

    def test_add_temporary_file(self) -> None:
        """Test adding temporary file tracking."""
        session = SessionState(session_id="test123")
        temp_file = Path("/tmp/temp.mp4")

        session.add_temporary_file(temp_file)

        assert temp_file in session.temporary_files

    def test_add_temporary_file_no_duplicates(self) -> None:
        """Test no duplicate temporary files."""
        session = SessionState(session_id="test123")
        temp_file = Path("/tmp/temp.mp4")

        session.add_temporary_file(temp_file)
        session.add_temporary_file(temp_file)

        assert len(session.temporary_files) == 1

    def test_remove_temporary_file(self) -> None:
        """Test removing temporary file tracking."""
        temp_file = Path("/tmp/temp.mp4")
        session = SessionState(
            session_id="test123",
            temporary_files=[temp_file],
        )

        session.remove_temporary_file(temp_file)

        assert temp_file not in session.temporary_files

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        session = SessionState(
            session_id="test123",
            status=SessionStatus.PAUSED,
            current_index=2,
            output_dir=Path("/output"),
            config_snapshot={"quality": 80},
        )
        data = session.to_dict()

        assert data["session_id"] == "test123"
        assert data["status"] == "paused"
        assert data["current_index"] == 2
        assert data["output_dir"] == "/output"
        assert data["config_snapshot"] == {"quality": 80}

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "session_id": "test123",
            "status": "interrupted",
            "started_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T11:00:00",
            "current_index": 5,
            "pending_videos": [],
            "completed_videos": [],
            "failed_videos": [],
            "temporary_files": ["/tmp/temp.mp4"],
            "output_dir": "/output",
            "config_snapshot": {},
        }
        session = SessionState.from_dict(data)

        assert session.session_id == "test123"
        assert session.status == SessionStatus.INTERRUPTED
        assert session.current_index == 5
        assert session.output_dir == Path("/output")
        assert Path("/tmp/temp.mp4") in session.temporary_files


class TestSessionStateManager:
    """Tests for SessionStateManager."""

    def test_initialization(self) -> None:
        """Test manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.state_dir == Path(tmpdir)
            assert manager.current_session is None

    def test_state_file_path(self) -> None:
        """Test state file path property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.state_file_path == Path(tmpdir) / "current_session.json"

    def test_history_dir(self) -> None:
        """Test history directory property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.history_dir == Path(tmpdir) / "history"

    def test_create_session(self) -> None:
        """Test creating a new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_paths = [
                Path(tmpdir) / "video1.mov",
                Path(tmpdir) / "video2.mov",
            ]
            # Create dummy files
            for p in video_paths:
                p.touch()

            session = manager.create_session(
                video_paths=video_paths,
                output_dir=Path(tmpdir) / "output",
            )

            assert session.session_id is not None
            assert len(session.session_id) == 8
            assert session.status == SessionStatus.ACTIVE
            assert len(session.pending_videos) == 2
            assert session.output_dir == Path(tmpdir) / "output"

    def test_create_session_while_active_raises(self) -> None:
        """Test creating session while one is active raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])

            with pytest.raises(SessionStateError):
                manager.create_session(video_paths=[video_path])

    def test_save_and_load(self) -> None:
        """Test saving and loading session state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            original = manager.create_session(video_paths=[video_path])
            session_id = original.session_id

            # Create new manager to load from disk
            manager2 = SessionStateManager(state_dir=Path(tmpdir))
            loaded = manager2.load_session()

            assert loaded.session_id == session_id

    def test_load_nonexistent_raises(self) -> None:
        """Test loading nonexistent session raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            with pytest.raises(SessionNotFoundError):
                manager.load_session()

    def test_load_corrupted_raises(self) -> None:
        """Test loading corrupted session raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            # Write invalid JSON
            state_file = manager.state_file_path
            state_file.write_text("not valid json")

            with pytest.raises(SessionCorruptedError):
                manager.load_session()

    def test_has_resumable_session_false(self) -> None:
        """Test has_resumable_session returns False when no session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.has_resumable_session() is False

    def test_has_resumable_session_paused(self) -> None:
        """Test has_resumable_session returns True for paused session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])
            manager.pause_session()

            # New manager checks persisted state
            manager2 = SessionStateManager(state_dir=Path(tmpdir))
            assert manager2.has_resumable_session() is True

    def test_mark_video_completed(self) -> None:
        """Test marking video as completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])
            video = session.pending_videos[0]

            manager.mark_video_completed(video, original_size=1000, converted_size=500)

            assert len(session.pending_videos) == 0
            assert len(session.completed_videos) == 1

    def test_mark_video_failed(self) -> None:
        """Test marking video as failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])
            video = session.pending_videos[0]

            manager.mark_video_failed(video, "Test error")

            assert len(session.pending_videos) == 0
            assert len(session.failed_videos) == 1
            assert session.failed_videos[0].error_message == "Test error"

    def test_pause_session(self) -> None:
        """Test pausing a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])
            result = manager.pause_session()

            assert result is True
            assert manager.current_session.status == SessionStatus.PAUSED

    def test_pause_session_no_session(self) -> None:
        """Test pausing when no session active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.pause_session() is False

    def test_resume_session(self) -> None:
        """Test resuming a paused session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])
            manager.pause_session()

            session = manager.resume_session()

            assert session is not None
            assert session.status == SessionStatus.ACTIVE

    def test_complete_session(self) -> None:
        """Test completing a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])
            session_id = session.session_id

            manager.complete_session()

            assert manager.current_session is None
            assert not manager.state_file_path.exists()
            # Session should be archived
            assert (manager.history_dir / f"{session_id}.json").exists()

    def test_cancel_session(self) -> None:
        """Test cancelling a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])
            session_id = session.session_id

            manager.cancel_session()

            assert manager.current_session is None
            assert not manager.state_file_path.exists()
            # Session should be archived with cancelled status
            archive_file = manager.history_dir / f"{session_id}.json"
            assert archive_file.exists()
            archived_data = json.loads(archive_file.read_text())
            assert archived_data["status"] == "cancelled"

    def test_cleanup_orphaned_temp_files(self) -> None:
        """Test cleaning up orphaned temporary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])

            # Create a temp file and track it
            temp_file = Path(tmpdir) / "temp.mp4"
            temp_file.touch()
            session.add_temporary_file(temp_file)
            manager.save(force=True)

            # Cleanup
            cleaned = manager.cleanup_orphaned_temp_files()

            assert temp_file in cleaned
            assert not temp_file.exists()
            assert len(session.temporary_files) == 0

    def test_get_session_status(self) -> None:
        """Test getting session status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])
            status = manager.get_session_status()

            assert status is not None
            assert "session_id" in status
            assert status["status"] == "active"
            assert status["pending"] == 1
            assert status["completed"] == 0
            assert status["failed"] == 0

    def test_get_session_status_no_session(self) -> None:
        """Test getting status when no session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            assert manager.get_session_status() is None

    def test_get_resumable_sessions(self) -> None:
        """Test getting list of resumable sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            manager.create_session(video_paths=[video_path])
            manager.pause_session()

            sessions = manager.get_resumable_sessions()

            assert len(sessions) == 1
            assert sessions[0]["status"] == "paused"

    def test_delete_session(self) -> None:
        """Test deleting a session from history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))
            video_path = Path(tmpdir) / "video.mov"
            video_path.touch()

            session = manager.create_session(video_paths=[video_path])
            session_id = session.session_id
            manager.complete_session()

            # Verify session is archived
            assert (manager.history_dir / f"{session_id}.json").exists()

            # Delete it
            result = manager.delete_session(session_id)

            assert result is True
            assert not (manager.history_dir / f"{session_id}.json").exists()

    def test_delete_session_not_found(self) -> None:
        """Test deleting nonexistent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionStateManager(state_dir=Path(tmpdir))

            result = manager.delete_session("nonexistent")

            assert result is False

    def test_interrupted_session_detection(self) -> None:
        """Test interrupted session is marked on manager startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a session file with ACTIVE status (simulating crash)
            state_file = Path(tmpdir) / "current_session.json"
            session_data = {
                "session_id": "test123",
                "status": "active",
                "started_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:30:00",
                "current_index": 0,
                "pending_videos": [],
                "completed_videos": [],
                "failed_videos": [],
                "temporary_files": [],
                "output_dir": None,
                "config_snapshot": {},
            }
            state_file.write_text(json.dumps(session_data))

            # Create new manager - should detect interrupted session
            manager = SessionStateManager(state_dir=Path(tmpdir))

            # Load and verify it was marked as interrupted
            session = manager.load_session()
            assert session.status == SessionStatus.INTERRUPTED
