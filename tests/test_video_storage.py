from pathlib import Path

import pytest

from app.config import Settings
from app.domain.errors import StorageAppError, ValidationAppError
from app.services.video_storage import VideoStorageService


def make_settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, upload_dir=tmp_path / "uploads")


def test_validate_extension_accepts_mvp_formats(tmp_path: Path) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    assert service.validate_extension("sample.mp4") == "mp4"
    assert service.validate_extension("sample.MOV") == "mov"


def test_validate_extension_rejects_unsupported_formats(tmp_path: Path) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    with pytest.raises(ValidationAppError) as exc_info:
        service.validate_extension("sample.avi")

    assert exc_info.value.code == "unsupported_video_type"


@pytest.mark.parametrize(
    "filename",
    [
        "../sample.mp4",
        "..\\sample.mp4",
        " sample.mp4",
        "sample.mp4 ",
        "sample\x00.mp4",
    ],
)
def test_validate_filename_rejects_unsafe_names(tmp_path: Path, filename: str) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    with pytest.raises(ValidationAppError) as exc_info:
        service.validate_extension(filename)

    assert exc_info.value.code == "invalid_filename"


def test_validate_content_type_rejects_mismatched_media_type(tmp_path: Path) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    with pytest.raises(ValidationAppError) as exc_info:
        service.validate_upload_metadata(filename="sample.mp4", content_type="text/plain")

    assert exc_info.value.code == "unsupported_media_content_type"


def test_build_upload_path_uses_video_id_directory(tmp_path: Path) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    upload_path = service.build_upload_path(video_id="video-123", original_filename="sample.mp4")

    assert upload_path == tmp_path / "uploads" / "video-123" / "original.mp4"


def test_build_upload_path_rejects_unsafe_video_id_segment(tmp_path: Path) -> None:
    service = VideoStorageService(make_settings(tmp_path))

    with pytest.raises(StorageAppError) as exc_info:
        service.build_upload_path(video_id="../outside", original_filename="sample.mp4")

    assert exc_info.value.code == "unsafe_upload_path"
