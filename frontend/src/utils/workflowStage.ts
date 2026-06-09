import type { VideoStatusValue } from "../api/types";

export type WorkflowStage = "empty" | "uploaded" | "processing" | "analyzed" | "failed";

export function workflowStage({
  analyzed,
  analyzing,
  hasVideo,
  status,
}: {
  analyzed: boolean;
  analyzing: boolean;
  hasVideo: boolean;
  status: VideoStatusValue | undefined;
}): WorkflowStage {
  if (status === "failed") {
    return "failed";
  }
  if (status === "processing" || analyzing) {
    return "processing";
  }
  if (analyzed) {
    return "analyzed";
  }
  if (hasVideo) {
    return "uploaded";
  }
  return "empty";
}
