from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.frame_analyzer import FrameAnalyzer, GeminiFrameAnalyzer
from app.adapters.provider_factory import (
    FallbackTranscriber,
    create_frame_analyzer,
    create_transcriber,
)
from app.adapters.transcriber import GeminiTranscriber, Transcriber
from app.config import Settings
from app.domain.errors import ProcessingAppError


def make_settings(
    tmp_path: Path,
    *,
    model_provider: str = "openai",
    transcription_provider_order: str | None = None,
    frame_analysis_provider: str | None = None,
    gemini_api_key: str | None = None,
) -> Settings:
    return Settings(
        _env_file=None,
        model_provider=model_provider,
        transcription_provider_order=transcription_provider_order,
        frame_analysis_provider=frame_analysis_provider,
        upload_dir=tmp_path / "uploads",
        audio_dir=tmp_path / "audio",
        frame_dir=tmp_path / "frames",
        openai_api_key=None,
        gemini_api_key=gemini_api_key,
    )


def test_transcriber_missing_api_key_raises_controlled_error(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav bytes")
    transcriber = Transcriber(settings=make_settings(tmp_path))

    with pytest.raises(ProcessingAppError) as exc_info:
        transcriber.transcribe(audio_path)

    assert exc_info.value.code == "transcription_not_configured"
    assert exc_info.value.message == "Transcription service is not configured."


def test_frame_analyzer_missing_api_key_raises_controlled_error(tmp_path: Path) -> None:
    frame_path = tmp_path / "frame_000001.jpg"
    frame_path.write_bytes(b"fake jpg bytes")
    frame_analyzer = FrameAnalyzer(settings=make_settings(tmp_path))

    with pytest.raises(ProcessingAppError) as exc_info:
        frame_analyzer.analyze([frame_path])

    assert exc_info.value.code == "frame_analysis_not_configured"
    assert exc_info.value.message == "Frame analysis service is not configured."


def test_provider_factory_defaults_to_openai_adapters(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)

    assert isinstance(create_transcriber(settings), Transcriber)
    assert isinstance(create_frame_analyzer(settings), FrameAnalyzer)


def test_provider_factory_creates_gemini_adapters(tmp_path: Path) -> None:
    settings = make_settings(
        tmp_path,
        model_provider="gemini",
        gemini_api_key="test-key",
    )

    assert isinstance(create_transcriber(settings), GeminiTranscriber)
    assert isinstance(create_frame_analyzer(settings), GeminiFrameAnalyzer)


def test_provider_factory_uses_separate_transcription_and_frame_providers(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path,
        model_provider="openai",
        transcription_provider_order="openai",
        frame_analysis_provider="gemini",
        gemini_api_key="test-key",
    )

    assert isinstance(create_transcriber(settings), Transcriber)
    assert isinstance(create_frame_analyzer(settings), GeminiFrameAnalyzer)


def test_provider_factory_creates_fallback_transcriber(tmp_path: Path) -> None:
    settings = make_settings(
        tmp_path,
        model_provider="gemini",
        transcription_provider_order="gemini,openai",
        gemini_api_key="test-key",
    )

    transcriber = create_transcriber(settings)

    assert isinstance(transcriber, FallbackTranscriber)
    assert [provider for provider, _ in transcriber.transcribers] == ["gemini", "openai"]


def test_provider_factory_rejects_unsupported_provider(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, model_provider="unknown-provider")

    with pytest.raises(ProcessingAppError) as exc_info:
        create_transcriber(settings)

    assert exc_info.value.code == "model_provider_unsupported"
    assert exc_info.value.details == {
        "provider": "unknown-provider",
        "supported_providers": ["gemini", "openai"],
    }


def test_fallback_transcriber_uses_next_provider_after_provider_failure(
    tmp_path: Path,
) -> None:
    class FailingTranscriber:
        def transcribe(self, audio_path: Path) -> list[object]:
            raise ProcessingAppError(
                "Transcription service failed.",
                code="transcription_failed",
            )

    class SuccessfulTranscriber:
        def transcribe(self, audio_path: Path) -> list[str]:
            return ["saved by fallback"]

    transcriber = FallbackTranscriber(
        [
            ("first", FailingTranscriber()),
            ("second", SuccessfulTranscriber()),
        ]
    )

    assert transcriber.transcribe(tmp_path / "audio.wav") == ["saved by fallback"]


def test_fallback_transcriber_does_not_hide_non_provider_errors(tmp_path: Path) -> None:
    class MissingAudioTranscriber:
        def transcribe(self, audio_path: Path) -> list[object]:
            raise ProcessingAppError(
                "Extracted audio file was not found.",
                code="audio_file_missing",
            )

    transcriber = FallbackTranscriber([("first", MissingAudioTranscriber())])

    with pytest.raises(ProcessingAppError) as exc_info:
        transcriber.transcribe(tmp_path / "missing.wav")

    assert exc_info.value.code == "audio_file_missing"


def test_gemini_transcriber_missing_api_key_raises_controlled_error(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav bytes")
    transcriber = GeminiTranscriber(settings=make_settings(tmp_path, model_provider="gemini"))

    with pytest.raises(ProcessingAppError) as exc_info:
        transcriber.transcribe(audio_path)

    assert exc_info.value.code == "transcription_not_configured"
    assert exc_info.value.message == "Transcription service is not configured."


def test_gemini_frame_analyzer_missing_api_key_raises_controlled_error(
    tmp_path: Path,
) -> None:
    frame_path = tmp_path / "frame_000001.jpg"
    frame_path.write_bytes(b"fake jpg bytes")
    frame_analyzer = GeminiFrameAnalyzer(settings=make_settings(tmp_path, model_provider="gemini"))

    with pytest.raises(ProcessingAppError) as exc_info:
        frame_analyzer.analyze([frame_path])

    assert exc_info.value.code == "frame_analysis_not_configured"
    assert exc_info.value.message == "Frame analysis service is not configured."


def test_gemini_transcriber_parses_json_segments(tmp_path: Path) -> None:
    transcriber = GeminiTranscriber(
        settings=make_settings(
            tmp_path,
            model_provider="gemini",
            gemini_api_key="test-key",
        )
    )

    segments = transcriber._segments_from_text(
        """
        ```json
        {"segments":[{"start_time":1.2,"end_time":3.4,"text":"Hello from Gemini."}]}
        ```
        """
    )

    assert segments[0].start_time == 1.2
    assert segments[0].end_time == 3.4
    assert segments[0].text == "Hello from Gemini."
