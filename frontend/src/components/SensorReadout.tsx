import type { Frame } from "../api/types";
import { formatTs, humanize } from "../lib";
import { ModeBadge } from "./ModeBadge";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border bg-white p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

export function SensorReadout({ frame }: { frame: Frame | null }) {
  if (!frame) return <p className="text-slate-600">Start playback to see readings.</p>;
  const { record: r, proposed: d } = frame;
  const fmt = (v: number | null, unit: string) => (v === null ? "—" : `${v.toFixed(2)} ${unit}`);
  return (
    <section aria-label="Current reading" className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Timestamp (dataset)" value={formatTs(r.timestamp)} />
        <Stat label="Temperature" value={fmt(r.temperature_c, "°C")} />
        <Stat label="Relative humidity" value={fmt(r.humidity_pct, "%")} />
        <Stat
          label="Occupancy"
          value={r.occupancy === null ? "—" : r.occupancy === 1 ? "Occupied" : "Unoccupied"}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <ModeBadge mode={d.mode} source={d.source} />
        <span className="text-sm text-slate-700">
          Reason: {humanize(d.reason)}
          {d.detail && ` — ${d.detail}`}
        </span>
        {!r.valid && <span className="text-sm text-rose-700">Invalid record: {r.error}</span>}
      </div>
      <p className="text-sm text-slate-600">
        Baseline (fixed schedule) mode: {humanize(frame.baseline.mode)}
      </p>
    </section>
  );
}
