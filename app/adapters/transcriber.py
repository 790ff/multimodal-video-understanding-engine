from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.config import Settings, get_settings
from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class TranscriptSegmentData:
    start_time: float
    end_time: float
    text: str


class Transcriber:
    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        model: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.transcription_model

    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        if not audio_path.is_file():
            raise ProcessingAppError(
                "Extracted audio file was not found.",
                code="audio_file_missing",
            )
        if not self.settings.openai_api_key:
            raise ProcessingAppError(
                "Transcription service is not configured.",
                code="transcription_not_configured",
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProcessingAppError(
                "Transcription dependency is not installed.",
                code="transcription_dependency_missing",
            ) from exc

        client = OpenAI(api_key=self.settings.openai_api_key)
        with audio_path.open("rb") as audio_file:
            if self.model == "whisper-1":
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            else:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                )

        return self._segments_from_response(response)

    def _segments_from_response(self, response: Any) -> list[TranscriptSegmentData]:
        raw_segments = self._get_value(response, "segments")
        if raw_segments:
            return [
                TranscriptSegmentData(
                    start_time=float(self._get_value(segment, "start", default=0.0)),
                    end_time=float(self._get_value(segment, "end", default=0.0)),
                    text=str(self._get_value(segment, "text", default="")).strip(),
                )
                for segment in raw_segments
                if str(self._get_value(segment, "text", default="")).strip()
            ]

        text = str(self._get_value(response, "text", default="")).strip()
        if not text:
            return []

        return [TranscriptSegmentData(start_time=0.0, end_time=0.0, text=text)]

    def _get_value(self, value: Any, field: str, *, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(field, default)
        return getattr(value, field, default)
