import type {
  AnalyzeVideoResponse,
  ApiErrorEnvelope,
  AskVideoResponse,
  TimelineResponse,
  UploadProgressEvent,
  VideoStatusResponse,
  VideoUploadResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

type UploadOptions = {
  onProgress?: (progress: UploadProgressEvent) => void;
};

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

  return apiErrorFromEnvelope(response.status, envelope);
}

function apiErrorFromEnvelope(status: number, envelope: ApiErrorEnvelope): ApiError {
  const error = envelope.error ?? {};
  return new ApiError({
    status,
    code: error.code ?? "request_failed",
    message: error.message ?? "Request failed.",
    details: error.details ?? {},
  });
}

function offlineError(cause: unknown): ApiError {
  return new ApiError({
    status: 0,
    code: "backend_offline",
    message: "The backend API is not reachable.",
    details: { cause: cause instanceof Error ? cause.name : "unknown" },
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
    throw offlineError(error);
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as TResponse;
}

function uploadJson<TResponse>(
  path: string,
  formData: FormData,
  options: UploadOptions = {},
): Promise<TResponse> {
  if (!options.onProgress) {
    return requestJson<TResponse>(path, {
      method: "POST",
      body: formData,
    });
  }

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${apiBaseUrl()}${path}`);
    request.responseType = "json";

    request.upload.onprogress = (event) => {
      const total = event.lengthComputable && event.total > 0 ? event.total : null;
      const percent = total ? Math.round((event.loaded / total) * 100) : null;
      options.onProgress?.({
        loaded: event.loaded,
        total,
        percent,
      });
    };

    request.onerror = () => reject(offlineError(new Error("XMLHttpRequestError")));
    request.onabort = () =>
      reject(
        new ApiError({
          status: 0,
          code: "request_aborted",
          message: "The upload request was cancelled.",
        }),
      );
    request.onload = () => {
      const payload = parseXhrPayload(request.response);
      if (request.status >= 200 && request.status < 300) {
        resolve(payload as TResponse);
        return;
      }

      reject(apiErrorFromEnvelope(request.status, payload as ApiErrorEnvelope));
    };

    request.send(formData);
  });
}

function parseXhrPayload(payload: unknown): unknown {
  if (typeof payload !== "string") {
    return payload ?? {};
  }
  if (!payload) {
    return {};
  }
  try {
    return JSON.parse(payload) as unknown;
  } catch {
    return {};
  }
}

export const videoApi = {
  upload(file: File, options: UploadOptions = {}): Promise<VideoUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return uploadJson<VideoUploadResponse>("/videos/upload", formData, options);
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
