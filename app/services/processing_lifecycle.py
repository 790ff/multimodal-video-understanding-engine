from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ProcessingStage(str, Enum):
    PREPARING = "preparing"
    AUDIO_EXTRACTION = "audio_extraction"
    FRAME_EXTRACTION = "frame_extraction"
    SCENE_DETECTION = "scene_detection"
    TRANSCRIPTION = "transcription"
    FRAME_ANALYSIS = "frame_analysis"
    TIMELINE_BUILDING = "timeline_building"
    STORAGE = "storage"


@dataclass
class AnalysisJob:
    video_id: str
    video_path: Path
    audio_path: Path
    frame_dir: Path
    stage: ProcessingStage = ProcessingStage.PREPARING

    def enter(self, stage: ProcessingStage) -> None:
        self.stage = stage


STAGE_ERROR_CODES = {
    ProcessingStage.PREPARING: "processing_storage_failed",
    ProcessingStage.AUDIO_EXTRACTION: "audio_extraction_failed",
    ProcessingStage.FRAME_EXTRACTION: "frame_extraction_failed",
    ProcessingStage.SCENE_DETECTION: "scene_detection_failed",
    ProcessingStage.TRANSCRIPTION: "transcription_failed",
    ProcessingStage.FRAME_ANALYSIS: "frame_analysis_failed",
    ProcessingStage.TIMELINE_BUILDING: "timeline_generation_failed",
    ProcessingStage.STORAGE: "processing_storage_failed",
}
