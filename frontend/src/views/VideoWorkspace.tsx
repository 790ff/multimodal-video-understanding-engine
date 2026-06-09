import { motion } from "motion/react";

import { AskPanel } from "../components/AskPanel";
import { DeveloperDetailsPanel } from "../components/DeveloperDetailsPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { TimelineView } from "../components/TimelineView";
import { UploadPanel } from "../components/UploadPanel";
import { VideoControlPanel } from "../components/VideoControlPanel";
import { useVideoWorkflow } from "../hooks/useVideoWorkflow";
import { workflowStage, type WorkflowStage } from "../utils/workflowStage";

export function VideoWorkspace() {
  const { state, actions } = useVideoWorkflow();
  const analyzed = state.status?.status === "analyzed";
  const stage = workflowStage({
    analyzed,
    analyzing: state.busy.analyzing,
    hasVideo: state.hasVideo,
    status: state.status?.status,
  });
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  return (
    <main className={`app-shell app-shell--${stage}`}>
      <motion.header
        className="app-header"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: "easeOut" }}
      >
        <div className="brand-cluster">
          <span className="brand-mark" aria-hidden="true">
            FD
          </span>
          <div>
            <span className="eyebrow">Private video desk</span>
            <h1>FrameDeck</h1>
            <p>Drop a clip. Build the review. Jump between moments. Ask what matters.</p>
          </div>
        </div>
        <span className={`stage-pill stage-pill--${stage}`}>{stageLabel(stage)}</span>
      </motion.header>

      <ErrorBanner
        error={state.error}
        actionLabel={state.recoveryActionLabel}
        onAction={() => void actions.retryLastFailedOperation()}
        onDismiss={actions.clearError}
      />

      <section className="workspace-grid" aria-label="Video workflow">
        <motion.aside
          className="workflow-rail"
          aria-label="Workflow controls"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <UploadPanel
            selectedFile={state.selectedFile}
            uploading={state.busy.uploading}
            progress={state.uploadProgress}
            onSelectFile={actions.selectFile}
            onUpload={actions.uploadSelectedFile}
          />
          <VideoControlPanel
            stage={stage}
            hasVideo={state.hasVideo}
            status={state.status}
            analysis={state.analysis}
            canAnalyze={state.canAnalyze}
            analyzing={state.busy.analyzing}
            analysisProgress={state.analysisProgress}
            onAnalyze={actions.analyzeVideo}
            onReset={actions.resetWorkspace}
          />
          <DeveloperDetailsPanel
            apiBaseUrl={apiBaseUrl}
            upload={state.upload}
            status={state.status}
            refreshingStatus={state.busy.refreshingStatus}
            onRefreshStatus={() => void actions.refreshStatus()}
            onLoadVideoId={actions.loadVideoId}
          />
        </motion.aside>

        <motion.div
          className="review-column"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut", delay: 0.03 }}
        >
          <section className="review-board-cell" aria-label="Review board">
            <div className="results-header">
              <div>
                <span className="eyebrow">Review board</span>
                <h2>Moments, sources, questions</h2>
              </div>
              {state.analysis ? (
                <div className="result-metrics" aria-label="Review counts">
                  <span>
                    <strong>{state.analysis.timeline_events}</strong> moments
                  </span>
                  <span>
                    <strong>{state.analysis.scenes}</strong> scenes
                  </span>
                  <span>
                    <strong>{state.analysis.transcript_segments}</strong> notes
                  </span>
                  <span>
                    <strong>{state.analysis.keyframes}</strong> visuals
                  </span>
                </div>
              ) : (
                <span className="readiness-pill">{stageResultLabel(stage)}</span>
              )}
            </div>

            <TimelineView
              timeline={state.timeline}
              loading={state.busy.loadingTimeline}
              analyzed={analyzed}
              stage={stage}
              onReload={() => void actions.loadTimeline()}
            />
          </section>

          <div className="workspace-cell workspace-cell--ask">
            <AskPanel
              answer={state.answer}
              disabled={!state.canAsk}
              asking={state.busy.asking}
              onAsk={actions.askQuestion}
            />
          </div>
        </motion.div>

      </section>
    </main>
  );
}

function stageLabel(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Ready to review";
  }
  if (stage === "processing") {
    return "Reviewing";
  }
  if (stage === "analyzed") {
    return "Notes ready";
  }
  if (stage === "failed") {
    return "Needs attention";
  }
  return "No clip loaded";
}

function stageResultLabel(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Review deck armed";
  }
  if (stage === "processing") {
    return "Building the deck";
  }
  if (stage === "failed") {
    return "Deck paused";
  }
  return "Waiting for clip";
}
