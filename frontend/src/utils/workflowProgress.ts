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
  label: "No video yet",
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
    label: progress.percent === null ? "Adding video" : `Adding ${progress.percent}%`,
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
      label: "Waiting for video",
      detail: "Add a video to start a review.",
      steps: [
        { id: "upload", label: "Video", status: "pending" },
        { id: "analysis", label: "Review", status: "pending" },
        { id: "timeline", label: "Ready", status: "pending" },
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
        { id: "upload", label: "Video", status: "complete" },
        { id: "analysis", label: "Review", status: "failed" },
        { id: "timeline", label: "Ready", status: "pending" },
      ],
    };
  }

  if (status === "analyzed") {
    return {
      phase: hasTimeline ? "complete" : "timeline",
      percent: hasTimeline ? 100 : null,
      label: hasTimeline ? "Review ready" : "Loading notes",
      detail: hasTimeline ? "Notes and questions are ready." : "Getting saved moments.",
      steps: [
        { id: "upload", label: "Video", status: "complete" },
        { id: "analysis", label: "Review", status: "complete" },
        {
          id: "timeline",
          label: "Ready",
          status: hasTimeline ? "complete" : loadingTimeline ? "active" : "pending",
        },
      ],
    };
  }

  if (status === "processing" || analyzing) {
    return {
      phase: "processing",
      percent: null,
      label: "Reviewing video",
      detail: "This can take a moment for longer clips.",
      steps: [
        { id: "upload", label: "Video", status: "complete" },
        { id: "analysis", label: "Review", status: "active" },
        { id: "timeline", label: "Ready", status: "pending" },
      ],
    };
  }

  return {
    phase: "ready",
    percent: 34,
    label: "Ready to review",
    detail: "Start the review when you are ready.",
    steps: [
      { id: "upload", label: "Video", status: "complete" },
      { id: "analysis", label: "Review", status: "active" },
      { id: "timeline", label: "Ready", status: "pending" },
    ],
  };
}
