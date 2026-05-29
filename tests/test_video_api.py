from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.audio_extractor import AudioExtractionResult
from app.adapters.frame_analyzer import FrameAnalysisResult
from app.adapters.frame_extractor import ExtractedFrame
from app.adapters.scene_detector import DetectedScene
from app.adapters.transcriber import TranscriptSegmentData
from app.api.videos import get_question_answerer, get_video_processor
from app.config import get_settings
from app.main import create_app
from app.services.question_answerer import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    QuestionAnswerer,
    RetrievedEvidenceContext,
)
from app.services.video_processor import VideoProcessor


class FakeAudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        assert video_path.exists()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake wav bytes")
        return AudioExtractionResult(audio_path=output_path)


class FakeFrameExtractor:
    def __init__(self) -> None:
        self.sample_seconds: int | None = None

    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        sample_seconds: int,
    ) -> list[ExtractedFrame]:
        assert video_path.exists()
        self.sample_seconds = sample_seconds
        output_dir.mkdir(parents=True, exist_ok=True)

        frames = []
        for sequence, timestamp in enumerate((0.0, 3.0), start=1):
            frame_path = output_dir / f"frame_{sequence:06d}.jpg"
            frame_path.write_bytes(b"fake jpg bytes")
            frames.append(ExtractedFrame(time=timestamp, path=frame_path))
        return frames


class FailingFrameExtractor:
    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        sample_seconds: int,
    ) -> list[ExtractedFrame]:
        raise RuntimeError("frame extraction should have reused existing metadata")


class FakeSceneDetector:
    def detect(self, video_path: Path) -> list[DetectedScene]:
        assert video_path.exists()
        return [
            DetectedScene(start_time=0.0, end_time=2.5),
            DetectedScene(start_time=2.5, end_time=5.0),
        ]


class FailingSceneDetector:
    def detect(self, video_path: Path) -> list[DetectedScene]:
        assert video_path.exists()
        raise RuntimeError("PySceneDetect could not decode scene boundaries")


class FailingAudioExtractor:
    def extract(self, video_path: Path, output_path: Path) -> AudioExtractionResult:
        raise RuntimeError("secret path /tmp/.env OPENAI_API_KEY=abc123")


class FakeTranscriber:
    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        assert audio_path.read_bytes() == b"fake wav bytes"
        return [
            TranscriptSegmentData(start_time=0.0, end_time=1.5, text="Intro narration"),
            TranscriptSegmentData(start_time=1.5, end_time=3.0, text="Action narration"),
        ]


class FakeUntimedTranscriber:
    def transcribe(self, audio_path: Path) -> list[TranscriptSegmentData]:
        assert audio_path.read_bytes() == b"fake wav bytes"
        return [
            TranscriptSegmentData(start_time=0.0, end_time=0.0, text="Untimed narration"),
        ]


class FakeFrameAnalyzer:
    def analyze(self, frame_paths: list[Path]) -> list[FrameAnalysisResult]:
        return [
            FrameAnalysisResult(
                frame_path=frame_path,
                visual_summary=f"Visual summary for {frame_path.name}",
            )
            for frame_path in frame_paths
        ]


class FakeAnswerProvider:
    def __init__(self, answer: str = "Answer from stored evidence.") -> None:
        self.answer = answer
        self.questions: list[str] = []
        self.contexts: list[RetrievedEvidenceContext] = []

    def generate(self, *, question: str, context: RetrievedEvidenceContext) -> str:
        self.questions.append(question)
        self.contexts.append(context)
        return self.answer


class FailingAnswerProvider:
    def generate(self, *, question: str, context: RetrievedEvidenceContext) -> str:
        raise AssertionError("Answer provider should not run without stored evidence.")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test_video_ai.sqlite3'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUDIO_DIR", str(tmp_path / "audio"))
    monkeypatch.setenv("FRAME_DIR", str(tmp_path / "frames"))
    monkeypatch.setenv("FRAME_SAMPLE_SECONDS", "3")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    test_client.app.dependency_overrides.clear()
    get_settings.cache_clear()


def _analyze_video_with_fakes(client: TestClient) -> str:
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]
    analyze_response = client.post(f"/videos/{video_id}/analyze")
    assert analyze_response.status_code == 200
    return video_id


def test_upload_video_creates_metadata_and_stores_original_file(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "demo.mp4"
    assert body["status"] == "uploaded"
    assert body["video_id"]

    stored_file = tmp_path / "uploads" / body["video_id"] / "original.mp4"
    assert stored_file.read_bytes() == b"fake mp4 bytes"

    db_path = tmp_path / "test_video_ai.sqlite3"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select id, original_filename, stored_path, status, error_message from videos"
        ).fetchone()

    assert row == (
        body["video_id"],
        "demo.mp4",
        str(stored_file),
        "uploaded",
        None,
    )


def test_upload_video_accepts_mov(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("clip.MOV", b"fake mov bytes", "video/quicktime")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "clip.MOV"
    assert body["status"] == "uploaded"
    assert (tmp_path / "uploads" / body["video_id"] / "original.mov").exists()


def test_upload_video_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/videos/upload",
        files={"file": ("demo.avi", b"fake avi bytes", "video/x-msvideo")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "unsupported_video_type",
            "message": "Unsupported video file type.",
            "details": {
                "extension": "avi",
                "allowed_extensions": ["mov", "mp4"],
            },
        }
    }


def test_get_video_status_returns_current_status(client: TestClient) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.get(f"/videos/{video_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "status": "uploaded",
        "error_message": None,
    }


def test_get_video_status_returns_404_for_missing_video(client: TestClient) -> None:
    response = client.get("/videos/00000000-0000-0000-0000-000000000000/status")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_get_video_timeline_returns_404_for_missing_video(client: TestClient) -> None:
    response = client.get("/videos/00000000-0000-0000-0000-000000000000/timeline")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_get_video_timeline_returns_409_before_analysis(client: TestClient) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.get(f"/videos/{video_id}/timeline")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "video_not_analyzed",
            "message": "Video has not been analyzed.",
            "details": {},
        }
    }


def test_analyze_video_runs_preprocessing_and_persists_metadata(
    client: TestClient,
    tmp_path: Path,
) -> None:
    frame_extractor = FakeFrameExtractor()
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=frame_extractor,
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "status": "analyzed",
        "transcript_segments": 2,
        "keyframes": 2,
        "scenes": 2,
        "timeline_events": 2,
    }
    assert frame_extractor.sample_seconds == 3
    audio_path = tmp_path / "audio" / video_id / "audio.wav"
    assert audio_path.read_bytes() == b"fake wav bytes"
    assert (tmp_path / "frames" / video_id / "frame_000001.jpg").exists()
    assert (tmp_path / "frames" / video_id / "frame_000002.jpg").exists()

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        video_row = connection.execute(
            "select status, error_message from videos where id = ?",
            (video_id,),
        ).fetchone()
        keyframe_rows = connection.execute(
            "select time, path, visual_summary from keyframes where video_id = ? order by time",
            (video_id,),
        ).fetchall()
        scene_rows = connection.execute(
            "select start_time, end_time from scenes where video_id = ? order by start_time",
            (video_id,),
        ).fetchall()
        transcript_rows = connection.execute(
            """
            select start_time, end_time, text
            from transcript_segments
            where video_id = ?
            order by start_time
            """,
            (video_id,),
        ).fetchall()
        timeline_rows = connection.execute(
            """
            select start_time, end_time, summary
            from timeline_events
            where video_id = ?
            order by start_time
            """,
            (video_id,),
        ).fetchall()
        evidence_link_count = connection.execute(
            """
            select count(*)
            from evidence_links
            join timeline_events on timeline_events.id = evidence_links.timeline_event_id
            where timeline_events.video_id = ?
            """,
            (video_id,),
        ).fetchone()[0]

    assert video_row == ("analyzed", None)
    assert keyframe_rows == [
        (
            0.0,
            str(tmp_path / "frames" / video_id / "frame_000001.jpg"),
            "Visual summary for frame_000001.jpg",
        ),
        (
            3.0,
            str(tmp_path / "frames" / video_id / "frame_000002.jpg"),
            "Visual summary for frame_000002.jpg",
        ),
    ]
    assert scene_rows == [(0.0, 2.5), (2.5, 5.0)]
    assert transcript_rows == [
        (0.0, 1.5, "Intro narration"),
        (1.5, 3.0, "Action narration"),
    ]
    assert timeline_rows == [
        (
            0.0,
            2.5,
            "Speech: Intro narration Action narration Visual: Visual summary for frame_000001.jpg",
        ),
        (
            2.5,
            5.0,
            "Speech: Action narration Visual: Visual summary for frame_000002.jpg",
        ),
    ]
    assert evidence_link_count == 7


def test_get_video_timeline_returns_ordered_events_with_evidence(
    client: TestClient,
    tmp_path: Path,
) -> None:
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]
    analyze_response = client.post(f"/videos/{video_id}/analyze")
    assert analyze_response.status_code == 200

    response = client.get(f"/videos/{video_id}/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "events": [
            {
                "start_time": 0.0,
                "end_time": 2.5,
                "summary": (
                    "Speech: Intro narration Action narration Visual: "
                    "Visual summary for frame_000001.jpg"
                ),
                "evidence": [
                    {"type": "scene", "start_time": 0.0, "end_time": 2.5},
                    {"type": "transcript", "start_time": 0.0, "end_time": 1.5},
                    {"type": "transcript", "start_time": 1.5, "end_time": 3.0},
                    {
                        "type": "frame",
                        "time": 0.0,
                        "path": str(tmp_path / "frames" / video_id / "frame_000001.jpg"),
                    },
                ],
            },
            {
                "start_time": 2.5,
                "end_time": 5.0,
                "summary": "Speech: Action narration Visual: Visual summary for frame_000002.jpg",
                "evidence": [
                    {"type": "scene", "start_time": 2.5, "end_time": 5.0},
                    {"type": "transcript", "start_time": 1.5, "end_time": 3.0},
                    {
                        "type": "frame",
                        "time": 3.0,
                        "path": str(tmp_path / "frames" / video_id / "frame_000002.jpg"),
                    },
                ],
            },
        ],
    }


def test_ask_video_success_uses_stored_evidence(client: TestClient) -> None:
    answer_provider = FakeAnswerProvider("The intro is described by stored evidence.")
    client.app.dependency_overrides[get_question_answerer] = lambda: QuestionAnswerer(
        answer_provider=answer_provider,
    )
    video_id = _analyze_video_with_fakes(client)

    response = client.post(
        f"/videos/{video_id}/ask",
        json={"question": "What happens at the start?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "The intro is described by stored evidence."
    assert answer_provider.questions == ["What happens at the start?"]
    assert len(answer_provider.contexts) == 1
    assert "Intro narration" in answer_provider.contexts[0].context_text
    assert "Visual summary for frame_000001.jpg" in answer_provider.contexts[0].context_text


def test_ask_video_returns_404_for_missing_video(client: TestClient) -> None:
    client.app.dependency_overrides[get_question_answerer] = lambda: QuestionAnswerer(
        answer_provider=FakeAnswerProvider(),
    )

    response = client.post(
        "/videos/00000000-0000-0000-0000-000000000000/ask",
        json={"question": "What happened?"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_ask_video_returns_409_before_analysis(client: TestClient) -> None:
    client.app.dependency_overrides[get_question_answerer] = lambda: QuestionAnswerer(
        answer_provider=FakeAnswerProvider(),
    )
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(
        f"/videos/{video_id}/ask",
        json={"question": "What happened?"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "video_not_analyzed",
            "message": "Video has not been analyzed.",
            "details": {},
        }
    }


def test_ask_video_rejects_empty_question(client: TestClient) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/ask", json={"question": "   "})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "empty_question",
            "message": "Question must not be empty.",
            "details": {},
        }
    }


def test_ask_video_returns_safe_answer_for_insufficient_evidence(
    client: TestClient,
    tmp_path: Path,
) -> None:
    client.app.dependency_overrides[get_question_answerer] = lambda: QuestionAnswerer(
        answer_provider=FailingAnswerProvider(),
    )
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]
    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        connection.execute(
            "update videos set status = 'analyzed' where id = ?",
            (video_id,),
        )

    response = client.post(
        f"/videos/{video_id}/ask",
        json={"question": "What happened?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": INSUFFICIENT_EVIDENCE_ANSWER,
        "evidence": [],
    }


def test_ask_video_returns_timestamped_evidence_with_answer(
    client: TestClient,
    tmp_path: Path,
) -> None:
    client.app.dependency_overrides[get_question_answerer] = lambda: QuestionAnswerer(
        answer_provider=FakeAnswerProvider("Stored timeline answer."),
    )
    video_id = _analyze_video_with_fakes(client)

    response = client.post(
        f"/videos/{video_id}/ask",
        json={"question": "What evidence supports the answer?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Stored timeline answer."
    assert {"type": "timeline_event", "start_time": 0.0, "end_time": 2.5} in body[
        "evidence"
    ]
    assert {"type": "transcript", "start_time": 0.0, "end_time": 1.5} in body["evidence"]
    assert {
        "type": "frame",
        "time": 0.0,
        "path": str(tmp_path / "frames" / video_id / "frame_000001.jpg"),
    } in body["evidence"]


def test_analyze_video_keeps_untimed_transcript_in_timeline(
    client: TestClient,
) -> None:
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeUntimedTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]
    analyze_response = client.post(f"/videos/{video_id}/analyze")
    assert analyze_response.status_code == 200

    timeline_response = client.get(f"/videos/{video_id}/timeline")

    first_event = timeline_response.json()["events"][0]
    assert "Untimed narration" in first_event["summary"]
    assert {
        "type": "transcript",
        "start_time": 0.0,
        "end_time": 0.0,
    } in first_event["evidence"]


def test_analyze_video_uses_fallback_scenes_when_scene_detection_fails(
    client: TestClient,
    tmp_path: Path,
) -> None:
    processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FailingSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "status": "analyzed",
        "transcript_segments": 2,
        "keyframes": 2,
        "scenes": 2,
        "timeline_events": 2,
    }

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        video_row = connection.execute(
            "select status, error_message from videos where id = ?",
            (video_id,),
        ).fetchone()
        scene_rows = connection.execute(
            "select start_time, end_time from scenes where video_id = ? order by start_time",
            (video_id,),
        ).fetchall()

    assert video_row == ("analyzed", None)
    assert scene_rows == [(0.0, 3.0), (3.0, 6.0)]


def test_analyze_video_reuses_existing_preprocessing_outputs(
    client: TestClient,
    tmp_path: Path,
) -> None:
    first_processor = VideoProcessor(
        audio_extractor=FakeAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: first_processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    first_response = client.post(f"/videos/{video_id}/analyze")
    assert first_response.status_code == 200

    second_processor = VideoProcessor(
        audio_extractor=FailingAudioExtractor(),
        frame_extractor=FailingFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: second_processor

    second_response = client.post(f"/videos/{video_id}/analyze")

    assert second_response.status_code == 200
    assert second_response.json() == {
        "video_id": video_id,
        "status": "analyzed",
        "transcript_segments": 2,
        "keyframes": 2,
        "scenes": 2,
        "timeline_events": 2,
    }

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        transcript_count = connection.execute(
            "select count(*) from transcript_segments where video_id = ?",
            (video_id,),
        ).fetchone()[0]
        keyframe_count = connection.execute(
            "select count(*) from keyframes where video_id = ?",
            (video_id,),
        ).fetchone()[0]

    assert transcript_count == 2
    assert keyframe_count == 2


def test_analyze_video_returns_404_for_missing_video(client: TestClient) -> None:
    response = client.post("/videos/00000000-0000-0000-0000-000000000000/analyze")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "video_not_found",
            "message": "Video was not found.",
            "details": {},
        }
    }


def test_analyze_video_returns_409_when_already_processing(
    client: TestClient,
    tmp_path: Path,
) -> None:
    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    with sqlite3.connect(tmp_path / "test_video_ai.sqlite3") as connection:
        connection.execute(
            "update videos set status = 'processing' where id = ?",
            (video_id,),
        )

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "video_already_processing",
            "message": "Video is already processing.",
            "details": {},
        }
    }


def test_analyze_video_failure_marks_video_failed_with_safe_message(
    client: TestClient,
) -> None:
    processor = VideoProcessor(
        audio_extractor=FailingAudioExtractor(),
        frame_extractor=FakeFrameExtractor(),
        scene_detector=FakeSceneDetector(),
        transcriber=FakeTranscriber(),
        frame_analyzer=FakeFrameAnalyzer(),
        settings=get_settings(),
    )
    client.app.dependency_overrides[get_video_processor] = lambda: processor

    upload_response = client.post(
        "/videos/upload",
        files={"file": ("demo.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    video_id = upload_response.json()["video_id"]

    response = client.post(f"/videos/{video_id}/analyze")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "video_analysis_failed",
            "message": "Video analysis failed.",
            "details": {},
        }
    }

    status_response = client.get(f"/videos/{video_id}/status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "video_id": video_id,
        "status": "failed",
        "error_message": "Video analysis failed.",
    }
