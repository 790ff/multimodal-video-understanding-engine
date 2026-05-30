import { ApiError } from "./client";

const CONFIG_FAILURE_CODES = new Set([
  "model_provider_unsupported",
  "transcription_not_configured",
  "transcription_dependency_missing",
  "frame_analysis_not_configured",
  "frame_analysis_dependency_missing",
]);

const ANALYSIS_FAILURE_CODES = new Set([
  "video_analysis_failed",
  "processing_error",
  "audio_file_missing",
  "keyframe_file_missing",
  "frame_analysis_failed",
  "transcription_failed",
  "timeline_evidence_missing",
]);

export type UserFacingError = {
  title: string;
  message: string;
};

export function toUserFacingError(error: unknown): UserFacingError {
  if (error instanceof ApiError) {
    if (error.code === "backend_offline") {
      return {
        title: "Backend offline",
        message: "The local API is not reachable. Start the backend and check the API URL.",
      };
    }
    if (error.code === "unsupported_video_type") {
      return {
        title: "Unsupported file",
        message: "Use an MP4 or MOV video for this local MVP.",
      };
    }
    if (error.code === "video_not_analyzed") {
      return {
        title: "Not analyzed yet",
        message: "Run analysis before opening the timeline or asking questions.",
      };
    }
    if (error.code === "video_already_processing") {
      return {
        title: "Analysis in progress",
        message: "This video is already being analyzed. Keep this page open and refresh status.",
      };
    }
    if (CONFIG_FAILURE_CODES.has(error.code)) {
      return {
        title: "Provider configuration needed",
        message: "Set the required provider key or model configuration in the local environment.",
      };
    }
    if (ANALYSIS_FAILURE_CODES.has(error.code) || error.status >= 500) {
      return {
        title: "Analysis failed",
        message: "The backend marked analysis as failed without exposing internal details.",
      };
    }
    if (error.code === "empty_question") {
      return {
        title: "Question required",
        message: "Enter a question before asking the video.",
      };
    }
    if (error.code === "video_not_found") {
      return {
        title: "Video not found",
        message: "The selected video record is not available in the local backend.",
      };
    }
  }

  return {
    title: "Request failed",
    message: "The operation could not be completed. Try again after checking the local app state.",
  };
}
