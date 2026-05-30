import { AlertTriangle, RotateCw, X } from "lucide-react";

import type { UserFacingError } from "../api/errors";

type ErrorBannerProps = {
  error: UserFacingError | null;
  actionLabel?: string | null;
  onDismiss: () => void;
  onAction?: () => void;
};

export function ErrorBanner({
  error,
  actionLabel,
  onDismiss,
  onAction,
}: ErrorBannerProps) {
  if (!error) {
    return null;
  }

  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <strong>{error.title}</strong>
        <p>{error.message}</p>
        <p className="error-banner__recovery">{error.recovery}</p>
      </div>
      {actionLabel && onAction ? (
        <button type="button" className="error-action-button" onClick={onAction}>
          <RotateCw size={16} aria-hidden="true" />
          {actionLabel}
        </button>
      ) : null}
      <button type="button" className="icon-button" aria-label="Dismiss error" onClick={onDismiss}>
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
