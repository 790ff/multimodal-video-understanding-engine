import { ChevronDown, Database, RefreshCw, Search, Server } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
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
  const [open, setOpen] = useState(false);

  function handleLoadVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLoadVideoId(videoIdInput);
  }

  return (
    <motion.section
      className="advanced-panel developer-details-panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
    >
      <button
        type="button"
        className="dev-drawer-trigger"
        aria-expanded={open}
        aria-controls="developer-details-body"
        onClick={() => setOpen((current) => !current)}
      >
        <span>
          <ChevronDown size={16} aria-hidden="true" className={open ? "drawer-chevron drawer-chevron--open" : "drawer-chevron"} />
          Dev drawer
        </span>
        <span className="dev-drawer-trigger__hint">{open ? "Hide setup" : "Show setup"}</span>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            id="developer-details-body"
            className="dev-drawer-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.24, ease: "easeOut" }}
          >
            <div className="dev-drawer-body__inner">
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
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.section>
  );
}
