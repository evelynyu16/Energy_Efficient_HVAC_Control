import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ControlEvent, RuntimeReport, SessionSummary } from "../api/types";
import { RuntimeComparison } from "../components/RuntimeComparison";
import { MODE_LABEL, formatTs, humanize } from "../lib";

export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [events, setEvents] = useState<ControlEvent[]>([]);
  const [report, setReport] = useState<RuntimeReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSessions().then((s) => {
      setSessions(s);
      if (s.length) setSelected(s[0].id);
    }).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.events(selected).then((r) => setEvents(r.items)).catch((e) => setError(e.message));
    api.report(selected).then(setReport).catch(() => setReport(null));
  }, [selected]);

  const current = sessions.find((s) => s.id === selected);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">History and Report</h1>
      {error && <p role="alert" className="text-rose-700">Error: {error}</p>}
      <label className="text-sm">
        Session{" "}
        <select aria-label="Session" className="rounded border px-1 py-0.5" value={selected ?? ""}
          onChange={(e) => setSelected(e.target.value)}>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>{s.id} · {s.created_at} · {s.status}</option>
          ))}
        </select>
      </label>
      {current && (
        <details className="rounded border bg-white p-3 text-sm">
          <summary className="cursor-pointer font-semibold">Session parameters</summary>
          <pre className="mt-2 overflow-x-auto">{JSON.stringify(current.settings, null, 2)}</pre>
        </details>
      )}
      {report && <RuntimeComparison report={report} />}
      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Dataset time</th><th className="p-2">Temp (°C)</th>
              <th className="p-2">RH (%)</th><th className="p-2">Occupancy</th>
              <th className="p-2">Previous</th><th className="p-2">New</th>
              <th className="p-2">Control</th><th className="p-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="p-2 whitespace-nowrap">{formatTs(e.timestamp)}</td>
                <td className="p-2">{e.temperature_c?.toFixed(2) ?? "—"}</td>
                <td className="p-2">{e.humidity_pct?.toFixed(1) ?? "—"}</td>
                <td className="p-2">{e.occupancy === null ? "—" : e.occupancy ? "Occupied" : "Unoccupied"}</td>
                <td className="p-2">{e.previous_mode ? MODE_LABEL[e.previous_mode] : "—"}</td>
                <td className="p-2 font-semibold">{MODE_LABEL[e.new_mode]}</td>
                <td className="p-2">{e.source === "MANUAL" ? "Manual" : "Automatic"}</td>
                <td className="p-2">{humanize(e.reason)}{e.detail && ` — ${e.detail}`}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr><td className="p-2 text-slate-500" colSpan={8}>No events recorded.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
