from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.status import VideoStatus


def _new_id() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VideoModel(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VideoStatus.UPLOADED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transcript_segments: Mapped[list[TranscriptSegmentModel]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    keyframes: Mapped[list[KeyframeModel]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    scenes: Mapped[list[SceneModel]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    timeline_events: Mapped[list[TimelineEventModel]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('uploaded', 'processing', 'analyzed', 'failed')",
            name="ck_videos_status",
        ),
    )


class TranscriptSegmentModel(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    video: Mapped[VideoModel] = relationship(back_populates="transcript_segments")

    __table_args__ = (
        CheckConstraint("start_time <= end_time", name="ck_transcript_time_range"),
        Index("ix_transcript_segments_video_id", "video_id"),
        Index("ix_transcript_segments_video_start", "video_id", "start_time"),
    )


class KeyframeModel(Base):
    __tablename__ = "keyframes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    time: Mapped[float] = mapped_column(Float, nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    visual_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    video: Mapped[VideoModel] = relationship(back_populates="keyframes")

    __table_args__ = (
        Index("ix_keyframes_video_id", "video_id"),
        Index("ix_keyframes_video_time", "video_id", "time"),
    )


class SceneModel(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    video: Mapped[VideoModel] = relationship(back_populates="scenes")

    __table_args__ = (
        CheckConstraint("start_time <= end_time", name="ck_scene_time_range"),
        Index("ix_scenes_video_id", "video_id"),
        Index("ix_scenes_video_start", "video_id", "start_time"),
    )


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    video: Mapped[VideoModel] = relationship(back_populates="timeline_events")
    evidence_links: Mapped[list[EvidenceLinkModel]] = relationship(
        back_populates="timeline_event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("start_time <= end_time", name="ck_timeline_event_time_range"),
        Index("ix_timeline_events_video_id", "video_id"),
        Index("ix_timeline_events_video_start", "video_id", "start_time"),
    )


class EvidenceLinkModel(Base):
    __tablename__ = "evidence_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    timeline_event_id: Mapped[str] = mapped_column(ForeignKey("timeline_events.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(36), nullable=False)

    timeline_event: Mapped[TimelineEventModel] = relationship(back_populates="evidence_links")

    __table_args__ = (
        CheckConstraint(
            "evidence_type in ('transcript', 'frame', 'scene', 'timeline_event')",
            name="ck_evidence_links_type",
        ),
        Index("ix_evidence_links_timeline_event_id", "timeline_event_id"),
    )
