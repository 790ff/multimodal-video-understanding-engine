export function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0:00";
  }

  const safeValue = Math.max(0, value);
  const minutes = Math.floor(safeValue / 60);
  const seconds = safeValue - minutes * 60;
  const paddedSeconds = Math.floor(seconds).toString().padStart(2, "0");
  const tenths = Math.round((seconds - Math.floor(seconds)) * 10);

  if (tenths > 0) {
    return `${minutes}:${paddedSeconds}.${tenths}`;
  }
  return `${minutes}:${paddedSeconds}`;
}

export function formatRange(start: number | null | undefined, end: number | null | undefined) {
  return `${formatSeconds(start)} - ${formatSeconds(end)}`;
}
