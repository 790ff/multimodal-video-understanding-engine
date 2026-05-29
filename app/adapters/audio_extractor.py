from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class AudioExtractionResult:
    audio_path: Path


class AudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            output_path.unlink(missing_ok=True)
            raise ProcessingAppError(
                "Could not extract audio from video.",
                code="audio_extraction_failed",
            ) from exc

        return AudioExtractionResult(audio_path=output_path)
