from pathlib import Path

import pytest

from app.adapters.frame_analyzer import FrameAnalyzer
from app.adapters.transcriber import Transcriber
from app.config import Settings
from app.domain.errors import ProcessingAppError


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        upload_dir=tmp_path / "uploads",
        audio_dir=tmp_path / "audio",
        frame_dir=tmp_path / "frames",
        openai_api_key=None,
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
