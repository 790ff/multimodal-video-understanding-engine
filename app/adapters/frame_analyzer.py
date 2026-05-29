from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import Settings, get_settings
from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class FrameAnalysisResult:
    frame_path: Path
    visual_summary: str


class FrameAnalyzer:
    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        model: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.vision_model

    def analyze(self, frame_paths: list[Path]) -> list[FrameAnalysisResult]:
        if not frame_paths:
            return []

        missing_paths = [
            str(frame_path)
            for frame_path in frame_paths
            if not frame_path.is_file() or frame_path.stat().st_size == 0
        ]
        if missing_paths:
            raise ProcessingAppError(
                "Keyframe file was not found.",
                code="keyframe_file_missing",
            )
        if not self.settings.openai_api_key:
            raise ProcessingAppError(
                "Frame analysis service is not configured.",
                code="frame_analysis_not_configured",
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProcessingAppError(
                "Frame analysis dependency is not installed.",
                code="frame_analysis_dependency_missing",
            ) from exc

        try:
            client = OpenAI(api_key=self.settings.openai_api_key)
            return [
                self._analyze_one(client=client, frame_path=frame_path)
                for frame_path in frame_paths
            ]
        except ProcessingAppError:
            raise
        except Exception as exc:
            raise ProcessingAppError(
                "Frame analysis service failed.",
                code="frame_analysis_failed",
            ) from exc

    def _analyze_one(self, *, client: object, frame_path: Path) -> FrameAnalysisResult:
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Summarize the visible content of this video keyframe in one "
                                "concise sentence. Mention only observable visual evidence."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": self._data_url(frame_path),
                            "detail": "low",
                        },
                    ],
                }
            ],
        )
        summary = str(getattr(response, "output_text", "")).strip()
        if not summary:
            raise ProcessingAppError(
                "Frame analysis returned an empty summary.",
                code="frame_analysis_empty",
            )
        return FrameAnalysisResult(frame_path=frame_path, visual_summary=summary)

    def _data_url(self, frame_path: Path) -> str:
        mime_type = mimetypes.guess_type(frame_path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"


class GeminiFrameAnalyzer:
    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        model: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.gemini_model

    def analyze(self, frame_paths: list[Path]) -> list[FrameAnalysisResult]:
        if not frame_paths:
            return []

        missing_paths = [
            str(frame_path)
            for frame_path in frame_paths
            if not frame_path.is_file() or frame_path.stat().st_size == 0
        ]
        if missing_paths:
            raise ProcessingAppError(
                "Keyframe file was not found.",
                code="keyframe_file_missing",
            )
        if not self.settings.gemini_api_key:
            raise ProcessingAppError(
                "Frame analysis service is not configured.",
                code="frame_analysis_not_configured",
            )

        try:
            from google import genai
        except ImportError as exc:
            raise ProcessingAppError(
                "Frame analysis dependency is not installed.",
                code="frame_analysis_dependency_missing",
            ) from exc

        try:
            client = genai.Client(api_key=self.settings.gemini_api_key)
            return [
                self._analyze_one(client=client, frame_path=frame_path)
                for frame_path in frame_paths
            ]
        except ProcessingAppError:
            raise
        except Exception as exc:
            raise ProcessingAppError(
                "Frame analysis service failed.",
                code="frame_analysis_failed",
            ) from exc

    def _analyze_one(self, *, client: object, frame_path: Path) -> FrameAnalysisResult:
        uploaded_frame = client.files.upload(file=str(frame_path))
        response = client.models.generate_content(
            model=self.model,
            contents=[
                (
                    "Summarize the visible content of this video keyframe in one "
                    "concise sentence. Mention only observable visual evidence."
                ),
                uploaded_frame,
            ],
        )
        summary = str(getattr(response, "text", "")).strip()
        if not summary:
            raise ProcessingAppError(
                "Frame analysis returned an empty summary.",
                code="frame_analysis_empty",
            )
        return FrameAnalysisResult(frame_path=frame_path, visual_summary=summary)
