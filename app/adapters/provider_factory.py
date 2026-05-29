from __future__ import annotations

from pathlib import Path

from app.adapters.frame_analyzer import FrameAnalyzer, GeminiFrameAnalyzer
from app.adapters.transcriber import GeminiTranscriber, Transcriber, TranscriptSegmentData
from app.config import Settings
from app.domain.errors import ProcessingAppError

SUPPORTED_PROVIDERS = ["gemini", "openai"]
TRANSCRIPTION_FALLBACK_CODES = {
    "transcription_dependency_missing",
    "transcription_failed",
    "transcription_invalid_response",
    "transcription_not_configured",
}


class FallbackTranscriber:
    def __init__(self, transcribers: list[tuple[str, Transcriber | GeminiTranscriber]]) -> None:
        self.transcribers = transcribers

    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        last_error: ProcessingAppError | None = None
        for _, transcriber in self.transcribers:
            try:
                return transcriber.transcribe(audio_path)
            except ProcessingAppError as exc:
                if exc.code not in TRANSCRIPTION_FALLBACK_CODES:
                    raise
                last_error = exc
        if last_error is not None:
            raise last_error
        return []


def create_transcriber(settings: Settings) -> Transcriber | GeminiTranscriber | FallbackTranscriber:
    providers = settings.active_transcription_providers
    transcribers = [
        (provider, _create_transcriber_for_provider(provider=provider, settings=settings))
        for provider in providers
    ]
    if len(transcribers) == 1:
        return transcribers[0][1]
    return FallbackTranscriber(transcribers)


def create_frame_analyzer(settings: Settings) -> FrameAnalyzer | GeminiFrameAnalyzer:
    return _create_frame_analyzer_for_provider(
        provider=settings.active_frame_analysis_provider,
        settings=settings,
    )


def _create_transcriber_for_provider(
    *,
    provider: str,
    settings: Settings,
) -> Transcriber | GeminiTranscriber:
    if provider == "openai":
        return Transcriber(settings=settings)
    if provider == "gemini":
        return GeminiTranscriber(settings=settings)
    raise _unsupported_provider(provider)


def _create_frame_analyzer_for_provider(
    *,
    provider: str,
    settings: Settings,
) -> FrameAnalyzer | GeminiFrameAnalyzer:
    if provider == "openai":
        return FrameAnalyzer(settings=settings)
    if provider == "gemini":
        return GeminiFrameAnalyzer(settings=settings)
    raise _unsupported_provider(provider)


def _unsupported_provider(provider: str) -> ProcessingAppError:
    return ProcessingAppError(
        "Configured model provider is not supported.",
        code="model_provider_unsupported",
        details={
            "provider": provider,
            "supported_providers": SUPPORTED_PROVIDERS,
        },
    )
