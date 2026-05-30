import { ApiError } from "./client";

const CONFIG_FAILURE_CODES = new Set([
  "model_provider_unsupported",
  "transcription_not_configured",
  "transcription_dependency_missing",
  "frame_analysis_not_configured",
  "frame_analysis_dependency_missing",
]);

const FFMPEG_FAILURE_CODES = new Set([
  "audio_extraction_failed",
  "frame_extraction_unavailable",
  "frame_extraction_failed",
]);

const ANALYSIS_FAILURE_CODES = new Set([
  "video_analysis_failed",
  "processing_error",
  "audio_file_missing",
  "keyframe_file_missing",
  "frame_analysis_failed",
  "frame_analysis_empty",
  "frame_analysis_incomplete",
  "frame_summary_storage_failed",
  "transcription_failed",
  "transcription_invalid_response",
  "transcription_invalid_timestamp",
  "scene_detection_unavailable",
  "scene_detection_failed",
  "timeline_no_evidence",
  "timeline_evidence_missing",
]);

export type UserFacingError = {
  title: string;
  message: string;
  recovery: string;
};

export function toUserFacingError(error: unknown): UserFacingError {
  if (error instanceof ApiError) {
    if (error.code === "backend_offline") {
      return {
        title: "Backend offline",
        message: "The local API is not reachable. Start the backend and check the API URL.",
        recovery: "Run the backend on the configured URL, then retry the last action.",
      };
    }
    if (error.code === "unsupported_video_type") {
      return {
        title: "Unsupported file",
        message: "Use an MP4 or MOV video for this local MVP.",
        recovery: "Choose a supported video file and upload again.",
      };
    }
    if (error.code === "upload_too_large" || error.code === "file_too_large") {
      return {
        title: "Video is too large",
        message: "Use a shorter video or raise the local upload limit before trying again.",
        recovery: "Select a smaller MP4 or MOV file and retry upload.",
      };
    }
    if (error.code === "video_not_analyzed") {
      return {
        title: "Not analyzed yet",
        message: "Run analysis before opening the timeline or asking questions.",
        recovery: "Start analysis for this video, then retry the action.",
      };
    }
    if (error.code === "video_already_processing") {
      return {
        title: "Analysis in progress",
        message: "This video is already being analyzed. Keep this page open and refresh status.",
        recovery: "Wait for the processing status to finish, then refresh.",
      };
    }
    if (CONFIG_FAILURE_CODES.has(error.code)) {
      return {
        title: "Provider configuration needed",
        message: "Set the required provider key or model configuration in the local environment.",
        recovery: "Update the local environment, restart the backend, and retry analysis.",
      };
    }
    if (FFMPEG_FAILURE_CODES.has(error.code)) {
      return {
        title: "FFmpeg needs attention",
        message: "The backend could not process the video media with the local video tools.",
        recovery: "Install FFmpeg or confirm it is available on PATH, then retry analysis.",
      };
    }
    if (ANALYSIS_FAILURE_CODES.has(error.code) || error.status >= 500) {
      return {
        title: "Analysis failed",
        message: "The backend marked analysis as failed without exposing internal details.",
        recovery: "Check provider keys, FFmpeg, and the source video, then retry analysis.",
      };
    }
    if (error.code === "empty_question") {
      return {
        title: "Question required",
        message: "Enter a question before asking the video.",
        recovery: "Type a question and submit it again.",
      };
    }
    if (error.code === "video_not_found") {
      return {
        title: "Video not found",
        message: "The selected video record is not available in the local backend.",
        recovery: "Load a different video ID or upload the video again.",
      };
    }
    if (error.code === "request_aborted") {
      return {
        title: "Request cancelled",
        message: "The browser stopped the request before it completed.",
        recovery: "Retry the action when the local app is ready.",
      };
    }
  }

  return {
    title: "Request failed",
    message: "The operation could not be completed. Try again after checking the local app state.",
    recovery: "Retry the action or refresh the current video status.",
  };
}

export function analysisFailedStatusError(): UserFacingError {
  return {
    title: "Analysis failed",
    message: "Analysis stopped before the timeline could be built.",
    recovery: "Check provider configuration, FFmpeg, and the source video, then retry analysis.",
  };
}
