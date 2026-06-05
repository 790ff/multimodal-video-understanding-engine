import { FileVideo2, UploadCloud } from "lucide-react";
import type { ChangeEvent } from "react";

import type { UploadProgressState } from "../utils/workflowProgress";
import { ProgressMeter } from "./ProgressMeter";

type UploadPanelProps = {
  selectedFile: File | null;
  uploading: boolean;
  progress: UploadProgressState;
  onSelectFile: (file: File | null) => void;
  onUpload: () => void;
};

export function UploadPanel({
  selectedFile,
  uploading,
  progress,
  onSelectFile,
  onUpload,
}: UploadPanelProps) {
  const uploaded = progress.phase === "complete";
  const uploadDisabled = !selectedFile || uploading || uploaded;
  const uploadButtonClass = uploaded ? "secondary-button upload-button" : "primary-button upload-button";

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    onSelectFile(event.target.files?.[0] ?? null);
  }

  return (
    <section className="tool-panel upload-panel" aria-labelledby="upload-title" aria-busy={uploading}>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Input</span>
          <h2 id="upload-title">Video upload</h2>
        </div>
        <FileVideo2 size={22} aria-hidden="true" />
      </div>
      <label className="file-drop" htmlFor="video-file-input">
        <input
          id="video-file-input"
          type="file"
          accept=".mp4,.mov,video/mp4,video/quicktime"
          aria-label="Video file"
          onChange={handleFileChange}
        />
        <UploadCloud size={28} aria-hidden="true" />
        <span>{selectedFile ? selectedFile.name : "Choose MP4 or MOV"}</span>
      </label>
      <ProgressMeter
        label={progress.label}
        detail={progress.detail}
        value={progress.percent}
        tone={progressTone(progress.phase)}
      />
      <button
        type="button"
        className={uploadButtonClass}
        onClick={onUpload}
        disabled={uploadDisabled}
      >
        <UploadCloud size={17} aria-hidden="true" />
        {uploading ? "Uploading" : uploaded ? "Uploaded" : progress.phase === "failed" ? "Retry upload" : "Upload"}
      </button>
    </section>
  );
}

function progressTone(phase: UploadProgressState["phase"]) {
  if (phase === "complete") {
    return "success";
  }
  if (phase === "failed") {
    return "danger";
  }
  if (phase === "uploading") {
    return "active";
  }
  return "neutral";
}
