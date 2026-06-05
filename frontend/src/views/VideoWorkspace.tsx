import { AskPanel } from "../components/AskPanel";
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
          <span className="eyebrow">Video analysis workspace</span>
          <h1>Multimodal Video Understanding Engine</h1>
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
            apiBaseUrl={apiBaseUrl}
            upload={state.upload}
            status={state.status}
            analysis={state.analysis}
            canAnalyze={state.canAnalyze}
            refreshingStatus={state.busy.refreshingStatus}
            analyzing={state.busy.analyzing}
            analysisProgress={state.analysisProgress}
            onAnalyze={actions.analyzeVideo}
            onRefreshStatus={() => void actions.refreshStatus()}
            onLoadVideoId={actions.loadVideoId}
            onReset={actions.resetWorkspace}
          />
        </aside>

        <section className="results-column" aria-label="Analysis results">
          <div className="results-header">
            <div>
              <span className="eyebrow">Evidence</span>
              <h2>Timeline and questions</h2>
            </div>
            {state.analysis ? (
              <div className="result-metrics" aria-label="Analysis counts">
                <span>
                  <strong>{state.analysis.transcript_segments}</strong> transcripts
                </span>
                <span>
                  <strong>{state.analysis.keyframes}</strong> frames
                </span>
                <span>
                  <strong>{state.analysis.scenes}</strong> scenes
                </span>
                <span>
                  <strong>{state.analysis.timeline_events}</strong> events
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
        </section>
      </section>
    </main>
  );
}

function stageLabel(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Ready to analyze";
  }
  if (stage === "processing") {
    return "Analyzing";
  }
  if (stage === "analyzed") {
    return "Evidence ready";
  }
  if (stage === "failed") {
    return "Needs attention";
  }
  return "No video loaded";
}

function stageResultLabel(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Results unlock after analysis";
  }
  if (stage === "processing") {
    return "Building evidence";
  }
  if (stage === "failed") {
    return "Analysis paused";
  }
  return "Waiting for upload";
}
