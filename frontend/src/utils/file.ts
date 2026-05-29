const SUPPORTED_EXTENSIONS = new Set(["mp4", "mov"]);

export function validateVideoFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!SUPPORTED_EXTENSIONS.has(extension)) {
    return "unsupported_video_type";
  }
  return null;
}

export function fileBasename(path: string | null | undefined): string {
  if (!path) {
    return "";
  }
  return path.split(/[\\/]/).pop() ?? path;
}
