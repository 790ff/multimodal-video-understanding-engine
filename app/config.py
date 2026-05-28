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

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    database_url: str = Field(default="sqlite:///data/video_ai.sqlite3", alias="DATABASE_URL")
    upload_dir: Path = Field(default=Path("data/uploads"), alias="UPLOAD_DIR")
    audio_dir: Path = Field(default=Path("data/audio"), alias="AUDIO_DIR")
    frame_dir: Path = Field(default=Path("data/frames"), alias="FRAME_DIR")

    frame_sample_seconds: int = Field(default=2, alias="FRAME_SAMPLE_SECONDS")
    max_upload_mb: int = Field(default=250, alias="MAX_UPLOAD_MB")
    allowed_video_extensions: str = Field(default="mp4,mov", alias="ALLOWED_VIDEO_EXTENSIONS")

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
