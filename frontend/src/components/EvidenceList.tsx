import { Film, MessageSquareText, PanelTop, Rows3 } from "lucide-react";

import type { TimelineEvidence } from "../api/types";
import { fileBasename } from "../utils/file";
import { formatRange, formatSeconds } from "../utils/time";

type EvidenceListProps = {
  evidence: TimelineEvidence[];
  compact?: boolean;
};

export function EvidenceList({ evidence, compact = false }: EvidenceListProps) {
  if (evidence.length === 0) {
    return <span className="evidence-empty">No timestamped evidence</span>;
  }

  return (
    <ul className={compact ? "evidence-list evidence-list--compact" : "evidence-list"}>
      {evidence.map((item, index) => (
        <li key={`${item.type}-${index}`}>
          <EvidenceIcon type={item.type} />
          <span>{labelForEvidence(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function EvidenceIcon({ type }: { type: string }) {
  const Icon =
    type === "frame"
      ? Film
      : type === "transcript"
        ? MessageSquareText
        : type === "scene"
          ? Rows3
          : PanelTop;

  return <Icon size={15} aria-hidden="true" />;
}

function labelForEvidence(item: TimelineEvidence): string {
  if (item.type === "frame") {
    const pathLabel = fileBasename(item.path);
    return pathLabel
      ? `Frame ${formatSeconds(item.time)} - ${pathLabel}`
      : `Frame ${formatSeconds(item.time)}`;
  }
  if (item.start_time !== undefined || item.end_time !== undefined) {
    return `${item.type} ${formatRange(item.start_time, item.end_time)}`;
  }
  return item.type;
}
