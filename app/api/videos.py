from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import EvidenceLinkModel, KeyframeModel, SceneModel, TranscriptSegmentModel
from app.domain.errors import AppError, ConflictAppError, NotFoundAppError, StorageAppError
from app.domain.status import VideoStatus
from app.repositories.video_repository import VideoRepository
from app.schemas import (
    AnalyzeVideoResponse,
    ErrorResponse,
    TimelineEventResponse,
    TimelineEvidence,
    TimelineResponse,
    VideoStatusResponse,
    VideoUploadResponse,
)
from app.services.video_processor import VideoProcessor
from app.services.video_storage import VideoStorageService

router = APIRouter(prefix="/videos", tags=["videos"])


def get_video_storage_service() -> VideoStorageService:
    return VideoStorageService()


def get_video_processor() -> VideoProcessor:
    return VideoProcessor()


UploadVideoFile = Annotated[UploadFile, File(...)]
DatabaseSession = Annotated[Session, Depends(get_db)]
StorageService = Annotated[VideoStorageService, Depends(get_video_storage_service)]
ProcessorService = Annotated[VideoProcessor, Depends(get_video_processor)]


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


@router.post(
    "/{video_id}/analyze",
    response_model=AnalyzeVideoResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def analyze_video(
    video_id: str,
    db: DatabaseSession,
    processor: ProcessorService,
) -> AnalyzeVideoResponse:
    repository = VideoRepository(db)
    result = processor.analyze(video_id=video_id, repository=repository)

    return AnalyzeVideoResponse(
        video_id=result.video_id,
        status=result.status,
        transcript_segments=result.transcript_segments,
        keyframes=result.keyframes,
        scenes=result.scenes,
        timeline_events=result.timeline_events,
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


@router.get(
    "/{video_id}/timeline",
    response_model=TimelineResponse,
    response_model_exclude_none=True,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def get_video_timeline(
    video_id: str,
    db: DatabaseSession,
) -> TimelineResponse:
    repository = VideoRepository(db)
    video = repository.get(video_id)
    if video is None:
        raise NotFoundAppError(
            "Video was not found.",
            code="video_not_found",
        )
    if VideoStatus(video.status) != VideoStatus.ANALYZED:
        raise ConflictAppError(
            "Video has not been analyzed.",
            code="video_not_analyzed",
        )

    transcripts = {
        segment.id: segment for segment in repository.list_transcript_segments(video)
    }
    keyframes = {keyframe.id: keyframe for keyframe in repository.list_keyframes(video)}
    scenes = {scene.id: scene for scene in repository.list_scenes(video)}

    events = []
    for event in repository.list_timeline_events(video):
        evidence = []
        sorted_links = sorted(
            event.evidence_links,
            key=lambda link: _evidence_sort_key(
                link,
                transcripts=transcripts,
                keyframes=keyframes,
                scenes=scenes,
            ),
        )
        for link in sorted_links:
            if link.evidence_type == "transcript" and link.evidence_id in transcripts:
                segment = transcripts[link.evidence_id]
                evidence.append(
                    TimelineEvidence(
                        type="transcript",
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                    )
                )
            elif link.evidence_type == "frame" and link.evidence_id in keyframes:
                keyframe = keyframes[link.evidence_id]
                evidence.append(
                    TimelineEvidence(
                        type="frame",
                        time=keyframe.time,
                        path=keyframe.path,
                    )
                )
            elif link.evidence_type == "scene" and link.evidence_id in scenes:
                scene = scenes[link.evidence_id]
                evidence.append(
                    TimelineEvidence(
                        type="scene",
                        start_time=scene.start_time,
                        end_time=scene.end_time,
                    )
                )
        events.append(
            TimelineEventResponse(
                start_time=event.start_time,
                end_time=event.end_time,
                summary=event.summary,
                evidence=evidence,
            )
        )

    return TimelineResponse(video_id=video.id, events=events)


def _evidence_sort_key(
    link: EvidenceLinkModel,
    *,
    transcripts: dict[str, TranscriptSegmentModel],
    keyframes: dict[str, KeyframeModel],
    scenes: dict[str, SceneModel],
) -> tuple[int, float, float]:
    evidence_type = link.evidence_type
    evidence_id = link.evidence_id
    if evidence_type == "scene" and evidence_id in scenes:
        scene = scenes[evidence_id]
        return (0, scene.start_time, scene.end_time)
    if evidence_type == "transcript" and evidence_id in transcripts:
        segment = transcripts[evidence_id]
        return (1, segment.start_time, segment.end_time)
    if evidence_type == "frame" and evidence_id in keyframes:
        keyframe = keyframes[evidence_id]
        return (2, keyframe.time, keyframe.time)
    return (9, 0.0, 0.0)
