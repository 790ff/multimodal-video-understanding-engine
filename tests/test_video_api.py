from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test_video_ai.sqlite3'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUDIO_DIR", str(tmp_path / "audio"))
    monkeypatch.setenv("FRAME_DIR", str(tmp_path / "frames"))
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

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
