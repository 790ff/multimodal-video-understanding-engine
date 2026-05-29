from __future__ import annotations

from app.adapters.frame_analyzer import FrameAnalyzer, GeminiFrameAnalyzer
from app.adapters.transcriber import GeminiTranscriber, Transcriber
from app.config import Settings
from app.domain.errors import ProcessingAppError


def create_transcriber(settings: Settings) -> Transcriber | GeminiTranscriber:
    provider = settings.active_model_provider
    if provider == "openai":
        return Transcriber(settings=settings)
    if provider == "gemini":
        return GeminiTranscriber(settings=settings)
    raise _unsupported_provider(provider)


def create_frame_analyzer(settings: Settings) -> FrameAnalyzer | GeminiFrameAnalyzer:
    provider = settings.active_model_provider
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
            "supported_providers": ["gemini", "openai"],
        },
    )
