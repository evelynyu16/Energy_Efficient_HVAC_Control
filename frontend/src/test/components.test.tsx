import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";
import { ModeBadge } from "../components/ModeBadge";
import { RuntimeComparison } from "../components/RuntimeComparison";
import { validateSettings } from "../pages/SettingsPage";
import type { ControlSettings, RuntimeReport } from "../api/types";

const settings: ControlSettings = {
  lower_bound_c: 20, upper_bound_c: 24, hysteresis_c: 0.5, min_mode_duration_s: 300,
  vacancy_delay_s: 600, baseline_start: "08:00:00", baseline_end: "18:00:00",
};

describe("UI requirements", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {}))); // never resolves
  });

  it("labels every page as a simulation", () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole("note")).toHaveTextContent("SIMULATION");
  });

  it("shows mode and control source as text, not colour alone", () => {
    render(<ModeBadge mode="ECO" source="MANUAL" />);
    expect(screen.getByTestId("mode-badge")).toHaveTextContent("Mode: Eco (HVAC off)(Manual)");
  });

  it("reports N/A when baseline runtime is zero", () => {
    const zero = { heating_s: 0, cooling_s: 0, active_s: 0 };
    const report: RuntimeReport = {
      session_id: "x", status: "ENDED", records_processed: 1, total_records: 1,
      proposed: zero, baseline: zero, counted_s: 60, excluded_gap_s: 0, excluded_invalid_s: 0,
      excluded_manual_s: 0, reduction_pct: null, disclaimer: "not measured energy savings",
    };
    render(<RuntimeComparison report={report} />);
    expect(screen.getByTestId("reduction")).toHaveTextContent("N/A");
  });

  it("mirrors FR-07 settings validation", () => {
    expect(validateSettings(settings)).toEqual([]);
    expect(validateSettings({ ...settings, lower_bound_c: 24 })).not.toEqual([]);
    expect(validateSettings({ ...settings, hysteresis_c: 2 })).not.toEqual([]);
    expect(validateSettings({ ...settings, vacancy_delay_s: -1 })).not.toEqual([]);
  });
});
