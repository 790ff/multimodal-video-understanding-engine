import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  message: string;
  actionLabel?: string;
  actionIcon?: LucideIcon;
  actionDisabled?: boolean;
  onAction?: () => void;
};

export function EmptyState({
  icon: Icon,
  title,
  message,
  actionLabel,
  actionIcon: ActionIcon,
  actionDisabled = false,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      <Icon size={24} aria-hidden="true" />
      <strong>{title}</strong>
      <p>{message}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          className="secondary-button empty-state__action"
          onClick={onAction}
          disabled={actionDisabled}
        >
          {ActionIcon ? <ActionIcon size={16} aria-hidden="true" /> : null}
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
