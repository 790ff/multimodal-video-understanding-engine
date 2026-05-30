import { ListChecks, Play, RefreshCw, RotateCcw, Search } from "lucide-react";
import { FormEvent, useState } from "react";

import type { AnalyzeVideoResponse, VideoStatusResponse, VideoUploadResponse } from "../api/types";
import { StatusBadge } from "./StatusBadge";

type VideoControlPanelProps = {
  upload: VideoUploadResponse | null;
  status: VideoStatusResponse | null;
  analysis: AnalyzeVideoResponse | null;
  canAnalyze: boolean;
  refreshingStatus: boolean;
  analyzing: boolean;
  onAnalyze: () => void;
  onRefreshStatus: () => void;
  onLoadVideoId: (videoId: string) => void;
  onReset: () => void;
};

export function VideoControlPanel({
  upload,
  status,
  analysis,
  canAnalyze,
  refreshingStatus,
  analyzing,
  onAnalyze,
  onRefreshStatus,
  onLoadVideoId,
  onReset,
}: VideoControlPanelProps) {
  const [videoIdInput, setVideoIdInput] = useState("");

  function handleLoadVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLoadVideoId(videoIdInput);
  }

  return (
    <section className="tool-panel control-panel" aria-labelledby="status-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Processing</span>
          <h2 id="status-title">Status</h2>
        </div>
        <StatusBadge status={status?.status} />
      </div>

      <dl className="metadata-grid">
        <div>
          <dt>File</dt>
          <dd>{upload?.filename ?? "None"}</dd>
        </div>
        <div>
          <dt>Video ID</dt>
          <dd className="mono-text">{status?.video_id ?? upload?.video_id ?? "None"}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{status?.status ?? "No video"}</dd>
        </div>
      </dl>

      <form className="load-video-form" onSubmit={handleLoadVideo}>
        <label htmlFor="load-video-id">Load video ID</label>
        <div>
          <input
            id="load-video-id"
            value={videoIdInput}
            onChange={(event) => setVideoIdInput(event.target.value)}
            placeholder="uuid"
          />
          <button type="submit" className="secondary-button">
            <Search size={16} aria-hidden="true" />
            Load
          </button>
        </div>
      </form>

      {analysis ? (
        <div className="analysis-counts" aria-label="Analysis counts">
          <span>
            <strong>{analysis.transcript_segments}</strong> transcripts
          </span>
          <span>
            <strong>{analysis.keyframes}</strong> frames
          </span>
          <span>
            <strong>{analysis.scenes}</strong> scenes
          </span>
          <span>
            <strong>{analysis.timeline_events}</strong> events
          </span>
        </div>
      ) : null}

      <div className="button-row">
        <button
          type="button"
          className="primary-button"
          onClick={onAnalyze}
          disabled={!canAnalyze}
        >
          <Play size={17} aria-hidden="true" />
          {analyzing ? "Analyzing" : "Analyze"}
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={onRefreshStatus}
          disabled={!upload && !status}
        >
          <RefreshCw size={17} aria-hidden="true" className={refreshingStatus ? "spin" : ""} />
          Refresh
        </button>
        <button type="button" className="ghost-button" onClick={onReset}>
          <RotateCcw size={17} aria-hidden="true" />
          New video
        </button>
      </div>

      {status?.status === "failed" ? (
        <p className="inline-warning">
          <ListChecks size={16} aria-hidden="true" />
          {status.error_message ?? "Analysis failed."}
        </p>
      ) : null}
    </section>
  );
}
