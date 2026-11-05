import type { Mode } from "./api/types";

/** Text labels for every mode: the UI must never rely on colour alone. */
export const MODE_LABEL: Record<Mode, string> = {
  HEATING: "Heating",
  COOLING: "Cooling",
  STANDBY: "Standby",
  ECO: "Eco (HVAC off)",
  DATA_UNAVAILABLE: "Data unavailable",
};

export const MODE_STYLE: Record<Mode, string> = {
  HEATING: "bg-orange-100 text-orange-900 border-orange-400",
  COOLING: "bg-sky-100 text-sky-900 border-sky-400",
  STANDBY: "bg-slate-100 text-slate-800 border-slate-400",
  ECO: "bg-emerald-100 text-emerald-900 border-emerald-500",
  DATA_UNAVAILABLE: "bg-rose-100 text-rose-900 border-rose-500 border-dashed",
};

export const humanize = (code: string) =>
  code.toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h} h ${m} min` : `${m} min`;
}

export const formatTs = (iso: string) => iso.replace("T", " ").slice(0, 19);
