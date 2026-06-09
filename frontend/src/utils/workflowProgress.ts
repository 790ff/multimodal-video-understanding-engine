import type { UploadProgressEvent, VideoStatusValue } from "../api/types";
import { formatBytes } from "./file";

type UploadProgressPhase = "idle" | "ready" | "uploading" | "complete" | "failed";

export type UploadProgressState = {
  phase: UploadProgressPhase;
  percent: number | null;
  label: string;
  detail: string;
};

type ProgressStepState = "pending" | "active" | "complete" | "failed";

export type ProgressStep = {
  id: string;
  label: string;
  status: ProgressStepState;
};

export type AnalysisProgressState = {
  phase: "idle" | "ready" | "processing" | "timeline" | "complete" | "failed";
  percent: number | null;
  label: string;
  detail: string;
  steps: ProgressStep[];
};

export const idleUploadProgress: UploadProgressState = {
  phase: "idle",
  percent: null,
  label: "No clip yet",
  detail: "Choose an MP4 or MOV.",
};

export function uploadProgressFromFile(file: File): UploadProgressState {
  return {
    phase: "ready",
    percent: 0,
    label: "Ready to add",
    detail: `${file.name} - ${formatBytes(file.size)}`,
  };
}

export function uploadProgressFromEvent(
  progress: UploadProgressEvent,
  file: File,
): UploadProgressState {
  const uploaded = formatBytes(progress.loaded);
  const total = progress.total ? formatBytes(progress.total) : formatBytes(file.size);
  return {
    phase: "uploading",
    percent: progress.percent,
    label: progress.percent === null ? "Adding clip" : `Adding ${progress.percent}%`,
    detail: `${uploaded} of ${total}`,
  };
}

export function buildAnalysisProgress({
  hasVideo,
  status,
  analyzing,
  loadingTimeline,
  hasTimeline,
}: {
  hasVideo: boolean;
  status: VideoStatusValue | undefined;
  analyzing: boolean;
  loadingTimeline: boolean;
  hasTimeline: boolean;
}): AnalysisProgressState {
  if (!hasVideo) {
    return {
      phase: "idle",
      percent: 0,
      label: "Waiting for clip",
      detail: "Add a clip to start a review.",
      steps: [
        { id: "upload", label: "Clip", status: "pending" },
        { id: "analysis", label: "Review", status: "pending" },
        { id: "timeline", label: "Board", status: "pending" },
      ],
    };
  }

  if (status === "failed") {
    return {
      phase: "failed",
      percent: 100,
      label: "Review stopped",
      detail: "Try again after checking setup.",
      steps: [
        { id: "upload", label: "Clip", status: "complete" },
        { id: "analysis", label: "Review", status: "failed" },
        { id: "timeline", label: "Board", status: "pending" },
      ],
    };
  }

  if (status === "analyzed") {
    return {
      phase: hasTimeline ? "complete" : "timeline",
      percent: hasTimeline ? 100 : null,
      label: hasTimeline ? "Board ready" : "Loading board",
      detail: hasTimeline ? "Moments and questions are live." : "Getting saved moments.",
      steps: [
        { id: "upload", label: "Clip", status: "complete" },
        { id: "analysis", label: "Review", status: "complete" },
        {
          id: "timeline",
          label: "Board",
          status: hasTimeline ? "complete" : loadingTimeline ? "active" : "pending",
        },
      ],
    };
  }

  if (status === "processing" || analyzing) {
    return {
      phase: "processing",
      percent: null,
      label: "Building deck",
      detail: "This can take a moment for longer clips.",
      steps: [
        { id: "upload", label: "Clip", status: "complete" },
        { id: "analysis", label: "Review", status: "active" },
        { id: "timeline", label: "Board", status: "pending" },
      ],
    };
  }

  return {
    phase: "ready",
    percent: 34,
    label: "Deck armed",
    detail: "Start review when the clip is ready.",
    steps: [
      { id: "upload", label: "Clip", status: "complete" },
      { id: "analysis", label: "Review", status: "active" },
      { id: "timeline", label: "Board", status: "pending" },
    ],
  };
}
