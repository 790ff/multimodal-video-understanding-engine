import { ListChecks, Play, RotateCcw } from "lucide-react";
import { motion } from "motion/react";

import type { AnalyzeVideoResponse, VideoStatusResponse } from "../api/types";
import type { WorkflowStage } from "../utils/workflowStage";
import type { AnalysisProgressState } from "../utils/workflowProgress";
import { ProgressMeter } from "./ProgressMeter";
import { StatusBadge } from "./StatusBadge";

type VideoControlPanelProps = {
  stage: WorkflowStage;
  hasVideo: boolean;
  status: VideoStatusResponse | null;
  analysis: AnalyzeVideoResponse | null;
  canAnalyze: boolean;
  analyzing: boolean;
  analysisProgress: AnalysisProgressState;
  onAnalyze: () => void;
  onReset: () => void;
};

export function VideoControlPanel({
  stage,
  hasVideo,
  status,
  analysis,
  canAnalyze,
  analyzing,
  analysisProgress,
  onAnalyze,
  onReset,
}: VideoControlPanelProps) {
  const showAnalyzeAction = stage === "uploaded" || stage === "processing" || stage === "failed";
  const analyzeLabel =
    stage === "processing" ? "Building" : stage === "failed" ? "Retry deck" : "Start review";

  return (
    <motion.section
      className={`tool-panel control-panel control-panel--${stage}`}
      aria-labelledby="status-title"
      aria-busy={analyzing}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.18 }}
    >
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Review engine</span>
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
        <div className="analysis-counts analysis-counts--compact" aria-label="Review counts">
          <span>
            <strong>{analysis.transcript_segments}</strong> notes
          </span>
          <span>
            <strong>{analysis.keyframes}</strong> visuals
          </span>
          <span>
            <strong>{analysis.scenes}</strong> scenes
          </span>
          <span>
            <strong>{analysis.timeline_events}</strong> moments
          </span>
        </div>
      ) : null}

      <div className="button-row">
        {showAnalyzeAction ? (
          <motion.button
            type="button"
            className="primary-button"
            onClick={onAnalyze}
            disabled={!canAnalyze}
            whileTap={canAnalyze ? { x: 2, y: 2 } : undefined}
          >
            <Play size={17} aria-hidden="true" />
            {analyzeLabel}
          </motion.button>
        ) : null}
        {hasVideo ? (
          <button type="button" className="secondary-button" onClick={onReset}>
            <RotateCcw size={17} aria-hidden="true" />
            Replace video
          </button>
        ) : null}
      </div>

      {status?.status === "failed" ? (
        <p className="inline-warning">
          <ListChecks size={16} aria-hidden="true" />
          Review stopped before notes were ready. Check setup, then try again.
        </p>
      ) : null}
    </motion.section>
  );
}

function stageTitle(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Deck ready";
  }
  if (stage === "processing") {
    return "Building deck";
  }
  if (stage === "analyzed") {
    return "Review live";
  }
  if (stage === "failed") {
    return "Deck stalled";
  }
  return "No clip loaded";
}

function stageDetail(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "The clip is parked. Start the review to generate the board.";
  }
  if (stage === "processing") {
    return "The deck is filling with moments, sources, and notes.";
  }
  if (stage === "analyzed") {
    return "Moments and questions are unlocked.";
  }
  if (stage === "failed") {
    return "The last run stopped before the board was ready.";
  }
  return "Drop a short MP4 or MOV into the source slot.";
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
