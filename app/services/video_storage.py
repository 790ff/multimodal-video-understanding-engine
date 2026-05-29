from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.db.models import VideoModel
from app.domain.errors import FileTooLargeAppError, StorageAppError, ValidationAppError
from app.repositories.video_repository import VideoRepository


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

    async def store_upload(
        self,
        *,
        file: UploadFile,
        repository: VideoRepository,
    ) -> VideoModel:
        if not file.filename:
            raise ValidationAppError(
                "Uploaded file must include a filename.",
                code="missing_filename",
            )

        video_id, upload_path = self.prepare_upload_target(file.filename)
        try:
            await self.write_upload_file(file, upload_path)
            return repository.create(
                video_id=video_id,
                original_filename=file.filename,
                stored_path=str(upload_path),
            )
        except (FileTooLargeAppError, ValidationAppError):
            self.cleanup_upload_dir(upload_path.parent)
            raise
        except OSError as exc:
            self.cleanup_upload_dir(upload_path.parent)
            raise StorageAppError(
                "Could not store uploaded video.",
                code="video_storage_failed",
            ) from exc
        except SQLAlchemyError as exc:
            self.cleanup_upload_dir(upload_path.parent)
            raise StorageAppError(
                "Could not save uploaded video metadata.",
                code="metadata_storage_failed",
            ) from exc

    def prepare_upload_target(self, original_filename: str) -> tuple[str, Path]:
        self.validate_extension(original_filename)
        for _ in range(10):
            video_id = str(uuid4())
            upload_path = self.build_upload_path(
                video_id=video_id,
                original_filename=original_filename,
            )
            if not upload_path.parent.exists():
                return video_id, upload_path

        raise StorageAppError(
            "Could not allocate upload storage.",
            code="upload_storage_unavailable",
        )

    async def write_upload_file(self, file: UploadFile, upload_path: Path) -> None:
        upload_path.parent.mkdir(parents=True, exist_ok=False)
        temp_path = upload_path.with_name(f"{upload_path.name}.tmp")
        bytes_written = 0

        try:
            with temp_path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > self.settings.max_upload_bytes:
                        raise FileTooLargeAppError(
                            "Uploaded file exceeds the configured size limit.",
                            code="upload_too_large",
                            details={"max_upload_mb": self.settings.max_upload_mb},
                        )
                    output.write(chunk)
            temp_path.replace(upload_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            upload_path.unlink(missing_ok=True)
            raise

    def cleanup_upload_dir(self, upload_dir: Path) -> None:
        shutil.rmtree(upload_dir, ignore_errors=True)
