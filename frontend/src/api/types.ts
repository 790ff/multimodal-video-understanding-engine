export type VideoStatusValue = "uploaded" | "processing" | "analyzed" | "failed";

export type VideoUploadResponse = {
  video_id: string;
  filename: string;
  status: VideoStatusValue;
};

export type VideoStatusResponse = {
  video_id: string;
  status: VideoStatusValue;
  error_message: string | null;
};

export type AnalyzeVideoResponse = {
  video_id: string;
  status: VideoStatusValue;
  transcript_segments: number;
  keyframes: number;
  scenes: number;
  timeline_events: number;
};

export type TimelineEvidence = {
  type: "timeline_event" | "transcript" | "frame" | "scene" | string;
  time?: number | null;
  start_time?: number | null;
  end_time?: number | null;
  path?: string | null;
};

export type TimelineEvent = {
  start_time: number;
  end_time: number;
  summary: string;
  evidence: TimelineEvidence[];
};

export type TimelineResponse = {
  video_id: string;
  events: TimelineEvent[];
};

export type AskVideoResponse = {
  answer: string;
  evidence: TimelineEvidence[];
};

export type ApiErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};
