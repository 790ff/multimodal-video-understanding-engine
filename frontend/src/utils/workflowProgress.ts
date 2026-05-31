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
  label: "Waiting for a video",
  detail: "Choose an MP4 or MOV file.",
};

export function uploadProgressFromFile(file: File): UploadProgressState {
  return {
    phase: "ready",
    percent: 0,
    label: "Ready to upload",
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
    label: progress.percent === null ? "Uploading video" : `Uploading ${progress.percent}%`,
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
      label: "Waiting for upload",
      detail: "Upload or load a video to begin.",
      steps: [
        { id: "upload", label: "Upload", status: "pending" },
        { id: "analysis", label: "Analysis", status: "pending" },
        { id: "timeline", label: "Timeline", status: "pending" },
      ],
    };
  }

  if (status === "failed") {
    return {
      phase: "failed",
      percent: 100,
      label: "Analysis failed",
      detail: "Retry analysis after checking local configuration.",
      steps: [
        { id: "upload", label: "Upload", status: "complete" },
        { id: "analysis", label: "Analysis", status: "failed" },
        { id: "timeline", label: "Timeline", status: "pending" },
      ],
    };
  }

  if (status === "analyzed") {
    return {
      phase: hasTimeline ? "complete" : "timeline",
      percent: hasTimeline ? 100 : null,
      label: hasTimeline ? "Analysis complete" : "Loading timeline",
      detail: hasTimeline ? "Timeline and question answering are ready." : "Fetching stored events.",
      steps: [
        { id: "upload", label: "Upload", status: "complete" },
        { id: "analysis", label: "Analysis", status: "complete" },
        {
          id: "timeline",
          label: "Timeline",
          status: hasTimeline ? "complete" : loadingTimeline ? "active" : "pending",
        },
      ],
    };
  }

  if (status === "processing" || analyzing) {
    return {
      phase: "processing",
      percent: null,
      label: "Analysis running",
      detail: "Status refreshes while the backend processes the video.",
      steps: [
        { id: "upload", label: "Upload", status: "complete" },
        { id: "analysis", label: "Analysis", status: "active" },
        { id: "timeline", label: "Timeline", status: "pending" },
      ],
    };
  }

  return {
    phase: "ready",
    percent: 34,
    label: "Ready for analysis",
    detail: "Start analysis to build transcript, frames, scenes, and timeline.",
    steps: [
      { id: "upload", label: "Upload", status: "complete" },
      { id: "analysis", label: "Analysis", status: "active" },
      { id: "timeline", label: "Timeline", status: "pending" },
    ],
  };
}
