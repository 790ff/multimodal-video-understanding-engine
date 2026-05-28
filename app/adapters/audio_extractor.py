from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioExtractionResult:
    audio_path: Path


class AudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        raise NotImplementedError("FFmpeg audio extraction starts in M3.")
