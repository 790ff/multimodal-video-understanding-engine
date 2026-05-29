import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  message: string;
};

export function EmptyState({ icon: Icon, title, message }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <Icon size={24} aria-hidden="true" />
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
