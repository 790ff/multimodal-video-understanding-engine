from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KeyframeModel, SceneModel, TranscriptSegmentModel, VideoModel
from app.domain.status import VideoStatus


class VideoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, video_id: str) -> Optional[VideoModel]:
        return self.session.get(VideoModel, video_id)

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
