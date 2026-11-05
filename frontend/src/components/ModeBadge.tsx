import type { ControlSource, Mode } from "../api/types";
import { MODE_LABEL, MODE_STYLE } from "../lib";

export function ModeBadge({ mode, source }: { mode: Mode | null; source?: ControlSource }) {
  if (!mode) return <span className="text-slate-500">No mode yet</span>;
  return (
    <span
      data-testid="mode-badge"
      className={`inline-flex items-center gap-2 rounded border-2 px-3 py-1 font-semibold ${MODE_STYLE[mode]}`}
    >
      Mode: {MODE_LABEL[mode]}
      {source && <span className="text-xs font-normal">({source === "MANUAL" ? "Manual" : "Automatic"})</span>}
    </span>
  );
}
