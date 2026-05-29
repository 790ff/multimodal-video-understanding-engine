import type {
  AnalyzeVideoResponse,
  ApiErrorEnvelope,
  AskVideoResponse,
  TimelineResponse,
  VideoStatusResponse,
  VideoUploadResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor({
    status,
    code,
    message,
    details = {},
  }: {
    status: number;
    code: string;
    message: string;
    details?: Record<string, unknown>;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function apiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
  return configuredBaseUrl.replace(/\/+$/, "");
}

async function parseError(response: Response): Promise<ApiError> {
  let envelope: ApiErrorEnvelope = {};
  try {
    envelope = (await response.json()) as ApiErrorEnvelope;
  } catch {
    envelope = {};
  }

  const error = envelope.error ?? {};
  return new ApiError({
    status: response.status,
    code: error.code ?? "request_failed",
    message: error.message ?? "Request failed.",
    details: error.details ?? {},
  });
}

async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {},
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, init);
  } catch (error) {
    throw new ApiError({
      status: 0,
      code: "backend_offline",
      message: "The backend API is not reachable.",
      details: { cause: error instanceof Error ? error.name : "unknown" },
    });
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as TResponse;
}

export const videoApi = {
  upload(file: File): Promise<VideoUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return requestJson<VideoUploadResponse>("/videos/upload", {
      method: "POST",
      body: formData,
    });
  },

  status(videoId: string): Promise<VideoStatusResponse> {
    return requestJson<VideoStatusResponse>(`/videos/${videoId}/status`);
  },

  analyze(videoId: string): Promise<AnalyzeVideoResponse> {
    return requestJson<AnalyzeVideoResponse>(`/videos/${videoId}/analyze`, {
      method: "POST",
    });
  },

  timeline(videoId: string): Promise<TimelineResponse> {
    return requestJson<TimelineResponse>(`/videos/${videoId}/timeline`);
  },

  ask(videoId: string, question: string): Promise<AskVideoResponse> {
    return requestJson<AskVideoResponse>(`/videos/${videoId}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
  },
};
