const PILL_VARIANTS: Record<string, string> = {
  completed: "ok",
  passed: "ok",
  succeeded: "ok",
  in_progress: "run",
  running: "run",
  pending: "run",
  failed: "fail",
  error: "fail",
};

/** Maps a backend status string onto the Swiss badge vocabulary. */
export function StatusPill({ status }: { status: string | null | undefined }) {
  const value = status ?? "unknown";
  const variant = PILL_VARIANTS[value.toLowerCase()] ?? "idle";

  return (
    <span className={`pill pill--${variant}`}>
      <i aria-hidden="true" />
      {value.replace(/_/g, " ")}
    </span>
  );
}
