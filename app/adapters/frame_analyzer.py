from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrameAnalysisResult:
    frame_path: Path
    visual_summary: str


class FrameAnalyzer:
    def analyze(self, frame_paths: list[Path]) -> list[FrameAnalysisResult]:
        raise NotImplementedError("Vision frame analysis starts in M4.")
