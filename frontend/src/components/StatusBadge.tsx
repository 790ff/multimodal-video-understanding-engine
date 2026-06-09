import { AlertTriangle, CheckCircle2, Clock3, Loader2 } from "lucide-react";

import type { VideoStatusValue } from "../api/types";

type StatusBadgeProps = {
  status: VideoStatusValue | null | undefined;
};

const labels: Record<VideoStatusValue, string> = {
  uploaded: "Added",
  processing: "Reviewing",
  analyzed: "Ready",
  failed: "Stopped",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  if (!status) {
    return <span className="status-badge status-badge--empty">No clip</span>;
  }

  const Icon =
    status === "analyzed"
      ? CheckCircle2
      : status === "failed"
        ? AlertTriangle
        : status === "processing"
          ? Loader2
          : Clock3;

  return (
    <span className={`status-badge status-badge--${status}`}>
      <Icon size={15} aria-hidden="true" className={status === "processing" ? "spin" : ""} />
      {labels[status]}
    </span>
  );
}
