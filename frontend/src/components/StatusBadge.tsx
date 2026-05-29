import { AlertTriangle, CheckCircle2, Clock3, Loader2 } from "lucide-react";

import type { VideoStatusValue } from "../api/types";

type StatusBadgeProps = {
  status: VideoStatusValue | null | undefined;
};

const labels: Record<VideoStatusValue, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  analyzed: "Analyzed",
  failed: "Failed",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  if (!status) {
    return <span className="status-badge status-badge--empty">No video</span>;
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
