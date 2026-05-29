from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceLinkData:
    evidence_type: str
    evidence_id: str


@dataclass(frozen=True)
class TimelineEventData:
    start_time: float
    end_time: float
    summary: str
    evidence: tuple[EvidenceLinkData, ...]
