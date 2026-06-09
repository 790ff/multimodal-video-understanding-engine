import { FileVideo2, UploadCloud } from "lucide-react";
import { motion } from "motion/react";
import type { ChangeEvent, DragEvent } from "react";
import { useState } from "react";

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
  const [dragging, setDragging] = useState(false);
  const uploaded = progress.phase === "complete";
  const uploadDisabled = !selectedFile || uploading || uploaded;
  const uploadButtonClass = uploaded ? "secondary-button upload-button" : "primary-button upload-button";

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    onSelectFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    onSelectFile(event.dataTransfer.files?.[0] ?? null);
  }

  function handleDrag(event: DragEvent<HTMLLabelElement>, active: boolean) {
    event.preventDefault();
    setDragging(active);
  }

  return (
    <motion.section
      className={`tool-panel upload-panel${dragging ? " upload-panel--dragging" : ""}`}
      aria-labelledby="upload-title"
      aria-busy={uploading}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.18 }}
    >
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Source slot</span>
          <h2 id="upload-title">Load clip</h2>
        </div>
        <FileVideo2 size={22} aria-hidden="true" />
      </div>
      <label
        className="file-drop"
        htmlFor="video-file-input"
        onDragEnter={(event) => handleDrag(event, true)}
        onDragOver={(event) => handleDrag(event, true)}
        onDragLeave={(event) => handleDrag(event, false)}
        onDrop={handleDrop}
      >
        <input
          id="video-file-input"
          type="file"
          accept=".mp4,.mov,video/mp4,video/quicktime"
          aria-label="Video file"
          onChange={handleFileChange}
        />
        <span className="file-drop__icon">
          <UploadCloud size={28} aria-hidden="true" />
        </span>
        <span className="file-drop__title">{selectedFile ? selectedFile.name : "Drop MP4 or MOV"}</span>
        <span className="file-drop__meta">
          {selectedFile ? formatBytes(selectedFile.size) : "Choose from Finder"}
        </span>
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
        {uploading ? "Adding" : uploaded ? "Clip added" : progress.phase === "failed" ? "Try again" : "Add clip"}
      </button>
    </motion.section>
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

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
