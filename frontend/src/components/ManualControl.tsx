import { useState } from "react";
import type { ManualMode, SessionState } from "../api/types";
import { MODE_LABEL } from "../lib";

const MODES: ManualMode[] = ["HEATING", "COOLING", "STANDBY", "ECO"];

interface Props {
  state: SessionState | null;
  onManual: (mode: ManualMode, reason: string) => void;
  onAuto: (reason: string) => void;
}

export function ManualControl({ state, onManual, onAuto }: Props) {
  const [mode, setMode] = useState<ManualMode>("STANDBY");
  const [reason, setReason] = useState("");
  const disabled = !state || ["ENDED", "COMPLETED"].includes(state.status);
  return (
    <fieldset className="rounded border bg-white p-3" disabled={disabled}>
      <legend className="px-1 text-sm font-semibold">
        Control: {state?.control_source === "MANUAL" ? `Manual (${MODE_LABEL[state.manual_mode!]})` : "Automatic"}
      </legend>
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm">
          Manual mode{" "}
          <select aria-label="Manual mode" className="rounded border px-1 py-0.5" value={mode}
            onChange={(e) => setMode(e.target.value as ManualMode)}>
            {MODES.map((m) => <option key={m} value={m}>{MODE_LABEL[m]}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Reason{" "}
          <input aria-label="Reason" className="rounded border px-1 py-0.5" value={reason}
            onChange={(e) => setReason(e.target.value)} placeholder="e.g. visitor arriving" />
        </label>
        <button className="btn" onClick={() => onManual(mode, reason)}>Apply manual mode</button>
        <button className="btn" onClick={() => onAuto(reason)}
          disabled={state?.control_source !== "MANUAL"}>Return to automatic</button>
      </div>
    </fieldset>
  );
}
