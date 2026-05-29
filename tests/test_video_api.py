from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.audio_extractor import AudioExtractionResult
from app.adapters.frame_extractor import ExtractedFrame
from app.adapters.scene_detector import DetectedScene
from app.api.videos import get_video_processor
from app.config import get_settings
from app.main import create_app
from app.services.video_processor import VideoProcessor


class FakeAudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        assert video_path.exists()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake wav bytes")
        return AudioExtractionResult(audio_path=output_path)


class FakeFrameExtractor:
    def __init__(self) -> None:
        self.sample_seconds: int | None = None

    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        sample_seconds: int,
    ) -> list[ExtractedFrame]:
        assert video_path.exists()
        self.sample_seconds = sample_seconds
        output_dir.mkdir(parents=True, exist_ok=True)

        frames = []
        for sequence, timestamp in enumerate((0.0, 3.0), start=1):
            frame_path = output_dir / f"frame_{sequence:06d}.jpg"
            frame_path.write_bytes(b"fake jpg bytes")
            frames.append(ExtractedFrame(time=timestamp, path=frame_path))
        return frames


class FakeSceneDetector:
    def detect(self, video_path: Path) -> list[DetectedScene]:
        assert video_path.exists()
        return [
            DetectedScene(start_time=0.0, end_time=2.5),
            DetectedScene(start_time=2.5, end_time=5.0),
        ]


class FailingAudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        raise RuntimeError("secret path /tmp/.env OPENAI_API_KEY=abc123")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test_video_ai.sqlite3'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUDIO_DIR", str(tmp_path / "audio"))
    monkeypatch.setenv("FRAME_DIR", str(tmp_path / "frames"))
    monkeypatch.setenv("FRAME_SAMPLE_SECONDS", "3")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    test_client.app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_upload_video_creates_metadata_and_stores_original_file(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "demo.mp4"
    assert body["status"] == "uploaded"
    assert body["video_id"]

    stored_file = tmp_path / "uploads" / body["video_id"] / "original.mp4"
    assert stored_file.read_bytes() == b"fake mp4 bytes"

    db_path = tmp_path / "test_video_ai.sqlite3"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select id, original_filename, stored_path, status, error_message from videos"
        ).fetchone()

    assert row == (
        body["video_id"],
        "demo.mp4",
        str(stored_file),
        "uploaded",
        None,
    )


def test_upload_video_accepts_mov(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("clip.MOV", b"fake mov bytes", "video/quicktime")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "clip.MOV"
    assert body["status"] == "uploaded"
    assert (tmp_path / "uploads" / body["video_id"] / "original.mov").exists()


def test_upload_video_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("demo.avi", b"fake avi bytes", "video/x-msvideo")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "unsupported_video_type",
            "message": "Unsupported video file type.",
            "details": {
                "extension": "avi",
                "allowed_extensions": ["mov", "mp4"],
            },
        }
    }


def test_get_video_status_returns_current_status(client: TestClient) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.get(f"/videos/{video_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "status": "uploaded",
        "error_message": None,
    }


def test_get_video_status_returns_404_for_missing_video(client: TestClient) -> None:
    response = client.get("/videos/00000000-0000-0000-0000-000000000000/status")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_analyze_video_runs_preprocessing_and_persists_metadata(
    client: TestClient,
    tmp_path: Path,
) -> None:
    frame_extractor = FakeFrameExtractor()
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=frame_extractor,
        scene_detector=FakeSceneDetector(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "status": "analyzed",
        "transcript_segments": 0,
        "keyframes": 2,
        "scenes": 2,
        "timeline_events": 0,
    }
    assert frame_extractor.sample_seconds == 3
    audio_path = tmp_path / "audio" / video_id / "audio.wav"
    assert audio_path.read_bytes() == b"fake wav bytes"
    assert (tmp_path / "frames" / video_id / "frame_000001.jpg").exists()
    assert (tmp_path / "frames" / video_id / "frame_000002.jpg").exists()

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        video_row = connection.execute(
            "select status, error_message from videos where id = ?",
            (video_id,),
        ).fetchone()
        keyframe_rows = connection.execute(
            "select time, path from keyframes where video_id = ? order by time",
            (video_id,),
        ).fetchall()
        scene_rows = connection.execute(
            "select start_time, end_time from scenes where video_id = ? order by start_time",
            (video_id,),
        ).fetchall()

    assert video_row == ("analyzed", None)
    assert keyframe_rows == [
        (0.0, str(tmp_path / "frames" / video_id / "frame_000001.jpg")),
        (3.0, str(tmp_path / "frames" / video_id / "frame_000002.jpg")),
    ]
    assert scene_rows == [(0.0, 2.5), (2.5, 5.0)]


def test_analyze_video_returns_404_for_missing_video(client: TestClient) -> None:
    response = client.post("/videos/00000000-0000-0000-0000-000000000000/analyze")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_analyze_video_returns_409_when_already_processing(
    client: TestClient,
    tmp_path: Path,
) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        connection.execute(
            "update videos set status = 'processing' where id = ?",
            (video_id,),
        )

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "video_already_processing",
            "message": "Video is already processing.",
            "details": {},
        }
    }


def test_analyze_video_failure_marks_video_failed_with_safe_message(
    client: TestClient,
) -> None:
    processor = VideoProcessor(
        audio_extractor=FailingAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "video_preprocessing_failed",
            "message": "Video preprocessing failed.",
            "details": {},
        }
    }

    status_response = client.get(f"/videos/{video_id}/status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "video_id": video_id,
        "status": "failed",
        "error_message": "Video preprocessing failed.",
    }
