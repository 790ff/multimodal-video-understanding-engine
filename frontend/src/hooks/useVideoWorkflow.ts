import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, videoApi } from "../api/client";
import {
  analysisFailedStatusError,
  toUserFacingError,
  type UserFacingError,
} from "../api/errors";
import type {
  AnalyzeVideoResponse,
  AskVideoResponse,
  TimelineResponse,
  VideoStatusResponse,
  VideoUploadResponse,
} from "../api/types";
import { validateVideoFile } from "../utils/file";
import {
  buildAnalysisProgress,
  idleUploadProgress,
  uploadProgressFromEvent,
  uploadProgressFromFile,
  type AnalysisProgressState,
  type UploadProgressState,
} from "../utils/workflowProgress";

const STORAGE_KEY = "mvue.currentVideoId";

type WorkflowOperation = "upload" | "status" | "analysis" | "timeline" | "question";

type BusyState = {
  uploading: boolean;
  refreshingStatus: boolean;
  analyzing: boolean;
  loadingTimeline: boolean;
  asking: boolean;
};

export type VideoWorkflowState = {
  selectedFile: File | null;
  upload: VideoUploadResponse | null;
  status: VideoStatusResponse | null;
  analysis: AnalyzeVideoResponse | null;
  timeline: TimelineResponse | null;
  answer: AskVideoResponse | null;
  error: UserFacingError | null;
  busy: BusyState;
  uploadProgress: UploadProgressState;
  analysisProgress: AnalysisProgressState;
  recoveryActionLabel: string | null;
  canAnalyze: boolean;
  canAsk: boolean;
  hasVideo: boolean;
};

const idleBusyState: BusyState = {
  uploading: false,
  refreshingStatus: false,
  analyzing: false,
  loadingTimeline: false,
  asking: false,
};

export function useVideoWorkflow() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<VideoUploadResponse | null>(null);
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeVideoResponse | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [answer, setAnswer] = useState<AskVideoResponse | null>(null);
  const [error, setError] = useState<UserFacingError | null>(null);
  const [busy, setBusy] = useState<BusyState>(idleBusyState);
  const [uploadProgress, setUploadProgress] =
    useState<UploadProgressState>(idleUploadProgress);
  const [lastFailedOperation, setLastFailedOperation] = useState<WorkflowOperation | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");

  const videoId = upload?.video_id ?? status?.video_id ?? null;

  const setBusyFlag = useCallback((key: keyof BusyState, value: boolean) => {
    setBusy((current) => ({ ...current, [key]: value }));
  }, []);

  const captureError = useCallback((caught: unknown, operation: WorkflowOperation) => {
    setError(toUserFacingError(caught));
    setLastFailedOperation(operation);
  }, []);

  const loadTimeline = useCallback(
    async (targetVideoId = videoId) => {
      if (!targetVideoId) {
        return null;
      }
      setBusyFlag("loadingTimeline", true);
      try {
        const nextTimeline = await videoApi.timeline(targetVideoId);
        setTimeline(nextTimeline);
        setError(null);
        setLastFailedOperation(null);
        return nextTimeline;
      } catch (caught) {
        setTimeline(null);
        captureError(caught, "timeline");
        return null;
      } finally {
        setBusyFlag("loadingTimeline", false);
      }
    },
    [captureError, setBusyFlag, videoId],
  );

  const refreshStatus = useCallback(
    async (targetVideoId = videoId) => {
      if (!targetVideoId) {
        return null;
      }
      setBusyFlag("refreshingStatus", true);
      try {
        const nextStatus = await videoApi.status(targetVideoId);
        setStatus(nextStatus);
        if (nextStatus.status === "analyzed") {
          void loadTimeline(targetVideoId);
        }
        if (nextStatus.status === "failed") {
          setError((currentError) => currentError ?? analysisFailedStatusError());
          setLastFailedOperation((currentOperation) => currentOperation ?? "analysis");
        } else {
          setError(null);
          setLastFailedOperation(null);
        }
        return nextStatus;
      } catch (caught) {
        captureError(caught, "status");
        return null;
      } finally {
        setBusyFlag("refreshingStatus", false);
      }
    },
    [captureError, loadTimeline, setBusyFlag, videoId],
  );

  useEffect(() => {
    const storedVideoId = window.localStorage.getItem(STORAGE_KEY);
    if (storedVideoId) {
      void refreshStatus(storedVideoId);
    }
  }, [refreshStatus]);

  useEffect(() => {
    if (videoId) {
      window.localStorage.setItem(STORAGE_KEY, videoId);
    }
  }, [videoId]);

  useEffect(() => {
    if (!videoId || (status?.status !== "processing" && !busy.analyzing)) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void refreshStatus(videoId);
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [busy.analyzing, refreshStatus, status?.status, videoId]);

  const selectFile = useCallback((file: File | null) => {
    setSelectedFile(file);
    setError(null);
    setLastFailedOperation(null);
    setUploadProgress(file ? uploadProgressFromFile(file) : idleUploadProgress);
  }, []);

  const uploadSelectedFile = useCallback(async () => {
    if (!selectedFile) {
      setError({
        title: "Video required",
        message: "Choose an MP4 or MOV file before uploading.",
        recovery: "Select a supported video file and upload again.",
      });
      setLastFailedOperation("upload");
      return;
    }

    const validationCode = validateVideoFile(selectedFile);
    if (validationCode) {
      captureError(
        new ApiError({
          status: 400,
          code: validationCode,
          message: "Unsupported video file type.",
        }),
        "upload",
      );
      setUploadProgress({
        phase: "failed",
        percent: 0,
        label: "Upload blocked",
        detail: "Choose an MP4 or MOV file.",
      });
      return;
    }

    setBusyFlag("uploading", true);
    setUploadProgress({
      phase: "uploading",
      percent: 0,
      label: "Uploading video",
      detail: uploadProgressFromFile(selectedFile).detail,
    });
    try {
      const uploadedVideo = await videoApi.upload(selectedFile, {
        onProgress: (progress) => {
          setUploadProgress(uploadProgressFromEvent(progress, selectedFile));
        },
      });
      setUpload(uploadedVideo);
      setStatus({
        video_id: uploadedVideo.video_id,
        status: uploadedVideo.status,
        error_message: null,
      });
      setAnalysis(null);
      setTimeline(null);
      setAnswer(null);
      setError(null);
      setLastFailedOperation(null);
      setUploadProgress({
        phase: "complete",
        percent: 100,
        label: "Upload complete",
        detail: `${uploadedVideo.filename} is ready for analysis.`,
      });
    } catch (caught) {
      captureError(caught, "upload");
      setUploadProgress({
        phase: "failed",
        percent: null,
        label: "Upload needs retry",
        detail: "The video was not stored by the backend.",
      });
    } finally {
      setBusyFlag("uploading", false);
    }
  }, [captureError, selectedFile, setBusyFlag]);

  const loadVideoId = useCallback(
    async (inputVideoId: string) => {
      const targetVideoId = inputVideoId.trim();
      if (!targetVideoId) {
        setError({
          title: "Video ID required",
          message: "Enter a stored video ID to load its current status.",
          recovery: "Paste a video ID from this local backend and load it again.",
        });
        setLastFailedOperation("status");
        return;
      }

      setUpload(null);
      setAnalysis(null);
      setTimeline(null);
      setAnswer(null);
      setError(null);
      setLastFailedOperation(null);
      await refreshStatus(targetVideoId);
    },
    [refreshStatus],
  );

  const analyzeVideo = useCallback(async () => {
    if (!videoId) {
      setError({
        title: "Video required",
        message: "Upload a video before running analysis.",
        recovery: "Upload or load a video, then start analysis.",
      });
      setLastFailedOperation("analysis");
      return;
    }

    setBusyFlag("analyzing", true);
    setStatus((current) =>
      current ? { ...current, status: "processing", error_message: null } : current,
    );
    setTimeline(null);
    setAnswer(null);
    try {
      const nextAnalysis = await videoApi.analyze(videoId);
      setAnalysis(nextAnalysis);
      setStatus({
        video_id: nextAnalysis.video_id,
        status: nextAnalysis.status,
        error_message: null,
      });
      setError(null);
      setLastFailedOperation(null);
      if (nextAnalysis.status === "analyzed") {
        await loadTimeline(nextAnalysis.video_id);
      }
    } catch (caught) {
      captureError(caught, "analysis");
      await refreshStatus(videoId);
    } finally {
      setBusyFlag("analyzing", false);
    }
  }, [captureError, loadTimeline, refreshStatus, setBusyFlag, videoId]);

  const askQuestion = useCallback(
    async (question: string) => {
      if (!videoId) {
        setError({
          title: "Video required",
          message: "Upload and analyze a video before asking questions.",
          recovery: "Analyze a video, then ask again.",
        });
        setLastFailedOperation("question");
        return;
      }
      if (status?.status !== "analyzed") {
        captureError(
          new ApiError({
            status: 409,
            code: "video_not_analyzed",
            message: "Video has not been analyzed.",
          }),
          "question",
        );
        return;
      }

      setBusyFlag("asking", true);
      setLastQuestion(question.trim());
      try {
        const nextAnswer = await videoApi.ask(videoId, question.trim());
        setAnswer(nextAnswer);
        setError(null);
        setLastFailedOperation(null);
      } catch (caught) {
        captureError(caught, "question");
      } finally {
        setBusyFlag("asking", false);
      }
    },
    [captureError, setBusyFlag, status?.status, videoId],
  );

  const resetWorkspace = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setSelectedFile(null);
    setUpload(null);
    setStatus(null);
    setAnalysis(null);
    setTimeline(null);
    setAnswer(null);
    setError(null);
    setBusy(idleBusyState);
    setUploadProgress(idleUploadProgress);
    setLastFailedOperation(null);
    setLastQuestion("");
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setLastFailedOperation(null);
  }, []);

  const retryLastFailedOperation = useCallback(async () => {
    if (!lastFailedOperation) {
      return;
    }

    if (lastFailedOperation === "upload") {
      await uploadSelectedFile();
      return;
    }
    if (lastFailedOperation === "analysis") {
      await analyzeVideo();
      return;
    }
    if (lastFailedOperation === "timeline") {
      await loadTimeline();
      return;
    }
    if (lastFailedOperation === "question" && lastQuestion) {
      await askQuestion(lastQuestion);
      return;
    }

    await refreshStatus();
  }, [
    analyzeVideo,
    askQuestion,
    lastFailedOperation,
    lastQuestion,
    loadTimeline,
    refreshStatus,
    uploadSelectedFile,
  ]);

  const analysisProgress = useMemo(
    () =>
      buildAnalysisProgress({
        hasVideo: Boolean(videoId),
        status: status?.status,
        analyzing: busy.analyzing,
        loadingTimeline: busy.loadingTimeline,
        hasTimeline: Boolean(timeline),
      }),
    [busy.analyzing, busy.loadingTimeline, status?.status, timeline, videoId],
  );

  const recoveryActionLabel = useMemo(() => {
    if (!error || !lastFailedOperation) {
      return null;
    }
    if (lastFailedOperation === "upload") {
      return "Retry upload";
    }
    if (lastFailedOperation === "analysis") {
      return "Retry analysis";
    }
    if (lastFailedOperation === "timeline") {
      return "Reload timeline";
    }
    if (lastFailedOperation === "question" && lastQuestion) {
      return "Ask again";
    }
    return "Refresh status";
  }, [error, lastFailedOperation, lastQuestion]);

  const state: VideoWorkflowState = useMemo(
    () => ({
      selectedFile,
      upload,
      status,
      analysis,
      timeline,
      answer,
      error,
      busy,
      uploadProgress,
      analysisProgress,
      recoveryActionLabel,
      canAnalyze: Boolean(videoId) && !busy.analyzing && status?.status !== "processing",
      canAsk: Boolean(videoId) && status?.status === "analyzed" && !busy.asking,
      hasVideo: Boolean(videoId),
    }),
    [
      analysis,
      analysisProgress,
      answer,
      busy,
      error,
      recoveryActionLabel,
      selectedFile,
      status,
      timeline,
      upload,
      uploadProgress,
      videoId,
    ],
  );

  return {
    state,
    actions: {
      selectFile,
      uploadSelectedFile,
      analyzeVideo,
      refreshStatus,
      loadTimeline,
      loadVideoId,
      askQuestion,
      clearError,
      retryLastFailedOperation,
      resetWorkspace,
    },
  };
}
