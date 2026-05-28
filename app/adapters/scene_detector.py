from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectedScene:
    start_time: float
    end_time: float


class SceneDetector:
    def detect(self, video_path: Path) -> list[DetectedScene]:
        raise NotImplementedError("Scene detection starts in M3.")
