// Thin typed wrapper over the FastAPI REST endpoints. All network access goes through here.
import type {
  ControlEvent, ControlSettings, DatasetReport, Decision, ManualMode, RuntimeReport,
  SessionState, SessionSummary, StepResponse,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = Array.isArray(body.detail) ? body.detail.join("; ") : String(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  dataset: () => request<DatasetReport>("/api/dataset"),

  getSettings: () => request<ControlSettings>("/api/settings"),
  putSettings: (s: Partial<ControlSettings>) =>
    request<{ settings: ControlSettings; changes: unknown[] }>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(s),
    }),

  startSession: () => post<SessionState>("/api/sessions"),
  listSessions: () => request<SessionSummary[]>("/api/sessions"),
  state: (id: string) => request<SessionState>(`/api/sessions/${id}/state`),
  play: (id: string) => post<SessionState>(`/api/sessions/${id}/play`),
  pause: (id: string) => post<SessionState>(`/api/sessions/${id}/pause`),
  step: (id: string, count: number) => post<StepResponse>(`/api/sessions/${id}/step`, { count }),
  manual: (id: string, mode: ManualMode, reason: string) =>
    post<Decision>(`/api/sessions/${id}/manual`, { mode, reason }),
  auto: (id: string, reason: string) => post<Decision>(`/api/sessions/${id}/auto`, { reason }),
  end: (id: string) => post<RuntimeReport>(`/api/sessions/${id}/end`),
  events: (id: string, controller: "PROPOSED" | "BASELINE" = "PROPOSED") =>
    request<{ items: ControlEvent[]; total: number }>(
      `/api/sessions/${id}/events?controller=${controller}&limit=1000`,
    ),
  report: (id: string) => request<RuntimeReport>(`/api/sessions/${id}/report`),
};
