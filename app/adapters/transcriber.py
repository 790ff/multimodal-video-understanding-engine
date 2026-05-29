from __future__ import annotations

import json
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

        try:
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
        except Exception as exc:
            raise ProcessingAppError(
                "Transcription service failed.",
                code="transcription_failed",
            ) from exc

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


class GeminiTranscriber:
    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        model: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.gemini_model

    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        if not audio_path.is_file():
            raise ProcessingAppError(
                "Extracted audio file was not found.",
                code="audio_file_missing",
            )
        if not self.settings.gemini_api_key:
            raise ProcessingAppError(
                "Transcription service is not configured.",
                code="transcription_not_configured",
            )

        try:
            from google import genai
        except ImportError as exc:
            raise ProcessingAppError(
                "Transcription dependency is not installed.",
                code="transcription_dependency_missing",
            ) from exc

        try:
            client = genai.Client(api_key=self.settings.gemini_api_key)
            uploaded_audio = client.files.upload(file=str(audio_path))
            response = client.models.generate_content(
                model=self.model,
                contents=[self._transcription_prompt(), uploaded_audio],
            )
        except Exception as exc:
            raise ProcessingAppError(
                "Transcription service failed.",
                code="transcription_failed",
            ) from exc

        return self._segments_from_text(str(getattr(response, "text", "")).strip())

    def _transcription_prompt(self) -> str:
        return (
            "Transcribe this audio for a video analysis pipeline. Return only JSON with "
            'this shape: {"segments":[{"start_time":0.0,"end_time":0.0,"text":"..."}]}. '
            "Use seconds for timestamps. If exact timestamps are unavailable, return one "
            "segment with start_time 0.0 and end_time 0.0."
        )

    def _segments_from_text(self, response_text: str) -> list[TranscriptSegmentData]:
        data = self._json_from_text(response_text)
        raw_segments = data.get("segments", [])
        if not isinstance(raw_segments, list):
            raise ProcessingAppError(
                "Transcription returned an invalid response.",
                code="transcription_invalid_response",
            )

        segments = []
        for segment in raw_segments:
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            start_time = float(segment.get("start_time", segment.get("start", 0.0)))
            end_time = float(segment.get("end_time", segment.get("end", 0.0)))
            segments.append(
                TranscriptSegmentData(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                )
            )
        return segments

    def _json_from_text(self, response_text: str) -> dict[str, Any]:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProcessingAppError(
                "Transcription returned an invalid response.",
                code="transcription_invalid_response",
            ) from exc
        if not isinstance(data, dict):
            raise ProcessingAppError(
                "Transcription returned an invalid response.",
                code="transcription_invalid_response",
            )
        return data
