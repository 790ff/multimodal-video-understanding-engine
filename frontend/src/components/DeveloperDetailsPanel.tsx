import { ChevronDown, Database, RefreshCw, Search, Server } from "lucide-react";
import { FormEvent, useState } from "react";

import type { VideoStatusResponse, VideoUploadResponse } from "../api/types";

type DeveloperDetailsPanelProps = {
  apiBaseUrl: string;
  upload: VideoUploadResponse | null;
  status: VideoStatusResponse | null;
  refreshingStatus: boolean;
  onRefreshStatus: () => void;
  onLoadVideoId: (videoId: string) => void;
};

export function DeveloperDetailsPanel({
  apiBaseUrl,
  upload,
  status,
  refreshingStatus,
  onRefreshStatus,
  onLoadVideoId,
}: DeveloperDetailsPanelProps) {
  const [videoIdInput, setVideoIdInput] = useState("");

  function handleLoadVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLoadVideoId(videoIdInput);
  }

  return (
    <details className="advanced-panel developer-details-panel">
      <summary>
        <span>
          <ChevronDown size={16} aria-hidden="true" />
          Developer details
        </span>
      </summary>

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
        <div>
          <dt>API</dt>
          <dd className="advanced-line">
            <Server size={15} aria-hidden="true" />
            <span>{apiBaseUrl}</span>
          </dd>
        </div>
        <div>
          <dt>Storage</dt>
          <dd className="advanced-line">
            <Database size={15} aria-hidden="true" />
            <span>SQLite and local media folders</span>
          </dd>
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

      <button
        type="button"
        className="ghost-button advanced-refresh"
        onClick={onRefreshStatus}
        disabled={!upload && !status}
      >
        <RefreshCw size={17} aria-hidden="true" className={refreshingStatus ? "spin" : ""} />
        Refresh status
      </button>
    </details>
  );
}
