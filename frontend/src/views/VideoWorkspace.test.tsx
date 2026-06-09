import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { VideoWorkspace } from "./VideoWorkspace";

const apiMocks = vi.hoisted(() => ({
  upload: vi.fn(),
  status: vi.fn(),
  analyze: vi.fn(),
  timeline: vi.fn(),
  ask: vi.fn(),
}));

vi.mock("../api/client", () => {
  class ApiError extends Error {
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

  return {
    ApiError,
    videoApi: apiMocks,
  };
});

type UploadOptions = {
  onProgress?: (progress: { loaded: number; total: number | null; percent: number | null }) => void;
};

describe("VideoWorkspace", () => {
  beforeEach(() => {
    installLocalStorageMock();
    apiMocks.upload.mockImplementation((file: File, options?: UploadOptions) => {
      options?.onProgress?.({ loaded: file.size, total: file.size, percent: 100 });
      return Promise.resolve({
        video_id: "video-1",
        filename: file.name,
        status: "uploaded",
      });
    });
    apiMocks.status.mockResolvedValue({
      video_id: "video-1",
      status: "uploaded",
      error_message: null,
    });
    apiMocks.analyze.mockResolvedValue({
      video_id: "video-1",
      status: "analyzed",
      transcript_segments: 2,
      keyframes: 2,
      scenes: 1,
      timeline_events: 1,
    });
    apiMocks.timeline.mockResolvedValue({
      video_id: "video-1",
      events: [
        {
          start_time: 0,
          end_time: 2,
          summary: "Opening scene with visible narration.",
          evidence: [{ type: "transcript", start_time: 0, end_time: 2 }],
        },
      ],
    });
    apiMocks.ask.mockResolvedValue({
      answer: "The video opens with narrated context.",
      evidence: [{ type: "timeline_event", start_time: 0, end_time: 2 }],
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("starts with one clear add-video action and keeps locked tools quiet", async () => {
    render(<VideoWorkspace />);

    expect(screen.getAllByText("No clip loaded").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "No clip loaded" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^add clip$/i })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /^start review$/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Your question")).not.toBeInTheDocument();
    expect(screen.getByText("Questions locked")).toBeInTheDocument();
    const devDrawer = screen.getByRole("button", { name: /dev drawer/i });
    expect(devDrawer).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("http://127.0.0.1:8000")).not.toBeInTheDocument();

    fireEvent.click(devDrawer);
    await waitFor(() => {
      expect(screen.getByText("http://127.0.0.1:8000")).toBeVisible();
    });
    expect(devDrawer).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(devDrawer);
    expect(devDrawer).toHaveAttribute("aria-expanded", "false");
  });

  it("covers add, review, notes, and question state transitions", async () => {
    render(<VideoWorkspace />);

    chooseFile("clip.mp4");
    fireEvent.click(screen.getByRole("button", { name: /^add clip$/i }));

    expect(await screen.findByRole("button", { name: /^clip added$/i })).toBeDisabled();
    expect(screen.getByRole("heading", { name: "Deck ready" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^start review$/i })).toBeEnabled();
    expect(screen.queryByLabelText("Your question")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^start review$/i }));

    await waitFor(() => {
      expect(screen.getAllByText("Opening scene with visible narration.").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("Board ready")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Your question"), {
      target: { value: "What happened at the start?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask question$/i }));

    expect(await screen.findByText("The video opens with narrated context.")).toBeInTheDocument();
    expect(apiMocks.ask).toHaveBeenCalledWith("video-1", "What happened at the start?");
  });

  it("shows upload progress while the upload request is in flight", async () => {
    const upload = deferred<{
      video_id: string;
      filename: string;
      status: "uploaded";
    }>();
    apiMocks.upload.mockImplementationOnce((file: File, options?: UploadOptions) => {
      options?.onProgress?.({ loaded: 4, total: 8, percent: 50 });
      return upload.promise;
    });

    render(<VideoWorkspace />);

    chooseFile("progress.mp4", "video bytes");
    fireEvent.click(screen.getByRole("button", { name: /^add clip$/i }));

    expect(await screen.findByText("Adding 50%")).toBeInTheDocument();

    upload.resolve({
      video_id: "video-1",
      filename: "progress.mp4",
      status: "uploaded",
    });

    expect(await screen.findByRole("button", { name: /^clip added$/i })).toBeDisabled();
  });

  it("keeps analysis errors actionable and retries without exposing provider details", async () => {
    apiMocks.analyze
      .mockRejectedValueOnce(
        new ApiError({
          status: 500,
          code: "frame_analysis_not_configured",
          message: "OPENAI_API_KEY=secret stack trace",
        }),
      )
      .mockResolvedValueOnce({
        video_id: "video-1",
        status: "analyzed",
        transcript_segments: 1,
        keyframes: 1,
        scenes: 1,
        timeline_events: 1,
      });
    apiMocks.status.mockResolvedValueOnce({
      video_id: "video-1",
      status: "failed",
      error_message: "secret stack trace",
    });

    render(<VideoWorkspace />);

    await uploadReadyVideo();
    fireEvent.click(screen.getByRole("button", { name: /^start review$/i }));

    expect(await screen.findByText("Provider configuration needed")).toBeInTheDocument();
    expect(screen.getByText(/restart the backend/i)).toBeInTheDocument();
    expect(screen.queryByText(/OPENAI_API_KEY|stack trace/)).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /try review again/i })[0]);

    await waitFor(() => {
      expect(screen.getAllByText("Opening scene with visible narration.").length).toBeGreaterThan(0);
    });
    expect(apiMocks.analyze).toHaveBeenCalledTimes(2);
  });

  it("handles unsupported files and timeline reload recovery with mocked backend responses", async () => {
    render(<VideoWorkspace />);

    chooseFile("clip.avi");
    fireEvent.click(screen.getByRole("button", { name: /^add clip$/i }));

    expect(await screen.findByText("Unsupported file")).toBeInTheDocument();
    expect(apiMocks.upload).not.toHaveBeenCalled();

    cleanup();
    apiMocks.timeline
      .mockRejectedValueOnce(
        new ApiError({
          status: 0,
          code: "backend_offline",
          message: "Fetch failed at http://127.0.0.1:8000",
        }),
      )
      .mockResolvedValueOnce({
        video_id: "video-1",
        events: [
          {
            start_time: 3,
            end_time: 5,
            summary: "Recovered timeline event.",
            evidence: [{ type: "frame", time: 3, path: "/tmp/frame.jpg" }],
          },
        ],
      });

    render(<VideoWorkspace />);

    await uploadReadyVideo();
    fireEvent.click(screen.getByRole("button", { name: /^start review$/i }));

    expect(await screen.findByText("Backend offline")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /reload notes/i })[0]);

    await waitFor(() => {
      expect(screen.getAllByText("Recovered timeline event.").length).toBeGreaterThan(0);
    });
  });
});

async function uploadReadyVideo() {
  chooseFile("clip.mp4");
  fireEvent.click(screen.getByRole("button", { name: /^add clip$/i }));
  await screen.findByRole("button", { name: /^clip added$/i });
}

function chooseFile(filename: string, contents = "fake video") {
  const fileInput = screen.getByLabelText("Video file");
  const file = new File([contents], filename, {
    type: filename.endsWith(".mov") ? "video/quicktime" : "video/mp4",
  });
  fireEvent.change(fileInput, { target: { files: [file] } });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });

  return { promise, resolve, reject };
}

function installLocalStorageMock() {
  const store = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store.set(key, value);
      }),
      removeItem: vi.fn((key: string) => {
        store.delete(key);
      }),
      clear: vi.fn(() => {
        store.clear();
      }),
    },
  });
}
