from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.errors import AppError, NotFoundAppError, StorageAppError
from app.domain.status import VideoStatus
from app.repositories.video_repository import VideoRepository
from app.schemas import ErrorResponse, VideoStatusResponse, VideoUploadResponse
from app.services.video_storage import VideoStorageService

router = APIRouter(prefix="/videos", tags=["videos"])


def get_video_storage_service() -> VideoStorageService:
    return VideoStorageService()


UploadVideoFile = Annotated[UploadFile, File(...)]
DatabaseSession = Annotated[Session, Depends(get_db)]
StorageService = Annotated[VideoStorageService, Depends(get_video_storage_service)]


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_video(
    file: UploadVideoFile,
    db: DatabaseSession,
    storage_service: StorageService,
) -> VideoUploadResponse:
    repository = VideoRepository(db)
    video = None
    try:
        video = await storage_service.store_upload(file=file, repository=repository)
        db.commit()
        db.refresh(video)
    except AppError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        if video is not None:
            storage_service.cleanup_upload_dir(Path(video.stored_path).parent)
        raise StorageAppError(
            "Could not save uploaded video metadata.",
            code="metadata_storage_failed",
        ) from exc

    return VideoUploadResponse(
        video_id=video.id,
        filename=video.original_filename,
        status=VideoStatus(video.status),
    )


@router.get(
    "/{video_id}/status",
    response_model=VideoStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_video_status(
    video_id: str,
    db: DatabaseSession,
) -> VideoStatusResponse:
    repository = VideoRepository(db)
    video = repository.get(video_id)
    if video is None:
        raise NotFoundAppError(
            "Video was not found.",
            code="video_not_found",
        )

    return VideoStatusResponse(
        video_id=video.id,
        status=VideoStatus(video.status),
        error_message=video.error_message,
    )
