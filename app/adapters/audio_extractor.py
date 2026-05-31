from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import Settings, get_settings
from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class AudioExtractionResult:
    audio_path: Path


class AudioExtractor:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

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
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.settings.ffmpeg_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            output_path.unlink(missing_ok=True)
            raise ProcessingAppError(
                "Audio extraction timed out.",
                code="audio_extraction_timeout",
            ) from exc
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            output_path.unlink(missing_ok=True)
            raise ProcessingAppError(
                "Could not extract audio from video.",
                code="audio_extraction_failed",
            ) from exc

        return AudioExtractionResult(audio_path=output_path)
