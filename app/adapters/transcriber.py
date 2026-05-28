from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptSegmentData:
    start_time: float
    end_time: float
    text: str


class Transcriber:
    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        raise NotImplementedError("Transcription starts in M4.")
