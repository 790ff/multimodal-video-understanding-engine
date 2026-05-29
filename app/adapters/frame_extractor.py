from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from app.domain.errors import ProcessingAppError


@dataclass(frozen=True)
class ExtractedFrame:
    time: float
    path: Path


class FrameExtractor:
    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        sample_seconds: int,
    ) -> list[ExtractedFrame]:
        if sample_seconds <= 0:
            raise ProcessingAppError(
                "Frame sample interval must be greater than zero.",
                code="invalid_frame_sample_interval",
            )

        try:
            import cv2
        except ImportError as exc:
            raise ProcessingAppError(
                "Could not extract keyframes from video.",
                code="frame_extraction_unavailable",
            ) from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ProcessingAppError(
                "Could not extract keyframes from video.",
                code="frame_extraction_failed",
            )

        try:
            fps = self._positive_float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            frames = (
                self._extract_by_frame_index(
                    capture=capture,
                    output_dir=output_dir,
                    sample_seconds=sample_seconds,
                    fps=fps,
                    frame_count=frame_count,
                    cv2=cv2,
                )
                if fps > 0 and frame_count > 0
                else self._extract_by_scan(
                    capture=capture,
                    output_dir=output_dir,
                    sample_seconds=sample_seconds,
                    fps=fps,
                    cv2=cv2,
                )
            )
        finally:
            capture.release()

        if not frames:
            raise ProcessingAppError(
                "Could not extract keyframes from video.",
                code="frame_extraction_failed",
            )
        return frames

    def _extract_by_frame_index(
        self,
        *,
        capture: object,
        output_dir: Path,
        sample_seconds: int,
        fps: float,
        frame_count: int,
        cv2: object,
    ) -> list[ExtractedFrame]:
        interval_frames = max(1, round(fps * sample_seconds))
        frames: list[ExtractedFrame] = []

        for frame_index in range(0, frame_count, interval_frames):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                continue
            frames.append(
                self._write_frame(
                    frame=frame,
                    output_dir=output_dir,
                    sequence=len(frames) + 1,
                    timestamp=round(frame_index / fps, 3),
                    cv2=cv2,
                )
            )

        return frames

    def _extract_by_scan(
        self,
        *,
        capture: object,
        output_dir: Path,
        sample_seconds: int,
        fps: float,
        cv2: object,
    ) -> list[ExtractedFrame]:
        frames: list[ExtractedFrame] = []
        frame_index = 0
        next_sample_time = 0.0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            timestamp = self._timestamp_for_frame(
                capture=capture,
                frame_index=frame_index,
                fps=fps,
                cv2=cv2,
            )
            if timestamp + 0.001 >= next_sample_time:
                frames.append(
                    self._write_frame(
                        frame=frame,
                        output_dir=output_dir,
                        sequence=len(frames) + 1,
                        timestamp=round(timestamp, 3),
                        cv2=cv2,
                    )
                )
                next_sample_time += sample_seconds
            frame_index += 1

        return frames

    def _write_frame(
        self,
        *,
        frame: object,
        output_dir: Path,
        sequence: int,
        timestamp: float,
        cv2: object,
    ) -> ExtractedFrame:
        frame_path = output_dir / f"frame_{sequence:06d}.jpg"
        if not cv2.imwrite(str(frame_path), frame):
            raise ProcessingAppError(
                "Could not extract keyframes from video.",
                code="frame_write_failed",
            )
        return ExtractedFrame(time=timestamp, path=frame_path)

    def _timestamp_for_frame(
        self,
        *,
        capture: object,
        frame_index: int,
        fps: float,
        cv2: object,
    ) -> float:
        if fps > 0:
            return frame_index / fps

        timestamp_ms = self._positive_float(capture.get(cv2.CAP_PROP_POS_MSEC))
        return timestamp_ms / 1000 if timestamp_ms > 0 else 0.0

    def _positive_float(self, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return number if isfinite(number) and number > 0 else 0.0
