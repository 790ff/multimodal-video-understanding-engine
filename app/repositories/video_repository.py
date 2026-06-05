from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    EvidenceLinkModel,
    KeyframeModel,
    SceneModel,
    TimelineEventModel,
    TranscriptSegmentModel,
    VideoModel,
)
from app.domain.status import VideoStatus
from app.domain.timeline import TimelineEventData


class VideoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, video_id: str) -> Optional[VideoModel]:
        return self.session.get(VideoModel, video_id)

    def list_video_ids(self) -> list[str]:
        statement = select(VideoModel.id).order_by(VideoModel.created_at)
        return list(self.session.scalars(statement))

    def create(
        self,
        *,
        video_id: str,
        original_filename: str,
        stored_path: str,
    ) -> VideoModel:
        video = VideoModel(
            id=video_id,
            original_filename=original_filename,
            stored_path=stored_path,
        )
        self.session.add(video)
        self.session.flush()
        return video

    def set_status(
        self,
        video: VideoModel,
        status: VideoStatus,
        *,
        error_message: Optional[str] = None,
    ) -> VideoModel:
        video.status = status.value
        video.error_message = error_message
        self.session.flush()
        return video

    def clear_preprocessing_metadata(self, video: VideoModel) -> None:
        video.transcript_segments.clear()
        video.keyframes.clear()
        video.scenes.clear()
        video.timeline_events.clear()
        self.session.flush()

    def clear_all_metadata(self) -> None:
        for video in list(self.session.scalars(select(VideoModel))):
            self.session.delete(video)
        self.session.flush()

    def clear_analysis_outputs(self, video: VideoModel) -> None:
        video.transcript_segments.clear()
        video.timeline_events.clear()
        for keyframe in self.list_keyframes(video):
            keyframe.visual_summary = None
        self.session.flush()

    def list_keyframes(self, video: VideoModel) -> list[KeyframeModel]:
        statement = (
            select(KeyframeModel)
            .where(KeyframeModel.video_id == video.id)
            .order_by(KeyframeModel.time)
        )
        return list(self.session.scalars(statement))

    def list_scenes(self, video: VideoModel) -> list[SceneModel]:
        statement = (
            select(SceneModel)
            .where(SceneModel.video_id == video.id)
            .order_by(SceneModel.start_time)
        )
        return list(self.session.scalars(statement))

    def list_transcript_segments(self, video: VideoModel) -> list[TranscriptSegmentModel]:
        statement = (
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.video_id == video.id)
            .order_by(TranscriptSegmentModel.start_time)
        )
        return list(self.session.scalars(statement))

    def list_timeline_events(self, video: VideoModel) -> list[TimelineEventModel]:
        statement = (
            select(TimelineEventModel)
            .options(selectinload(TimelineEventModel.evidence_links))
            .where(TimelineEventModel.video_id == video.id)
            .order_by(TimelineEventModel.start_time)
        )
        return list(self.session.scalars(statement))

    def replace_keyframes(
        self,
        video: VideoModel,
        keyframes: Iterable[tuple[float, str] | tuple[float, str, Optional[str]]],
    ) -> list[KeyframeModel]:
        video.keyframes.clear()
        self.session.flush()

        models = []
        for keyframe in keyframes:
            time = keyframe[0]
            path = keyframe[1]
            visual_summary = keyframe[2] if len(keyframe) == 3 else None
            models.append(
                KeyframeModel(
                    video_id=video.id,
                    time=time,
                    path=path,
                    visual_summary=visual_summary,
                )
            )
        video.keyframes.extend(models)
        self.session.flush()
        return models

    def replace_scenes(
        self,
        video: VideoModel,
        scenes: Iterable[tuple[float, float]],
    ) -> list[SceneModel]:
        video.scenes.clear()
        self.session.flush()

        models = [
            SceneModel(
                video_id=video.id,
                start_time=start_time,
                end_time=end_time,
            )
            for start_time, end_time in scenes
        ]
        video.scenes.extend(models)
        self.session.flush()
        return models

    def replace_transcript_segments(
        self,
        video: VideoModel,
        segments: Iterable[tuple[float, float, str]],
    ) -> list[TranscriptSegmentModel]:
        video.transcript_segments.clear()
        self.session.flush()

        models = [
            TranscriptSegmentModel(
                video_id=video.id,
                start_time=start_time,
                end_time=end_time,
                text=text,
            )
            for start_time, end_time, text in segments
        ]
        video.transcript_segments.extend(models)
        self.session.flush()
        return models

    def update_keyframe_visual_summaries(
        self,
        video: VideoModel,
        summaries: Iterable[tuple[str, str]],
    ) -> int:
        summary_by_path = dict(summaries)
        updated = 0
        for keyframe in self.list_keyframes(video):
            summary = summary_by_path.get(keyframe.path)
            if summary is None:
                continue
            keyframe.visual_summary = summary
            updated += 1
        self.session.flush()
        return updated

    def replace_timeline_events(
        self,
        video: VideoModel,
        events: Iterable[TimelineEventData],
    ) -> list[TimelineEventModel]:
        video.timeline_events.clear()
        self.session.flush()

        models = []
        for event in events:
            model = TimelineEventModel(
                video_id=video.id,
                start_time=event.start_time,
                end_time=event.end_time,
                summary=event.summary,
            )
            model.evidence_links.extend(
                EvidenceLinkModel(
                    evidence_type=evidence.evidence_type,
                    evidence_id=evidence.evidence_id,
                )
                for evidence in event.evidence
            )
            models.append(model)
        video.timeline_events.extend(models)
        self.session.flush()
        return models
