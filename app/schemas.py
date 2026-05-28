from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.status import VideoStatus


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


class VideosModuleResponse(BaseModel):
    module: str
    status: str
    milestone: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str
    status: VideoStatus


class VideoStatusResponse(BaseModel):
    video_id: str
    status: VideoStatus
    error_message: Optional[str] = None


class AnalyzeVideoResponse(BaseModel):
    video_id: str
    status: VideoStatus
    transcript_segments: int = 0
    keyframes: int = 0
    scenes: int = 0
    timeline_events: int = 0


class TimelineEvidence(BaseModel):
    type: str
    time: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    path: Optional[str] = None


class TimelineEventResponse(BaseModel):
    start_time: float
    end_time: float
    summary: str
    evidence: list[TimelineEvidence] = Field(default_factory=list)


class TimelineResponse(BaseModel):
    video_id: str
    events: list[TimelineEventResponse] = Field(default_factory=list)


class AskVideoRequest(BaseModel):
    question: str = Field(min_length=1)


class AskVideoResponse(BaseModel):
    answer: str
    evidence: list[TimelineEvidence] = Field(default_factory=list)
