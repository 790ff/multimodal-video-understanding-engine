from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtractedFrame:
    time: float
    path: Path


class FrameExtractor:
    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        sample_seconds: int,
    ) -> list[ExtractedFrame]:
        raise NotImplementedError("OpenCV frame extraction starts in M3.")
