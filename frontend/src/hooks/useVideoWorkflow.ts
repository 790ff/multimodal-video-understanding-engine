import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, videoApi } from "../api/client";
import { toUserFacingError, type UserFacingError } from "../api/errors";
import type {
  AnalyzeVideoResponse,
  AskVideoResponse,
  TimelineResponse,
  VideoStatusResponse,
  VideoUploadResponse,
} from "../api/types";
import { validateVideoFile } from "../utils/file";

const STORAGE_KEY = "mvue.currentVideoId";

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

  const videoId = upload?.video_id ?? status?.video_id ?? null;

  const setBusyFlag = useCallback((key: keyof BusyState, value: boolean) => {
    setBusy((current) => ({ ...current, [key]: value }));
  }, []);

  const captureError = useCallback((caught: unknown) => {
    setError(toUserFacingError(caught));
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
        return nextTimeline;
      } catch (caught) {
        setTimeline(null);
        captureError(caught);
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
          setError((currentError) => currentError ?? {
            title: "Analysis failed",
            message: nextStatus.error_message ?? "The backend marked analysis as failed.",
          });
        }
        return nextStatus;
      } catch (caught) {
        captureError(caught);
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
  }, []);

  const uploadSelectedFile = useCallback(async () => {
    if (!selectedFile) {
      setError({
        title: "Video required",
        message: "Choose an MP4 or MOV file before uploading.",
      });
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
      );
      return;
    }

    setBusyFlag("uploading", true);
    try {
      const uploadedVideo = await videoApi.upload(selectedFile);
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
    } catch (caught) {
      captureError(caught);
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
        });
        return;
      }

      setUpload(null);
      setAnalysis(null);
      setTimeline(null);
      setAnswer(null);
      setError(null);
      await refreshStatus(targetVideoId);
    },
    [refreshStatus],
  );

  const analyzeVideo = useCallback(async () => {
    if (!videoId) {
      setError({
        title: "Video required",
        message: "Upload a video before running analysis.",
      });
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
      if (nextAnalysis.status === "analyzed") {
        await loadTimeline(nextAnalysis.video_id);
      }
    } catch (caught) {
      captureError(caught);
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
        });
        return;
      }
      if (status?.status !== "analyzed") {
        captureError(
          new ApiError({
            status: 409,
            code: "video_not_analyzed",
            message: "Video has not been analyzed.",
          }),
        );
        return;
      }

      setBusyFlag("asking", true);
      try {
        const nextAnswer = await videoApi.ask(videoId, question.trim());
        setAnswer(nextAnswer);
        setError(null);
      } catch (caught) {
        captureError(caught);
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
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

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
      canAnalyze: Boolean(videoId) && !busy.analyzing && status?.status !== "processing",
      canAsk: Boolean(videoId) && status?.status === "analyzed" && !busy.asking,
      hasVideo: Boolean(videoId),
    }),
    [analysis, answer, busy, error, selectedFile, status, timeline, upload, videoId],
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
      resetWorkspace,
    },
  };
}
