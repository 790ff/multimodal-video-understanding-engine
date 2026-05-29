import { FileVideo2, UploadCloud } from "lucide-react";
import type { ChangeEvent } from "react";

type UploadPanelProps = {
  selectedFile: File | null;
  uploading: boolean;
  onSelectFile: (file: File | null) => void;
  onUpload: () => void;
};

export function UploadPanel({
  selectedFile,
  uploading,
  onSelectFile,
  onUpload,
}: UploadPanelProps) {
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    onSelectFile(event.target.files?.[0] ?? null);
  }

  return (
    <section className="tool-panel upload-panel" aria-labelledby="upload-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Input</span>
          <h2 id="upload-title">Video upload</h2>
        </div>
        <FileVideo2 size={22} aria-hidden="true" />
      </div>
      <label className="file-drop">
        <input type="file" accept=".mp4,.mov,video/mp4,video/quicktime" onChange={handleFileChange} />
        <UploadCloud size={28} aria-hidden="true" />
        <span>{selectedFile ? selectedFile.name : "Choose MP4 or MOV"}</span>
      </label>
      <button
        type="button"
        className="primary-button"
        onClick={onUpload}
        disabled={!selectedFile || uploading}
      >
        <UploadCloud size={17} aria-hidden="true" />
        {uploading ? "Uploading" : "Upload"}
      </button>
    </section>
  );
}
