from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.db.models import KeyframeModel, SceneModel, TranscriptSegmentModel, VideoModel
from app.domain.errors import ProcessingAppError
from app.domain.timeline import EvidenceLinkData, TimelineEventData
from app.repositories.video_repository import VideoRepository


@dataclass(frozen=True)
class TimelineBuildResult:
    events: int


@dataclass(frozen=True)
class TimelineWindow:
    start_time: float
    end_time: float
    scene: SceneModel | None = None


class TimelineSynthesizer(Protocol):
    def synthesize(
        self,
        *,
        window: TimelineWindow,
        transcript_segments: list[TranscriptSegmentModel],
        keyframes: list[KeyframeModel],
    ) -> str:
        pass


class EvidenceTimelineSynthesizer:
    def synthesize(
        self,
        *,
        window: TimelineWindow,
        transcript_segments: list[TranscriptSegmentModel],
        keyframes: list[KeyframeModel],
    ) -> str:
        speech = self._compact(" ".join(segment.text for segment in transcript_segments))
        visual = self._compact(
            " ".join(
                keyframe.visual_summary.strip()
                for keyframe in keyframes
                if keyframe.visual_summary and keyframe.visual_summary.strip()
            )
        )

        parts = []
        if speech:
            parts.append(f"Speech: {speech}")
        if visual:
            parts.append(f"Visual: {visual}")
        if parts:
            return " ".join(parts)
        return f"Scene from {window.start_time:.3f}s to {window.end_time:.3f}s."

    def _compact(self, text: str, *, limit: int = 320) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 3].rstrip()}..."


class TimelineBuilder:
    def __init__(self, *, synthesizer: TimelineSynthesizer | None = None) -> None:
        self.synthesizer = synthesizer or EvidenceTimelineSynthesizer()

    def build(self, *, video: VideoModel, repository: VideoRepository) -> TimelineBuildResult:
        scenes = repository.list_scenes(video)
        keyframes = repository.list_keyframes(video)
        transcript_segments = repository.list_transcript_segments(video)

        if not keyframes and not transcript_segments:
            raise ProcessingAppError(
                "Timeline could not be built because no usable evidence was found.",
                code="timeline_no_evidence",
            )

        windows = self._windows_from_scenes(scenes) or self._fallback_windows(
            keyframes=keyframes,
            transcript_segments=transcript_segments,
        )
        events = [
            self._build_event(
                window=window,
                keyframes=keyframes,
                transcript_segments=transcript_segments,
            )
            for window in windows
        ]
        stored_events = repository.replace_timeline_events(video, events)
        return TimelineBuildResult(events=len(stored_events))

    def _windows_from_scenes(self, scenes: list[SceneModel]) -> list[TimelineWindow]:
        return [
            TimelineWindow(
                start_time=round(scene.start_time, 3),
                end_time=round(scene.end_time, 3),
                scene=scene,
            )
            for scene in scenes
        ]

    def _fallback_windows(
        self,
        *,
        keyframes: list[KeyframeModel],
        transcript_segments: list[TranscriptSegmentModel],
    ) -> list[TimelineWindow]:
        starts = [segment.start_time for segment in transcript_segments]
        starts.extend(keyframe.time for keyframe in keyframes)
        ends = [segment.end_time for segment in transcript_segments]
        ends.extend(keyframe.time for keyframe in keyframes)
        if not starts or not ends:
            return []
        start_time = round(min(starts), 3)
        end_time = round(max(ends), 3)
        return [TimelineWindow(start_time=start_time, end_time=max(start_time, end_time))]

    def _build_event(
        self,
        *,
        window: TimelineWindow,
        keyframes: list[KeyframeModel],
        transcript_segments: list[TranscriptSegmentModel],
    ) -> TimelineEventData:
        window_transcripts = [
            segment for segment in transcript_segments if self._overlaps(segment, window)
        ]
        window_keyframes = [
            keyframe for keyframe in keyframes if self._contains_keyframe(keyframe, window)
        ]
        summary = self.synthesizer.synthesize(
            window=window,
            transcript_segments=window_transcripts,
            keyframes=window_keyframes,
        )
        evidence = self._evidence_for_window(
            window=window,
            transcript_segments=window_transcripts,
            keyframes=window_keyframes,
        )
        return TimelineEventData(
            start_time=window.start_time,
            end_time=window.end_time,
            summary=summary,
            evidence=tuple(evidence),
        )

    def _evidence_for_window(
        self,
        *,
        window: TimelineWindow,
        transcript_segments: list[TranscriptSegmentModel],
        keyframes: list[KeyframeModel],
    ) -> list[EvidenceLinkData]:
        evidence = []
        if window.scene is not None:
            evidence.append(EvidenceLinkData(evidence_type="scene", evidence_id=window.scene.id))
        evidence.extend(
            EvidenceLinkData(evidence_type="transcript", evidence_id=segment.id)
            for segment in transcript_segments
        )
        evidence.extend(
            EvidenceLinkData(evidence_type="frame", evidence_id=keyframe.id)
            for keyframe in keyframes
        )
        return evidence

    def _overlaps(self, segment: TranscriptSegmentModel, window: TimelineWindow) -> bool:
        if segment.start_time == segment.end_time:
            return window.start_time <= segment.start_time <= window.end_time
        return segment.start_time < window.end_time and segment.end_time > window.start_time

    def _contains_keyframe(self, keyframe: KeyframeModel, window: TimelineWindow) -> bool:
        return window.start_time <= keyframe.time <= window.end_time
