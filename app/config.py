from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Multimodal Video Understanding Engine", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    model_provider: str = Field(default="openai", alias="MODEL_PROVIDER")
    transcription_provider_order: Optional[str] = Field(
        default=None,
        alias="TRANSCRIPTION_PROVIDER_ORDER",
    )
    frame_analysis_provider: Optional[str] = Field(default=None, alias="FRAME_ANALYSIS_PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")

    database_url: str = Field(default="sqlite:///data/video_ai.sqlite3", alias="DATABASE_URL")
    upload_dir: Path = Field(default=Path("data/uploads"), alias="UPLOAD_DIR")
    audio_dir: Path = Field(default=Path("data/audio"), alias="AUDIO_DIR")
    frame_dir: Path = Field(default=Path("data/frames"), alias="FRAME_DIR")

    frame_sample_seconds: int = Field(default=2, alias="FRAME_SAMPLE_SECONDS")
    max_upload_mb: int = Field(default=250, alias="MAX_UPLOAD_MB")
    allowed_video_extensions: str = Field(default="mp4,mov", alias="ALLOWED_VIDEO_EXTENSIONS")
    transcription_model: str = Field(default="whisper-1", alias="TRANSCRIPTION_MODEL")
    vision_model: str = Field(default="gpt-4.1-mini", alias="VISION_MODEL")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")
    cors_allowed_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.allowed_video_extensions.split(",")
            if extension.strip()
        }

    @property
    def active_model_provider(self) -> str:
        return self.model_provider.strip().lower()

    @property
    def active_transcription_providers(self) -> list[str]:
        return self._provider_list(self.transcription_provider_order) or [
            self.active_model_provider,
        ]

    @property
    def active_frame_analysis_provider(self) -> str:
        return (
            self.frame_analysis_provider.strip().lower()
            if self.frame_analysis_provider
            else self.active_model_provider
        )

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    def _provider_list(self, providers: Optional[str]) -> list[str]:
        if not providers:
            return []
        return [
            provider.strip().lower()
            for provider in providers.split(",")
            if provider.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_runtime_dirs(settings: Optional[Settings] = None) -> None:
    active_settings = settings or get_settings()
    for directory in (
        active_settings.upload_dir,
        active_settings.audio_dir,
        active_settings.frame_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
