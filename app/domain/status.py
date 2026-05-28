from __future__ import annotations

from enum import Enum


class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"
