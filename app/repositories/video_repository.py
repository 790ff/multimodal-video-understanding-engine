from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import VideoModel
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
