// Mirrors backend/app/schemas.py and backend/app/control/*. Keep in sync.

export type Mode = "HEATING" | "COOLING" | "STANDBY" | "ECO" | "DATA_UNAVAILABLE";
export type ManualMode = Exclude<Mode, "DATA_UNAVAILABLE">;
export type ControlSource = "AUTO" | "MANUAL";
export type SessionStatus = "READY" | "RUNNING" | "PAUSED" | "ENDED" | "COMPLETED" | "INTERRUPTED";

export interface ControlSettings {
  lower_bound_c: number;
  upper_bound_c: number;
  hysteresis_c: number;
  min_mode_duration_s: number;
  vacancy_delay_s: number;
  baseline_start: string; // "HH:MM:SS"
  baseline_end: string;
}

export interface SensorRecord {
  index: number;
  timestamp: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  occupancy: 0 | 1 | null;
  valid: boolean;
  error: string | null;
}

export interface Decision {
  timestamp: string;
  mode: Mode;
  previous_mode: Mode | null;
  source: ControlSource;
  reason: string;
  detail: string;
}

export interface Frame {
  record: SensorRecord;
  proposed: Decision;
  baseline: Decision;
}

export interface SessionState {
  session_id: string;
  status: SessionStatus;
  cursor: number;
  total_records: number;
  dataset_label: string;
  settings: ControlSettings;
  manual_mode: ManualMode | null;
  control_source: ControlSource;
  current: Frame | null;
}

export interface StepResponse {
  frames: Frame[];
  state: SessionState;
}

export interface ControlEvent {
  id: number;
  session_id: string;
  controller: "PROPOSED" | "BASELINE";
  record_index: number | null;
  timestamp: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  occupancy: number | null;
  previous_mode: Mode | null;
  new_mode: Mode;
  source: ControlSource;
  reason: string;
  detail: string;
  logged_at: string;
}

export interface ModeTotals {
  heating_s: number;
  cooling_s: number;
  active_s: number;
}

export interface RuntimeReport {
  session_id: string;
  status: SessionStatus;
  records_processed: number;
  total_records: number;
  proposed: ModeTotals;
  baseline: ModeTotals;
  counted_s: number;
  excluded_gap_s: number;
  excluded_invalid_s: number;
  excluded_manual_s: number;
  reduction_pct: number | null;
  disclaimer: string;
}

export interface SessionSummary {
  id: string;
  created_at: string;
  ended_at: string | null;
  status: SessionStatus;
  dataset_label: string;
  total_records: number;
  cursor: number;
  settings: ControlSettings;
  report: RuntimeReport | null;
}

export interface DatasetReport {
  label: string;
  report: {
    files: string[];
    rows_read: number;
    exact_duplicates_removed: number;
    conflicting_timestamps: number;
    unplaceable_rows: number;
    invalid_records: number;
    valid_records: number;
    gaps_over_limit: number;
    first_timestamp: string | null;
    last_timestamp: string | null;
    issues: { source: string; row: number; timestamp: string | null; reason: string }[];
    issues_total: number;
  };
}
