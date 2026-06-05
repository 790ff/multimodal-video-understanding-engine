from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import Base
from app.db import models as _models  # noqa: F401
from app.db.models import KeyframeModel, TimelineEventModel, TranscriptSegmentModel
from app.domain.errors import StorageAppError
from app.domain.timeline import EvidenceLinkData, TimelineEventData
from app.repositories.video_repository import VideoRepository
from app.services.storage_lifecycle import RUNTIME_KEEP_FILE, RuntimeStorageLifecycle


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'metadata.sqlite3'}",
        upload_dir=tmp_path / "uploads",
        audio_dir=tmp_path / "audio",
        frame_dir=tmp_path / "frames",
    )


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.sqlite3'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with session_factory() as session:
        yield session


def test_reset_runtime_dirs_preserves_gitkeep_and_stays_inside_roots(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("must stay", encoding="utf-8")

    for root in (settings.upload_dir, settings.audio_dir, settings.frame_dir):
        root.mkdir(parents=True)
        (root / RUNTIME_KEEP_FILE).write_text("", encoding="utf-8")
        (root / "video-known").mkdir()
        (root / "video-known" / "artifact.bin").write_bytes(b"artifact")
        (root / "loose.tmp").write_text("orphan", encoding="utf-8")

    report = RuntimeStorageLifecycle(settings).reset_runtime_dirs()

    assert outside_file.read_text(encoding="utf-8") == "must stay"
    for root in (settings.upload_dir, settings.audio_dir, settings.frame_dir):
        assert root.is_dir()
        assert [child.name for child in root.iterdir()] == [RUNTIME_KEEP_FILE]
    assert all(not path.exists() for path in report.removed_paths)


def test_cleanup_orphan_runtime_files_keeps_known_video_dirs(
    tmp_path: Path,
    db_session: Session,
) -> None:
    settings = make_settings(tmp_path)
    repository = VideoRepository(db_session)
    known_video_id = "known-video"
    known_upload = settings.upload_dir / known_video_id / "original.mp4"
    known_upload.parent.mkdir(parents=True)
    known_upload.write_bytes(b"video")
    repository.create(
        video_id=known_video_id,
        original_filename="sample.mp4",
        stored_path=str(known_upload),
    )
    db_session.commit()

    for root in (settings.upload_dir, settings.audio_dir, settings.frame_dir):
        root.mkdir(parents=True, exist_ok=True)
        (root / RUNTIME_KEEP_FILE).write_text("", encoding="utf-8")
        (root / known_video_id).mkdir(exist_ok=True)
        (root / known_video_id / "kept.bin").write_bytes(b"kept")
        (root / "orphan-video").mkdir()
        (root / "orphan-video" / "removed.bin").write_bytes(b"removed")

    report = RuntimeStorageLifecycle(settings).cleanup_orphan_runtime_files(
        repository=repository,
    )

    for root in (settings.upload_dir, settings.audio_dir, settings.frame_dir):
        assert (root / RUNTIME_KEEP_FILE).exists()
        assert (root / known_video_id / "kept.bin").exists()
        assert not (root / "orphan-video").exists()
    assert {path.name for path in report.removed_paths} == {"orphan-video"}


def test_runtime_path_removal_rejects_paths_outside_configured_root(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.upload_dir.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("must stay", encoding="utf-8")

    with pytest.raises(StorageAppError) as exc_info:
        RuntimeStorageLifecycle(settings).remove_runtime_path(
            outside_file,
            root=settings.upload_dir,
        )

    assert exc_info.value.code == "unsafe_storage_path"
    assert outside_file.read_text(encoding="utf-8") == "must stay"


def test_reset_local_data_clears_repository_metadata_and_runtime_files(
    tmp_path: Path,
    db_session: Session,
) -> None:
    settings = make_settings(tmp_path)
    repository = VideoRepository(db_session)
    video_id = "video-with-analysis"
    upload_path = settings.upload_dir / video_id / "original.mp4"
    frame_path = settings.frame_dir / video_id / "frame_000001.jpg"
    upload_path.parent.mkdir(parents=True)
    frame_path.parent.mkdir(parents=True)
    upload_path.write_bytes(b"video")
    frame_path.write_bytes(b"frame")

    video = repository.create(
        video_id=video_id,
        original_filename="sample.mp4",
        stored_path=str(upload_path),
    )
    transcript = repository.replace_transcript_segments(video, [(0.0, 1.0, "hello")])[0]
    keyframe = repository.replace_keyframes(video, [(0.0, str(frame_path), "visible")])[0]
    repository.replace_timeline_events(
        video,
        [
            TimelineEventData(
                start_time=0.0,
                end_time=1.0,
                summary="stored event",
                evidence=(
                    EvidenceLinkData("transcript", transcript.id),
                    EvidenceLinkData("frame", keyframe.id),
                ),
            )
        ],
    )
    db_session.commit()

    RuntimeStorageLifecycle(settings).reset_local_data(repository=repository)
    db_session.commit()

    assert repository.list_video_ids() == []
    assert db_session.scalar(select(TranscriptSegmentModel).limit(1)) is None
    assert db_session.scalar(select(KeyframeModel).limit(1)) is None
    assert db_session.scalar(select(TimelineEventModel).limit(1)) is None
    for root in (settings.upload_dir, settings.audio_dir, settings.frame_dir):
        assert [child.name for child in root.iterdir()] == [RUNTIME_KEEP_FILE]
