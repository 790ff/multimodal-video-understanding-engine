from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from app.db.models import (
    EvidenceLinkModel,
    KeyframeModel,
    SceneModel,
    TimelineEventModel,
    TranscriptSegmentModel,
    VideoModel,
)
from app.domain.errors import ConflictAppError, NotFoundAppError, ValidationAppError
from app.domain.status import VideoStatus
from app.repositories.video_repository import VideoRepository

INSUFFICIENT_EVIDENCE_ANSWER = (
    "I do not have enough stored evidence to answer that question."
)


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence_type: str
    source_id: str
    content: str | None = None
    time: float | None = None
    start_time: float | None = None
    end_time: float | None = None
    path: str | None = None

    @property
    def has_content(self) -> bool:
        return bool(self.content and self.content.strip())


@dataclass(frozen=True)
class RetrievedEvidenceContext:
    evidence: tuple[RetrievedEvidence, ...]
    context_text: str

    @property
    def has_answerable_evidence(self) -> bool:
        return any(item.has_content for item in self.evidence)


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    evidence: tuple[RetrievedEvidence, ...]


class AnswerProvider(Protocol):
    def generate(self, *, question: str, context: RetrievedEvidenceContext) -> str:
        pass


class EvidenceOnlyAnswerProvider:
    def generate(self, *, question: str, context: RetrievedEvidenceContext) -> str:
        if not context.has_answerable_evidence:
            return INSUFFICIENT_EVIDENCE_ANSWER

        preferred = [
            item
            for item in context.evidence
            if item.evidence_type == "timeline_event" and item.has_content
        ]
        content_items = preferred or [item for item in context.evidence if item.has_content]
        answer_parts = [self._compact(item.content or "") for item in content_items[:3]]
        answer = " ".join(part for part in answer_parts if part)
        if not answer:
            return INSUFFICIENT_EVIDENCE_ANSWER

        compact_question = self._compact(question, limit=80)
        return f"Based on stored evidence for '{compact_question}': {answer}"

    def _compact(self, text: str, *, limit: int = 320) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 3].rstrip()}..."


class EvidenceRetriever:
    def __init__(
        self,
        *,
        max_timeline_events: int = 8,
        max_transcript_segments: int = 16,
        max_keyframes: int = 12,
        max_evidence_items: int = 40,
        max_context_chars: int = 6000,
    ) -> None:
        self.max_timeline_events = max_timeline_events
        self.max_transcript_segments = max_transcript_segments
        self.max_keyframes = max_keyframes
        self.max_evidence_items = max_evidence_items
        self.max_context_chars = max_context_chars

    def retrieve(
        self,
        *,
        video: VideoModel,
        repository: VideoRepository,
    ) -> RetrievedEvidenceContext:
        timeline_events = repository.list_timeline_events(video)
        transcript_segments = repository.list_transcript_segments(video)
        keyframes = repository.list_keyframes(video)
        scenes = repository.list_scenes(video)

        transcripts_by_id = {segment.id: segment for segment in transcript_segments}
        keyframes_by_id = {keyframe.id: keyframe for keyframe in keyframes}
        scenes_by_id = {scene.id: scene for scene in scenes}

        evidence: list[RetrievedEvidence] = []
        seen: set[tuple[str, str]] = set()

        for event in timeline_events[: self.max_timeline_events]:
            self._append_timeline_event(evidence=evidence, seen=seen, event=event)
            sorted_links = sorted(
                event.evidence_links,
                key=lambda link: self._evidence_sort_key(
                    link,
                    transcripts=transcripts_by_id,
                    keyframes=keyframes_by_id,
                    scenes=scenes_by_id,
                ),
            )
            for link in sorted_links:
                self._append_linked_evidence(
                    evidence=evidence,
                    seen=seen,
                    link=link,
                    transcripts=transcripts_by_id,
                    keyframes=keyframes_by_id,
                    scenes=scenes_by_id,
                )
                if len(evidence) >= self.max_evidence_items:
                    break
            if len(evidence) >= self.max_evidence_items:
                break

        if not any(item.evidence_type == "transcript" for item in evidence):
            for segment in transcript_segments[: self.max_transcript_segments]:
                self._append_transcript_segment(evidence=evidence, seen=seen, segment=segment)
                if len(evidence) >= self.max_evidence_items:
                    break

        if not any(item.evidence_type == "frame" for item in evidence):
            for keyframe in keyframes[: self.max_keyframes]:
                self._append_keyframe(evidence=evidence, seen=seen, keyframe=keyframe)
                if len(evidence) >= self.max_evidence_items:
                    break

        limited_evidence = self._limit_context(evidence)
        return RetrievedEvidenceContext(
            evidence=tuple(limited_evidence),
            context_text=self._context_text(limited_evidence),
        )

    def _append_timeline_event(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        event: TimelineEventModel,
    ) -> None:
        self._append(
            evidence=evidence,
            seen=seen,
            item=RetrievedEvidence(
                evidence_type="timeline_event",
                source_id=event.id,
                start_time=event.start_time,
                end_time=event.end_time,
                content=event.summary,
            ),
        )

    def _append_linked_evidence(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        link: EvidenceLinkModel,
        transcripts: dict[str, TranscriptSegmentModel],
        keyframes: dict[str, KeyframeModel],
        scenes: dict[str, SceneModel],
    ) -> None:
        if link.evidence_type == "transcript" and link.evidence_id in transcripts:
            self._append_transcript_segment(
                evidence=evidence,
                seen=seen,
                segment=transcripts[link.evidence_id],
            )
        elif link.evidence_type == "frame" and link.evidence_id in keyframes:
            self._append_keyframe(
                evidence=evidence,
                seen=seen,
                keyframe=keyframes[link.evidence_id],
            )
        elif link.evidence_type == "scene" and link.evidence_id in scenes:
            self._append_scene(
                evidence=evidence,
                seen=seen,
                scene=scenes[link.evidence_id],
            )

    def _append_transcript_segment(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        segment: TranscriptSegmentModel,
    ) -> None:
        self._append(
            evidence=evidence,
            seen=seen,
            item=RetrievedEvidence(
                evidence_type="transcript",
                source_id=segment.id,
                start_time=segment.start_time,
                end_time=segment.end_time,
                content=segment.text,
            ),
        )

    def _append_keyframe(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        keyframe: KeyframeModel,
    ) -> None:
        self._append(
            evidence=evidence,
            seen=seen,
            item=RetrievedEvidence(
                evidence_type="frame",
                source_id=keyframe.id,
                time=keyframe.time,
                path=keyframe.path,
                content=keyframe.visual_summary,
            ),
        )

    def _append_scene(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        scene: SceneModel,
    ) -> None:
        self._append(
            evidence=evidence,
            seen=seen,
            item=RetrievedEvidence(
                evidence_type="scene",
                source_id=scene.id,
                start_time=scene.start_time,
                end_time=scene.end_time,
                content=scene.summary,
            ),
        )

    def _append(
        self,
        *,
        evidence: list[RetrievedEvidence],
        seen: set[tuple[str, str]],
        item: RetrievedEvidence,
    ) -> None:
        key = (item.evidence_type, item.source_id)
        if key in seen:
            return
        if len(evidence) >= self.max_evidence_items:
            return
        seen.add(key)
        evidence.append(item)

    def _limit_context(self, evidence: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
        limited = []
        remaining_chars = self.max_context_chars
        for item in evidence[: self.max_evidence_items]:
            content = item.content
            if content:
                normalized = " ".join(content.split())
                if remaining_chars <= 0:
                    content = None
                elif len(normalized) > remaining_chars:
                    content = self._compact(normalized, limit=remaining_chars)
                    remaining_chars = 0
                else:
                    content = normalized
                    remaining_chars -= len(content)
            limited.append(replace(item, content=content))
        return limited

    def _context_text(self, evidence: list[RetrievedEvidence]) -> str:
        lines = []
        for item in evidence:
            content = item.content or item.path or "timestamp reference"
            lines.append(f"{item.evidence_type} {self._timestamp_label(item)}: {content}")
        return "\n".join(lines)[: self.max_context_chars]

    def _timestamp_label(self, item: RetrievedEvidence) -> str:
        if item.time is not None:
            return f"at {item.time:.3f}s"
        if item.start_time is not None and item.end_time is not None:
            return f"from {item.start_time:.3f}s to {item.end_time:.3f}s"
        return "without timestamp"

    def _evidence_sort_key(
        self,
        link: EvidenceLinkModel,
        *,
        transcripts: dict[str, TranscriptSegmentModel],
        keyframes: dict[str, KeyframeModel],
        scenes: dict[str, SceneModel],
    ) -> tuple[int, float, float]:
        evidence_type = link.evidence_type
        evidence_id = link.evidence_id
        if evidence_type == "scene" and evidence_id in scenes:
            scene = scenes[evidence_id]
            return (0, scene.start_time, scene.end_time)
        if evidence_type == "transcript" and evidence_id in transcripts:
            segment = transcripts[evidence_id]
            return (1, segment.start_time, segment.end_time)
        if evidence_type == "frame" and evidence_id in keyframes:
            keyframe = keyframes[evidence_id]
            return (2, keyframe.time, keyframe.time)
        return (9, 0.0, 0.0)

    def _compact(self, text: str, *, limit: int) -> str:
        if limit <= 3:
            return text[:limit]
        if len(text) <= limit:
            return text
        return f"{text[: limit - 3].rstrip()}..."


class QuestionAnswerer:
    def __init__(
        self,
        *,
        retriever: EvidenceRetriever | None = None,
        answer_provider: AnswerProvider | None = None,
    ) -> None:
        self.retriever = retriever or EvidenceRetriever()
        self.answer_provider = answer_provider or EvidenceOnlyAnswerProvider()

    def answer(
        self,
        *,
        video_id: str,
        question: str,
        repository: VideoRepository,
    ) -> AnswerResult:
        normalized_question = " ".join(question.split())
        if not normalized_question:
            raise ValidationAppError(
                "Question must not be empty.",
                code="empty_question",
            )

        video = repository.get(video_id)
        if video is None:
            raise NotFoundAppError(
                "Video was not found.",
                code="video_not_found",
            )
        if VideoStatus(video.status) != VideoStatus.ANALYZED:
            raise ConflictAppError(
                "Video has not been analyzed.",
                code="video_not_analyzed",
            )

        context = self.retriever.retrieve(video=video, repository=repository)
        if not context.has_answerable_evidence:
            return AnswerResult(
                answer=INSUFFICIENT_EVIDENCE_ANSWER,
                evidence=context.evidence,
            )

        answer = self.answer_provider.generate(
            question=normalized_question,
            context=context,
        ).strip()
        if not answer:
            answer = INSUFFICIENT_EVIDENCE_ANSWER

        return AnswerResult(answer=answer, evidence=context.evidence)
