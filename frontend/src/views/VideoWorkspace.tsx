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
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">Private video review</span>
          <h1>SceneNotes</h1>
          <p>Turn a video into clear notes you can read, revisit, and question.</p>
        </div>
        <span className={`stage-pill stage-pill--${stage}`}>{stageLabel(stage)}</span>
      </header>

      <ErrorBanner
        error={state.error}
        actionLabel={state.recoveryActionLabel}
        onAction={() => void actions.retryLastFailedOperation()}
        onDismiss={actions.clearError}
      />

      <section className="workspace-grid" aria-label="Video workflow">
        <aside className="workflow-rail" aria-label="Workflow controls">
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
        </aside>

        <section className="results-column" aria-label="Review results">
          <div className="results-header">
            <div>
              <span className="eyebrow">Review</span>
              <h2>Your video notes</h2>
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

          <AskPanel
            answer={state.answer}
            disabled={!state.canAsk}
            asking={state.busy.asking}
            onAsk={actions.askQuestion}
          />

          <DeveloperDetailsPanel
            apiBaseUrl={apiBaseUrl}
            upload={state.upload}
            status={state.status}
            refreshingStatus={state.busy.refreshingStatus}
            onRefreshStatus={() => void actions.refreshStatus()}
            onLoadVideoId={actions.loadVideoId}
          />
        </section>
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
  return "No video loaded";
}

function stageResultLabel(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Start review to create notes";
  }
  if (stage === "processing") {
    return "Preparing notes";
  }
  if (stage === "failed") {
    return "Review paused";
  }
  return "Waiting for video";
}
