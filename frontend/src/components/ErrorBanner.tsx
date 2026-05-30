import { AlertTriangle, X } from "lucide-react";

import type { UserFacingError } from "../api/errors";

type ErrorBannerProps = {
  error: UserFacingError | null;
  onDismiss: () => void;
};

export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  if (!error) {
    return null;
  }

  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <strong>{error.title}</strong>
        <p>{error.message}</p>
      </div>
      <button type="button" className="icon-button" aria-label="Dismiss error" onClick={onDismiss}>
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
