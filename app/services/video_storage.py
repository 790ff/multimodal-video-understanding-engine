from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.db.models import VideoModel
from app.domain.errors import FileTooLargeAppError, StorageAppError, ValidationAppError
from app.repositories.video_repository import VideoRepository
from app.services.storage_lifecycle import RuntimeStorageLifecycle
from app.services.storage_paths import controlled_child_path

ALLOWED_CONTENT_TYPES_BY_EXTENSION = {
    "mp4": {"application/mp4", "application/octet-stream", "video/mp4"},
    "mov": {
        "application/octet-stream",
        "video/mov",
        "video/quicktime",
        "video/x-quicktime",
    },
}


class VideoStorageService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        storage_lifecycle: Optional[RuntimeStorageLifecycle] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage_lifecycle = storage_lifecycle or RuntimeStorageLifecycle(self.settings)

    def validate_filename(self, filename: str) -> None:
        if not filename or filename != filename.strip():
            raise ValidationAppError(
                "Uploaded filename is invalid.",
                code="invalid_filename",
            )
        if (
            filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or any(ord(character) < 32 or ord(character) == 127 for character in filename)
            or len(filename.encode("utf-8")) > 255
        ):
            raise ValidationAppError(
                "Uploaded filename is invalid.",
                code="invalid_filename",
            )

    def validate_extension(self, filename: str) -> str:
        self.validate_filename(filename)
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

    def validate_content_type(self, *, extension: str, content_type: Optional[str]) -> None:
        normalized_content_type = (content_type or "").split(";", maxsplit=1)[0].strip().lower()
        if not normalized_content_type:
            return

        allowed_content_types = ALLOWED_CONTENT_TYPES_BY_EXTENSION.get(
            extension,
            {f"video/{extension}", "application/octet-stream"},
        )
        if normalized_content_type not in allowed_content_types:
            raise ValidationAppError(
                "Uploaded media content type is not supported.",
                code="unsupported_media_content_type",
                details={
                    "content_type": normalized_content_type,
                    "allowed_content_types": sorted(allowed_content_types),
                },
            )

    def validate_upload_metadata(self, *, filename: str, content_type: Optional[str]) -> str:
        extension = self.validate_extension(filename)
        self.validate_content_type(extension=extension, content_type=content_type)
        return extension

    def build_upload_path(self, *, video_id: str, original_filename: str) -> Path:
        extension = self.validate_extension(original_filename)
        return controlled_child_path(
            self.settings.upload_dir,
            video_id,
            f"original.{extension}",
            code="unsafe_upload_path",
        )

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

        video_id, upload_path = self.prepare_upload_target(
            filename=file.filename,
            content_type=file.content_type,
        )
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

    def prepare_upload_target(
        self,
        *,
        filename: str,
        content_type: Optional[str],
    ) -> tuple[str, Path]:
        self.validate_upload_metadata(filename=filename, content_type=content_type)
        for _ in range(10):
            video_id = str(uuid4())
            upload_path = self.build_upload_path(
                video_id=video_id,
                original_filename=filename,
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
        self.storage_lifecycle.remove_runtime_path(
            upload_dir,
            root=self.settings.upload_dir,
            code="unsafe_upload_path",
        )
