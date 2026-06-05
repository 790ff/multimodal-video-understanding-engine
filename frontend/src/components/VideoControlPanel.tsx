import {
  ChevronDown,
  Database,
  ListChecks,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Server,
} from "lucide-react";
import { FormEvent, useState } from "react";

import type { AnalyzeVideoResponse, VideoStatusResponse, VideoUploadResponse } from "../api/types";
import type { WorkflowStage } from "../utils/workflowStage";
import type { AnalysisProgressState } from "../utils/workflowProgress";
import { ProgressMeter } from "./ProgressMeter";
import { StatusBadge } from "./StatusBadge";

type VideoControlPanelProps = {
  stage: WorkflowStage;
  apiBaseUrl: string;
  upload: VideoUploadResponse | null;
  status: VideoStatusResponse | null;
  analysis: AnalyzeVideoResponse | null;
  canAnalyze: boolean;
  refreshingStatus: boolean;
  analyzing: boolean;
  analysisProgress: AnalysisProgressState;
  onAnalyze: () => void;
  onRefreshStatus: () => void;
  onLoadVideoId: (videoId: string) => void;
  onReset: () => void;
};

export function VideoControlPanel({
  stage,
  apiBaseUrl,
  upload,
  status,
  analysis,
  canAnalyze,
  refreshingStatus,
  analyzing,
  analysisProgress,
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

  const hasVideo = Boolean(upload || status);
  const showAnalyzeAction = stage === "uploaded" || stage === "processing" || stage === "failed";
  const analyzeLabel =
    stage === "processing" ? "Analyzing" : stage === "failed" ? "Retry analysis" : "Analyze";

  return (
    <section
      className={`tool-panel control-panel control-panel--${stage}`}
      aria-labelledby="status-title"
      aria-busy={refreshingStatus || analyzing}
    >
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Next step</span>
          <h2 id="status-title">{stageTitle(stage)}</h2>
        </div>
        <StatusBadge status={status?.status} />
      </div>

      <p className="stage-copy">{stageDetail(stage)}</p>

      <ProgressMeter
        label={analysisProgress.label}
        detail={analysisProgress.detail}
        value={analysisProgress.percent}
        tone={analysisProgressTone(analysisProgress.phase)}
      />

      <ol className="progress-steps" aria-label="Workflow progress">
        {analysisProgress.steps.map((step) => (
          <li key={step.id} className={`progress-step progress-step--${step.status}`}>
            <span aria-hidden="true" />
            {step.label}
          </li>
        ))}
      </ol>

      {analysis ? (
        <div className="analysis-counts analysis-counts--compact" aria-label="Analysis counts">
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
        {showAnalyzeAction ? (
          <button
            type="button"
            className="primary-button"
            onClick={onAnalyze}
            disabled={!canAnalyze}
          >
            <Play size={17} aria-hidden="true" />
            {analyzeLabel}
          </button>
        ) : null}
        {hasVideo ? (
          <button type="button" className="secondary-button" onClick={onReset}>
            <RotateCcw size={17} aria-hidden="true" />
            New video
          </button>
        ) : null}
      </div>

      {status?.status === "failed" ? (
        <p className="inline-warning">
          <ListChecks size={16} aria-hidden="true" />
          Analysis stopped before completion. Check local configuration, then retry analysis.
        </p>
      ) : null}

      <details className="advanced-panel">
        <summary>
          <span>
            <ChevronDown size={16} aria-hidden="true" />
            Advanced details
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
    </section>
  );
}

function stageTitle(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Start analysis";
  }
  if (stage === "processing") {
    return "Analysis running";
  }
  if (stage === "analyzed") {
    return "Review evidence";
  }
  if (stage === "failed") {
    return "Recover analysis";
  }
  return "Add a video";
}

function stageDetail(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Source stored locally. Analysis can start.";
  }
  if (stage === "processing") {
    return "Backend processing is in progress.";
  }
  if (stage === "analyzed") {
    return "Evidence is ready for review.";
  }
  if (stage === "failed") {
    return "Analysis stopped before evidence was ready.";
  }
  return "No source loaded.";
}

function analysisProgressTone(phase: AnalysisProgressState["phase"]) {
  if (phase === "complete") {
    return "success";
  }
  if (phase === "failed") {
    return "danger";
  }
  if (phase === "processing" || phase === "timeline") {
    return "active";
  }
  return "neutral";
}
