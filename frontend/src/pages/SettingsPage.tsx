import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ControlSettings } from "../api/types";

type Field = { key: keyof ControlSettings; label: string; unit: string; type: "number" | "time"; step?: number };

const FIELDS: Field[] = [
  { key: "lower_bound_c", label: "Comfort lower bound", unit: "°C", type: "number", step: 0.1 },
  { key: "upper_bound_c", label: "Comfort upper bound", unit: "°C", type: "number", step: 0.1 },
  { key: "hysteresis_c", label: "Hysteresis", unit: "°C", type: "number", step: 0.1 },
  { key: "min_mode_duration_s", label: "Minimum mode duration", unit: "seconds", type: "number", step: 1 },
  { key: "vacancy_delay_s", label: "Vacancy delay before Eco", unit: "seconds", type: "number", step: 1 },
  { key: "baseline_start", label: "Baseline schedule start", unit: "HH:MM", type: "time" },
  { key: "baseline_end", label: "Baseline schedule end", unit: "HH:MM", type: "time" },
];

/** Client-side mirror of FR-07; the backend re-validates and is authoritative. */
export function validateSettings(s: ControlSettings): string[] {
  const errors: string[] = [];
  if (s.lower_bound_c >= s.upper_bound_c) errors.push("Lower bound must be less than upper bound.");
  if (s.min_mode_duration_s < 0 || s.vacancy_delay_s < 0) errors.push("Durations must not be negative.");
  if (s.hysteresis_c < 0) errors.push("Hysteresis must not be negative.");
  else if (s.hysteresis_c >= (s.upper_bound_c - s.lower_bound_c) / 2)
    errors.push("Hysteresis must be less than half the comfort-band width.");
  return errors;
}

export function SettingsPage() {
  const [form, setForm] = useState<ControlSettings | null>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    api.getSettings().then(setForm).catch((e) => setMessages([e.message]));
  }, []);

  if (!form) return <p>Loading settings…</p>;

  const update = (f: Field, raw: string) =>
    setForm({ ...form, [f.key]: f.type === "number" ? Number(raw) : raw.length === 5 ? `${raw}:00` : raw });

  const save = async () => {
    setSaved(null);
    const errors = validateSettings(form);
    setMessages(errors);
    if (errors.length) return;
    try {
      const res = await api.putSettings(form);
      setForm(res.settings);
      setSaved(`Saved ${res.changes.length} change(s). New values apply to the next session.`);
    } catch (e) {
      setMessages([(e as Error).message]);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold">Settings</h1>
      <p className="text-sm text-slate-600">Demonstration assumptions, not regulatory limits. All timing uses dataset time.</p>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save(); }}>
        {FIELDS.map((f) => (
          <label key={f.key} className="flex items-center justify-between gap-4">
            <span>{f.label} ({f.unit})</span>
            <input
              aria-label={f.label}
              className="w-36 rounded border px-2 py-1"
              type={f.type}
              step={f.step}
              value={f.type === "time" ? String(form[f.key]).slice(0, 5) : String(form[f.key])}
              onChange={(e) => update(f, e.target.value)}
            />
          </label>
        ))}
        <button type="submit" className="btn btn-primary">Save settings</button>
      </form>
      {messages.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-rose-700">
          {messages.map((m) => <li key={m}>{m}</li>)}
        </ul>
      )}
      {saved && <p role="status" className="text-emerald-800">{saved}</p>}
    </div>
  );
}
