import type { SessionState } from "../api/types";

interface Props {
  state: SessionState | null;
  speed: number;
  onSpeed: (n: number) => void;
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
  onEnd: () => void;
  busy?: boolean;
}

export function PlaybackControls({ state, speed, onSpeed, onStart, onPause, onReset, onEnd, busy }: Props) {
  const running = state?.status === "RUNNING";
  const finished = state?.status === "ENDED" || state?.status === "COMPLETED";
  return (
    <div className="flex flex-wrap items-center gap-2">
      {running ? (
        <button className="btn" onClick={onPause} disabled={busy}>Pause</button>
      ) : (
        <button className="btn btn-primary" onClick={onStart} disabled={busy || finished}>
          {state ? "Start / Resume" : "Start"}
        </button>
      )}
      <button className="btn" onClick={onReset} disabled={busy}>Reset (new session)</button>
      <button className="btn" onClick={onEnd} disabled={busy || !state || finished}>End session</button>
      <label className="ml-2 text-sm">
        Records per tick{" "}
        <select
          aria-label="Records per tick"
          className="rounded border px-1 py-0.5"
          value={speed}
          onChange={(e) => onSpeed(Number(e.target.value))}
        >
          {[1, 5, 15, 60].map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </label>
      {state && (
        <span className="text-sm text-slate-600">
          Session {state.session_id} · {state.status} · {state.cursor}/{state.total_records} records
        </span>
      )}
    </div>
  );
}
