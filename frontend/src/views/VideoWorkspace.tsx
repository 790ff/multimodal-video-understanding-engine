import { Database, Server } from "lucide-react";

import { AskPanel } from "../components/AskPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { TimelineView } from "../components/TimelineView";
import { UploadPanel } from "../components/UploadPanel";
import { VideoControlPanel } from "../components/VideoControlPanel";
import { useVideoWorkflow } from "../hooks/useVideoWorkflow";

export function VideoWorkspace() {
  const { state, actions } = useVideoWorkflow();
  const analyzed = state.status?.status === "analyzed";

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">Local product app</span>
          <h1>Multimodal Video Understanding Engine</h1>
        </div>
        <div className="api-pill">
          <Server size={16} aria-hidden="true" />
          <span>{import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}</span>
        </div>
      </header>

      <ErrorBanner
        error={state.error}
        actionLabel={state.recoveryActionLabel}
        onAction={() => void actions.retryLastFailedOperation()}
        onDismiss={actions.clearError}
      />

      <section className="workspace-grid" aria-label="Video workflow">
        <div className="left-column">
          <UploadPanel
            selectedFile={state.selectedFile}
            uploading={state.busy.uploading}
            progress={state.uploadProgress}
            onSelectFile={actions.selectFile}
            onUpload={actions.uploadSelectedFile}
          />
          <VideoControlPanel
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
          <div className="runtime-note">
            <Database size={16} aria-hidden="true" />
            <span>SQLite and local media folders back this workspace.</span>
          </div>
        </div>

        <TimelineView
          timeline={state.timeline}
          loading={state.busy.loadingTimeline}
          analyzed={analyzed}
          onReload={() => void actions.loadTimeline()}
        />

        <AskPanel
          answer={state.answer}
          disabled={!state.canAsk}
          asking={state.busy.asking}
          onAsk={actions.askQuestion}
        />
      </section>
    </main>
  );
}
