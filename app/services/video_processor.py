from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.adapters.audio_extractor import AudioExtractor
from app.adapters.frame_extractor import ExtractedFrame, FrameExtractor
from app.adapters.scene_detector import DetectedScene, SceneDetector
from app.config import Settings, get_settings
from app.domain.errors import ConflictAppError, NotFoundAppError, ProcessingAppError
from app.domain.status import VideoStatus
from app.repositories.video_repository import VideoRepository

SAFE_PROCESSING_ERROR_MESSAGE = "Video preprocessing failed."


@dataclass(frozen=True)
class AnalysisResult:
    video_id: str
    status: VideoStatus
    transcript_segments: int = 0
    keyframes: int = 0
    scenes: int = 0
    timeline_events: int = 0


class VideoProcessor:
    def __init__(
        self,
        *,
        audio_extractor: Optional[AudioExtractor] = None,
        frame_extractor: Optional[FrameExtractor] = None,
        scene_detector: Optional[SceneDetector] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.audio_extractor = audio_extractor or AudioExtractor()
        self.frame_extractor = frame_extractor or FrameExtractor()
        self.scene_detector = scene_detector or SceneDetector()

    def analyze(self, video_id: str, repository: VideoRepository) -> AnalysisResult:
        video = repository.get(video_id)
        if video is None:
            raise NotFoundAppError(
                "Video was not found.",
                code="video_not_found",
            )
        if VideoStatus(video.status) == VideoStatus.PROCESSING:
            raise ConflictAppError(
                "Video is already processing.",
                code="video_already_processing",
            )

        video_path = Path(video.stored_path)
        audio_path = self._audio_output_path(video_id)
        frame_dir = self._frame_output_dir(video_id)

        try:
            repository.set_status(video, VideoStatus.PROCESSING, error_message=None)
            repository.clear_preprocessing_metadata(video)
            repository.session.commit()

            self._prepare_output_paths(audio_path=audio_path, frame_dir=frame_dir)
            self.audio_extractor.extract(video_path=video_path, output_path=audio_path)
            keyframes = self.frame_extractor.extract(
                video_path=video_path,
                output_dir=frame_dir,
                sample_seconds=self.settings.frame_sample_seconds,
            )
            scenes = self._detect_scenes_with_fallback(
                video_path=video_path,
                keyframes=keyframes,
            )

            repository.replace_keyframes(
                video,
                [(keyframe.time, str(keyframe.path)) for keyframe in keyframes],
            )
            repository.replace_scenes(
                video,
                [(scene.start_time, scene.end_time) for scene in scenes],
            )
            repository.set_status(video, VideoStatus.ANALYZED, error_message=None)
            repository.session.commit()

            return AnalysisResult(
                video_id=video.id,
                status=VideoStatus.ANALYZED,
                keyframes=len(keyframes),
                scenes=len(scenes),
            )
        except Exception as exc:
            self._mark_failed(video_id=video_id, repository=repository)
            raise ProcessingAppError(
                SAFE_PROCESSING_ERROR_MESSAGE,
                code=self._safe_processing_code(exc),
            ) from exc

    def _audio_output_path(self, video_id: str) -> Path:
        return self.settings.audio_dir / video_id / "audio.wav"

    def _frame_output_dir(self, video_id: str) -> Path:
        return self.settings.frame_dir / video_id

    def _prepare_output_paths(self, *, audio_path: Path, frame_dir: Path) -> None:
        shutil.rmtree(audio_path.parent, ignore_errors=True)
        shutil.rmtree(frame_dir, ignore_errors=True)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        frame_dir.mkdir(parents=True, exist_ok=True)

    def _detect_scenes_with_fallback(
        self,
        *,
        video_path: Path,
        keyframes: list[ExtractedFrame],
    ) -> list[DetectedScene]:
        try:
            scenes = self.scene_detector.detect(video_path=video_path)
        except Exception:
            return self._fallback_scenes_from_keyframes(keyframes)

        return scenes or self._fallback_scenes_from_keyframes(keyframes)

    def _fallback_scenes_from_keyframes(
        self,
        keyframes: list[ExtractedFrame],
    ) -> list[DetectedScene]:
        scenes: list[DetectedScene] = []
        for index, keyframe in enumerate(keyframes):
            start_time = round(keyframe.time, 3)
            if index + 1 < len(keyframes):
                end_time = round(keyframes[index + 1].time, 3)
            else:
                end_time = round(start_time + self.settings.frame_sample_seconds, 3)
            scenes.append(
                DetectedScene(
                    start_time=start_time,
                    end_time=max(start_time, end_time),
                )
            )
        return scenes

    def _mark_failed(self, *, video_id: str, repository: VideoRepository) -> None:
        repository.session.rollback()
        video = repository.get(video_id)
        if video is None:
            return
        repository.set_status(
            video,
            VideoStatus.FAILED,
            error_message=SAFE_PROCESSING_ERROR_MESSAGE,
        )
        repository.session.commit()

    def _safe_processing_code(self, exc: Exception) -> str:
        if isinstance(exc, ProcessingAppError):
            return exc.code
        return "video_preprocessing_failed"
