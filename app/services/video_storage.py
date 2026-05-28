from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config import Settings, get_settings
from app.domain.errors import ValidationAppError


class VideoStorageService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def validate_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower().lstrip(".")
        if not extension:
            raise ValidationAppError(
                "Uploaded file must include a file extension.",
                code="missing_file_extension",
            )
        if extension not in self.settings.allowed_extensions:
            raise ValidationAppError(
                "Unsupported video file type.",
                code="unsupported_video_type",
                details={
                    "extension": extension,
                    "allowed_extensions": sorted(self.settings.allowed_extensions),
                },
            )
        return extension

    def build_upload_path(self, *, video_id: str, original_filename: str) -> Path:
        extension = self.validate_extension(original_filename)
        return self.settings.upload_dir / video_id / f"original.{extension}"
