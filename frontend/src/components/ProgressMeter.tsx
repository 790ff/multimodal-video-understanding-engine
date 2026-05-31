type ProgressMeterProps = {
  label: string;
  detail?: string;
  value: number | null;
  tone?: "neutral" | "active" | "success" | "danger";
};

export function ProgressMeter({
  label,
  detail,
  value,
  tone = "neutral",
}: ProgressMeterProps) {
  const clampedValue =
    value === null ? null : Math.min(100, Math.max(0, Math.round(value)));

  return (
    <div className={`progress-meter progress-meter--${tone}`} aria-live="polite">
      <div className="progress-meter__header">
        <span>{label}</span>
        {clampedValue === null ? null : <span>{clampedValue}%</span>}
      </div>
      <div
        className="progress-meter__track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clampedValue ?? undefined}
      >
        <span
          className={clampedValue === null ? "progress-meter__bar is-indeterminate" : "progress-meter__bar"}
          style={clampedValue === null ? undefined : { width: `${clampedValue}%` }}
        />
      </div>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}
