from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.adapters.audio_extractor import AudioExtractor
from app.adapters.frame_analyzer import FrameAnalysisResult, FrameAnalyzer, GeminiFrameAnalyzer
from app.adapters.frame_extractor import ExtractedFrame, FrameExtractor
from app.adapters.provider_factory import (
    FallbackTranscriber,
    create_frame_analyzer,
    create_transcriber,
)
from app.adapters.scene_detector import DetectedScene, SceneDetector
from app.adapters.transcriber import GeminiTranscriber, Transcriber, TranscriptSegmentData
from app.config import Settings, get_settings
from app.domain.errors import ConflictAppError, NotFoundAppError, ProcessingAppError
from app.domain.status import VideoStatus
from app.repositories.video_repository import VideoRepository

SAFE_ANALYSIS_ERROR_MESSAGE = "Video analysis failed."


@dataclass(frozen=True)
class AnalysisResult:
    video_id: str
    status: VideoStatus
    transcript_segments: int = 0
    keyframes: int = 0
    scenes: int = 0
    timeline_events: int = 0


class VideoProcessor:
    def __init__(
        self,
        *,
        audio_extractor: Optional[AudioExtractor] = None,
        frame_extractor: Optional[FrameExtractor] = None,
        scene_detector: Optional[SceneDetector] = None,
        transcriber: Optional[Transcriber | GeminiTranscriber | FallbackTranscriber] = None,
        frame_analyzer: Optional[FrameAnalyzer | GeminiFrameAnalyzer] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.audio_extractor = audio_extractor or AudioExtractor()
        self.frame_extractor = frame_extractor or FrameExtractor()
        self.scene_detector = scene_detector or SceneDetector()
        self.transcriber = transcriber or create_transcriber(self.settings)
        self.frame_analyzer = frame_analyzer or create_frame_analyzer(self.settings)

    def analyze(self, video_id: str, repository: VideoRepository) -> AnalysisResult:
        video = repository.get(video_id)
        if video is None:
            raise NotFoundAppError(
                "Video was not found.",
                code="video_not_found",
            )
        if VideoStatus(video.status) == VideoStatus.PROCESSING:
            raise ConflictAppError(
                "Video is already processing.",
                code="video_already_processing",
            )

        video_path = Path(video.stored_path)
        audio_path = self._audio_output_path(video_id)
        frame_dir = self._frame_output_dir(video_id)

        try:
            repository.set_status(video, VideoStatus.PROCESSING, error_message=None)
            repository.session.commit()

            self._ensure_output_dirs(audio_path=audio_path, frame_dir=frame_dir)
            self._ensure_audio(video_path=video_path, audio_path=audio_path)

            keyframes = self._load_reusable_keyframes(video=video, repository=repository)
            if not keyframes:
                keyframes = self._extract_keyframes(
                    video=video,
                    video_path=video_path,
                    frame_dir=frame_dir,
                    repository=repository,
                )

            scenes = self._load_reusable_scenes(video=video, repository=repository)
            if not scenes:
                scenes = self._detect_scenes_with_fallback(
                    video_path=video_path,
                    keyframes=keyframes,
                )
                repository.replace_scenes(
                    video,
                    [(scene.start_time, scene.end_time) for scene in scenes],
                )

            transcript_segments = self._transcribe_audio(audio_path)
            repository.replace_transcript_segments(
                video,
                [
                    (segment.start_time, segment.end_time, segment.text)
                    for segment in transcript_segments
                ],
            )

            frame_summaries = self.frame_analyzer.analyze(
                [keyframe.path for keyframe in keyframes],
            )
            self._store_visual_summaries(
                video,
                keyframes=keyframes,
                frame_summaries=frame_summaries,
                repository=repository,
            )
            repository.set_status(video, VideoStatus.ANALYZED, error_message=None)
            repository.session.commit()

            return AnalysisResult(
                video_id=video.id,
                status=VideoStatus.ANALYZED,
                transcript_segments=len(transcript_segments),
                keyframes=len(keyframes),
                scenes=len(scenes),
                timeline_events=0,
            )
        except Exception as exc:
            self._mark_failed(video_id=video_id, repository=repository)
            raise ProcessingAppError(
                SAFE_ANALYSIS_ERROR_MESSAGE,
                code=self._safe_processing_code(exc),
            ) from exc

    def _audio_output_path(self, video_id: str) -> Path:
        return self.settings.audio_dir / video_id / "audio.wav"

    def _frame_output_dir(self, video_id: str) -> Path:
        return self.settings.frame_dir / video_id

    def _ensure_output_dirs(self, *, audio_path: Path, frame_dir: Path) -> None:
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        frame_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_audio(self, *, video_path: Path, audio_path: Path) -> None:
        if self._is_nonempty_file(audio_path):
            return
        self.audio_extractor.extract(video_path=video_path, output_path=audio_path)

    def _load_reusable_keyframes(
        self,
        *,
        video: object,
        repository: VideoRepository,
    ) -> list[ExtractedFrame]:
        existing_keyframes = repository.list_keyframes(video)
        if not existing_keyframes:
            return []
        if all(self._is_nonempty_file(Path(keyframe.path)) for keyframe in existing_keyframes):
            return [
                ExtractedFrame(time=keyframe.time, path=Path(keyframe.path))
                for keyframe in existing_keyframes
            ]

        repository.replace_keyframes(video, [])
        return []

    def _extract_keyframes(
        self,
        *,
        video: object,
        video_path: Path,
        frame_dir: Path,
        repository: VideoRepository,
    ) -> list[ExtractedFrame]:
        shutil.rmtree(frame_dir, ignore_errors=True)
        frame_dir.mkdir(parents=True, exist_ok=True)
        keyframes = self.frame_extractor.extract(
            video_path=video_path,
            output_dir=frame_dir,
            sample_seconds=self.settings.frame_sample_seconds,
        )
        repository.replace_keyframes(
            video,
            [(keyframe.time, str(keyframe.path)) for keyframe in keyframes],
        )
        return keyframes

    def _load_reusable_scenes(
        self,
        *,
        video: object,
        repository: VideoRepository,
    ) -> list[DetectedScene]:
        return [
            DetectedScene(start_time=scene.start_time, end_time=scene.end_time)
            for scene in repository.list_scenes(video)
        ]

    def _transcribe_audio(self, audio_path: Path) -> list[TranscriptSegmentData]:
        transcript_segments = []
        for segment in self.transcriber.transcribe(audio_path):
            text = segment.text.strip()
            if not text:
                continue
            if segment.start_time > segment.end_time:
                raise ProcessingAppError(
                    "Transcription returned an invalid timestamp range.",
                    code="transcription_invalid_timestamp",
                )
            transcript_segments.append(
                TranscriptSegmentData(
                    start_time=round(segment.start_time, 3),
                    end_time=round(segment.end_time, 3),
                    text=text,
                )
            )
        return transcript_segments

    def _store_visual_summaries(
        self,
        video: object,
        *,
        keyframes: list[ExtractedFrame],
        frame_summaries: list[FrameAnalysisResult],
        repository: VideoRepository,
    ) -> None:
        expected_paths = [str(keyframe.path) for keyframe in keyframes]
        summary_by_path = {
            str(result.frame_path): result.visual_summary.strip()
            for result in frame_summaries
            if result.visual_summary.strip()
        }
        missing_paths = [path for path in expected_paths if not summary_by_path.get(path)]
        if missing_paths:
            raise ProcessingAppError(
                "Frame analysis returned incomplete results.",
                code="frame_analysis_incomplete",
            )

        updated = repository.update_keyframe_visual_summaries(video, summary_by_path.items())
        if updated != len(expected_paths):
            raise ProcessingAppError(
                "Frame summaries could not be saved.",
                code="frame_summary_storage_failed",
            )

    def _is_nonempty_file(self, path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0

    def _detect_scenes_with_fallback(
        self,
        *,
        video_path: Path,
        keyframes: list[ExtractedFrame],
    ) -> list[DetectedScene]:
        try:
            scenes = self.scene_detector.detect(video_path=video_path)
        except Exception:
            return self._fallback_scenes_from_keyframes(keyframes)

        return scenes or self._fallback_scenes_from_keyframes(keyframes)

    def _fallback_scenes_from_keyframes(
        self,
        keyframes: list[ExtractedFrame],
    ) -> list[DetectedScene]:
        scenes: list[DetectedScene] = []
        for index, keyframe in enumerate(keyframes):
            start_time = round(keyframe.time, 3)
            if index + 1 < len(keyframes):
                end_time = round(keyframes[index + 1].time, 3)
            else:
                end_time = round(start_time + self.settings.frame_sample_seconds, 3)
            scenes.append(
                DetectedScene(
                    start_time=start_time,
                    end_time=max(start_time, end_time),
                )
            )
        return scenes

    def _mark_failed(self, *, video_id: str, repository: VideoRepository) -> None:
        repository.session.rollback()
        video = repository.get(video_id)
        if video is None:
            return
        repository.set_status(
            video,
            VideoStatus.FAILED,
            error_message=SAFE_ANALYSIS_ERROR_MESSAGE,
        )
        repository.session.commit()

    def _safe_processing_code(self, exc: Exception) -> str:
        if isinstance(exc, ProcessingAppError):
            return exc.code
        return "video_analysis_failed"
