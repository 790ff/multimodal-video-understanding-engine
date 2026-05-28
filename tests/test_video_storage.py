from pathlib import Path

import pytest

from app.config import Settings
from app.domain.errors import ValidationAppError
from app.services.video_storage import VideoStorageService


def test_validate_extension_accepts_mvp_formats(tmp_path: Path) -> None:
    settings = Settings(upload_dir=tmp_path / "uploads")
    service = VideoStorageService(settings)

    assert service.validate_extension("demo.mp4") == "mp4"
    assert service.validate_extension("demo.MOV") == "mov"


def test_validate_extension_rejects_unsupported_formats(tmp_path: Path) -> None:
    settings = Settings(upload_dir=tmp_path / "uploads")
    service = VideoStorageService(settings)

    with pytest.raises(ValidationAppError) as exc_info:
        service.validate_extension("demo.avi")

    assert exc_info.value.code == "unsupported_video_type"


def test_build_upload_path_uses_video_id_directory(tmp_path: Path) -> None:
    settings = Settings(upload_dir=tmp_path / "uploads")
    service = VideoStorageService(settings)

    upload_path = service.build_upload_path(video_id="video-123", original_filename="demo.mp4")

    assert upload_path == tmp_path / "uploads" / "video-123" / "original.mp4"
