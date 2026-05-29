from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import KeyframeModel, SceneModel, VideoModel
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
        video.keyframes.clear()
        video.scenes.clear()
        self.session.flush()

    def replace_keyframes(
        self,
        video: VideoModel,
        keyframes: Iterable[tuple[float, str]],
    ) -> list[KeyframeModel]:
        video.keyframes.clear()
        self.session.flush()

        models = [
            KeyframeModel(
                video_id=video.id,
                time=time,
                path=path,
            )
            for time, path in keyframes
        ]
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
