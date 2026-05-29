from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class DetectedScene:
    start_time: float
    end_time: float


class SceneDetector:
    def __init__(self, threshold: float = 27.0) -> None:
        self.threshold = threshold

    def detect(self, video_path: Path) -> list[DetectedScene]:
        try:
            from scenedetect import SceneManager, open_video
            from scenedetect.detectors import ContentDetector
        except ImportError as exc:
            raise ProcessingAppError(
                "Could not detect scenes in video.",
                code="scene_detection_unavailable",
            ) from exc

        try:
            video = open_video(str(video_path))
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=self.threshold))
            scene_manager.detect_scenes(video)
        except Exception as exc:
            raise ProcessingAppError(
                "Could not detect scenes in video.",
                code="scene_detection_failed",
            ) from exc

        return [
            DetectedScene(
                start_time=round(start_time.get_seconds(), 3),
                end_time=round(end_time.get_seconds(), 3),
            )
            for start_time, end_time in scene_manager.get_scene_list()
        ]
