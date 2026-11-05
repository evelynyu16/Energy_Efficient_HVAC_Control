import type { RuntimeReport } from "../api/types";
import { formatDuration } from "../lib";

export function RuntimeComparison({ report }: { report: RuntimeReport }) {
  const row = (label: string, p: number, b: number) => (
    <tr className="border-t">
      <th scope="row" className="py-1 pr-4 text-left font-normal">{label}</th>
      <td className="pr-4">{formatDuration(p)}</td>
      <td>{formatDuration(b)}</td>
    </tr>
  );
  return (
    <section aria-label="Runtime comparison" className="rounded border bg-white p-3">
      <h2 className="mb-2 font-semibold">Commanded runtime: occupancy-aware vs fixed schedule</h2>
      <table className="text-sm">
        <thead>
          <tr>
            <th />
            <th className="pr-4 text-left">Occupancy-aware</th>
            <th className="text-left">Fixed schedule</th>
          </tr>
        </thead>
        <tbody>
          {row("Heating", report.proposed.heating_s, report.baseline.heating_s)}
          {row("Cooling", report.proposed.cooling_s, report.baseline.cooling_s)}
          {row("Total heating + cooling", report.proposed.active_s, report.baseline.active_s)}
        </tbody>
      </table>
      <p className="mt-2 text-sm">
        Runtime reduction:{" "}
        <strong data-testid="reduction">
          {report.reduction_pct === null ? "N/A (baseline runtime is zero)" : `${report.reduction_pct.toFixed(1)} %`}
        </strong>
      </p>
      <p className="text-xs text-slate-600">
        Counted: {formatDuration(report.counted_s)} · Excluded — data gaps {formatDuration(report.excluded_gap_s)},
        invalid data {formatDuration(report.excluded_invalid_s)}, manual override{" "}
        {formatDuration(report.excluded_manual_s)}
      </p>
      <p className="mt-1 text-xs italic text-slate-600">{report.disclaimer}</p>
    </section>
  );
}
