# Architecture Prompt — Occupancy-Aware HVAC Control Simulator

> Paste everything below the line into Claude Code (or any coding agent) at the start of a
> working session. It describes the architecture already scaffolded in this repository, the rules
> every change must respect, and how each SRS requirement maps to code. Source of truth for the
> requirements: `docs/Energy_Efficient_HVAC_Control_SRS.pdf`.

---

## Role and goal

You are a senior engineer on a two-person course project (Fanchao Yu, Minyuan Wang). We are
building a **desktop web application that replays recorded office-room sensor data and simulates
HVAC control decisions** for one room and one simulated HVAC unit. Users monitor conditions,
override automatic decisions, review logs, and compare commanded heating/cooling time against a
fixed-schedule baseline.

This is a **simulation**. Recorded temperatures are fixed inputs and never respond to commands.
Runtime differences are a proxy and are **never** presented as measured energy savings. No
physical HVAC integration, multi-room optimisation, occupancy-model training, or machine
learning. Humidity is displayed only; it does not drive control.

## Tech stack (do not substitute)

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS 3, Recharts, React Router |
| Backend | Python 3.11+, FastAPI, Pydantic v2, REST + JSON |
| Data | Pandas for import/validation of the UCI Occupancy Detection text files |
| Database | SQLite via the standard-library `sqlite3` (no ORM) |
| Control | Deterministic Python state machine |
| Tests | Pytest (backend), Vitest + React Testing Library (frontend) |
| CI | GitHub Actions: ruff + pytest; tsc + vitest + vite build |

## Repository layout

```
backend/
  app/
    main.py                 # create_app(): wires DB, repositories, services, routers; CORS
    config.py               # paths (HVAC_DATA_DIR, HVAC_DB_PATH, HVAC_CORS_ORIGINS), MAX_GAP_SECONDS=300
    db.py                   # Database: one sqlite3 connection + lock, schema, tx() context manager
    schemas.py              # Pydantic API models  <-> frontend/src/api/types.ts
    control/                # PURE DOMAIN LOGIC — no FastAPI, no SQL, no pandas, no wall clock
      modes.py              # Mode, ControlSource, Reason enums; ACTIVE_MODES, MANUAL_MODES
      settings.py           # ControlSettings (frozen Pydantic) + FR-07 validation
      records.py            # SensorRecord, Decision (frozen dataclasses)
      thermostat.py         # thermostat_decision(): hysteresis only
      controller.py         # Controller state machine; Policy.OCCUPANCY | Policy.SCHEDULE
      runtime.py            # RuntimeAccumulator: FR-09/FR-10 totals and exclusions
    data/loader.py          # FR-01 import pipeline -> Dataset(records, ValidationReport)
    repositories/           # ALL SQL lives here
      settings_repo.py      # settings + settings_changes (old/new values)
      session_repo.py       # sessions + events
    services/
      dataset_service.py    # loads and caches the dataset (falls back to the bundled sample)
      playback.py           # PlaybackService: sessions, stepping, both controllers, logging
    api/                    # thin HTTP layer: validate -> call service -> map to schema
      deps.py, routes_data.py, routes_settings.py, routes_sessions.py
  tests/                    # pytest; one file per module + API integration tests
frontend/
  src/
    api/types.ts            # TS mirror of backend schemas
    api/client.ts           # the ONLY place that calls fetch()
    hooks/usePlayback.ts    # session lifecycle + step timer + rolling frame buffer
    components/             # SimulationBanner, ModeBadge, SensorReadout, PlaybackControls,
                            # ManualControl, TrendChart, RuntimeComparison
    pages/                  # DashboardPage, SettingsPage, HistoryPage
    lib.ts                  # MODE_LABEL (text), MODE_STYLE, formatters
    test/                   # Vitest setup + component tests
data/
  raw/                      # real UCI files (git-ignored); scripts/fetch_dataset.py
  sample/sample_occupancy.txt  # SYNTHETIC dev sample (has 1 duplicate, 1 invalid row, 1 gap)
scripts/                    # fetch_dataset.py, generate_sample_data.py
docs/                       # SRS PDF, this prompt
.github/workflows/ci.yml
```

### Dependency direction (enforce it)

```
api  ->  services  ->  control  (pure)
             |              ^
             v              |
       repositories     data/loader
             |
             v
            db
```

- `control/` imports nothing from `api`, `services`, `repositories`, `db`, `data`, FastAPI or pandas.
- Only `repositories/` contains SQL. Only `data/loader.py` uses pandas.
- Routes contain no business rules; they translate `PlaybackError`/`ValueError` to HTTP 409 and
  Pydantic errors to 422.
- Frontend components never call `fetch` directly; they go through `api/client.ts`.

## Domain model

**Modes:** `HEATING`, `COOLING`, `STANDBY`, `ECO`, `DATA_UNAVAILABLE`. A controller holds exactly
one mode, so heating and cooling can never be active together (FR-04).
**ControlSource:** `AUTO` | `MANUAL`. **Reason:** machine-readable enum on every decision, plus a
human-readable `detail` string.

**ControlSettings (defaults are demonstration assumptions, FR-05):**
lower 20.0 °C, upper 24.0 °C, hysteresis 0.5 °C (heating stops at 20.5, cooling stops at 23.5),
min mode duration 300 s, vacancy delay 600 s, baseline schedule 08:00–18:00 daily.
**Validation (FR-07):** lower < upper; durations ≥ 0; 0 ≤ hysteresis < (upper − lower)/2;
baseline start < end. Saving records one `settings_changes` row per changed field (old/new).
A session snapshots settings when it starts; edits apply to the next session (keeps replays
deterministic).

## Controller rules (`control/controller.py`) — priority order

1. **Invalid record** → `DATA_UNAVAILABLE` (reason `INVALID_INPUT`). **Gap > 5 min** since the
   previous record → `DATA_UNAVAILABLE` (reason `DATA_GAP`) on the record after the gap; vacancy
   tracking restarts from that record. Outranks manual mode (FR-06, FR-11).
2. **Manual override** → operator mode until "return to automatic"; bypasses the hold timer.
3. **Idle condition** → `ECO`, bypasses the hold timer.
   - `Policy.OCCUPANCY` (proposed): continuous vacancy ≥ `vacancy_delay_s` (dataset time).
   - `Policy.SCHEDULE` (baseline): timestamp outside `[baseline_start, baseline_end)`; ignores
     occupancy and never accepts manual commands.
4. **Thermostat with hysteresis** (`thermostat.py`) → HEATING/COOLING/STANDBY. A change between
   thermostat modes requires `min_mode_duration_s` in the current mode. Leaving `ECO`,
   `DATA_UNAVAILABLE` or the initial state bypasses the hold (reasons `REOCCUPIED`,
   `INSIDE_SCHEDULE`, `DATA_RESUMED`, `SESSION_START`).

Hard rules: all timing uses **dataset timestamps**, never `datetime.now()`. No randomness. Same
records + same settings ⇒ identical decision sequence (reliability NFR).

## Runtime comparison (`control/runtime.py`, FR-09/FR-10)

The decision in force after record *i* (including a manual command issued after it) covers
`[t_i, t_{i+1})`. For each interval: gap > 5 min → `excluded_gap_s`; either endpoint invalid →
`excluded_invalid_s`; proposed controller in MANUAL → `excluded_manual_s` (excluded from **both**
totals); otherwise add to `counted_s` and to heating/cooling totals of each controller.
`reduction_pct = (baseline − proposed) / baseline × 100`, `None` (UI shows "N/A") when baseline
is 0. Every report carries the "not measured energy savings" disclaimer.

## Data import (`data/loader.py`, FR-01)

UCI files (`datatraining.txt`, `datatest.txt`, `datatest2.txt`) have a quoted row-id column with
no header; drop it. Pipeline: read all → concat → drop exact duplicates → parse → rows with
unparseable timestamps are reported and dropped → timestamps with conflicting values become one
invalid record → validate (numeric temperature, humidity 0–100, occupancy ∈ {0,1}) → sort →
`SensorRecord` list with `valid`/`error`. Invalid rows stay in the stream so playback hits
`DATA_UNAVAILABLE`. The `ValidationReport` is exposed by `GET /api/dataset` before playback.
Light and CO2 are ignored for control.

## Persistence (`db.py`, SQLite)

- `settings(id=1, json, updated_at)` and `settings_changes(changed_at, field, old_value, new_value)`
- `sessions(id, created_at, ended_at, status, dataset_label, settings_json, total_records, cursor, report_json)`
- `events(session_id, controller PROPOSED|BASELINE, record_index, timestamp, temperature_c,
  humidity_pct, occupancy, previous_mode, new_mode, source, reason, detail, logged_at)`

Every mode change and every operator action is committed immediately (FR-08). Reset creates a
new session; old sessions/events are never deleted (FR-02). On startup, sessions left
READY/RUNNING/PAUSED become `INTERRUPTED` (their logs remain).

## REST API (prefix `/api`)

| Method & path | Purpose |
|---|---|
| `GET /health` | liveness, `simulation: true` |
| `GET /dataset` | validation report + invalid-row list (FR-01) |
| `GET /settings`, `PUT /settings`, `GET /settings/changes` | FR-07 |
| `POST /sessions` | start a new session (also Reset) |
| `GET /sessions`, `GET /sessions/{id}` | stored sessions incl. settings and final report |
| `GET /sessions/{id}/state` | live state: cursor, status, current frame, control source |
| `POST /sessions/{id}/play` / `pause` / `end` | playback lifecycle (FR-02) |
| `POST /sessions/{id}/step {count}` | advance N records; 409 unless RUNNING |
| `POST /sessions/{id}/manual {mode, reason}` / `auto {reason}` | FR-06 overrides |
| `GET /sessions/{id}/events?controller=PROPOSED|BASELINE` | FR-08 history |
| `GET /sessions/{id}/report` | FR-09/FR-10 comparison (live or stored) |

Playback is **pull-based**: the frontend calls `step` every 500 ms while RUNNING; pausing makes
the backend reject steps, so progression stops deterministically. The backend is the only source
of truth for controller state.

## Frontend rules

- Pages: **Dashboard** (playback controls, readings with units, mode badge, auto/manual,
  temperature and occupancy charts, manual override with a reason, report after end),
  **Settings** (all seven settings, client-side FR-07 mirror, backend authoritative),
  **History & Report** (session picker, parameters, runtime comparison, event table).
- `SimulationBanner` on every page. Modes, control source and reasons are always shown as
  **text**; colour is supplementary only (usability NFR).
- Keep `api/types.ts` in sync with `backend/app/schemas.py` whenever either changes.

## Requirement → code → test map

| Req | Code | Tests |
|---|---|---|
| FR-01 | `data/loader.py`, `routes_data.py` | `test_loader.py` |
| FR-02 | `services/playback.py` | `test_api.py::test_full_session_flow_and_persistence` |
| FR-03 | `SensorReadout`, `ModeBadge`, `ManualControl` | `components.test.tsx` |
| FR-04/05 | `thermostat.py`, `controller.py` | `test_thermostat.py`, `test_controller.py` |
| FR-06 | `controller.py` (manual, vacancy) | `test_controller.py` |
| FR-07 | `control/settings.py`, `settings_repo.py`, `SettingsPage` | `test_settings.py`, `test_api.py`, `components.test.tsx` |
| FR-08 | `session_repo.py` | `test_api.py` (restart persistence) |
| FR-09/10 | `runtime.py`, `Policy.SCHEDULE` | `test_runtime.py`, `test_api.py::test_full_playback_is_deterministic` |
| FR-11 | `controller.py` | `test_controller.py::test_gap_over_five_minutes_is_data_unavailable` |
| NFR reliability | no wall clock / randomness in `control/` | determinism tests |
| NFR transparency | `SimulationBanner`, report `disclaimer` | `components.test.tsx` |

## Assumptions to confirm with the instructor (keep documented if changed)

- A-1: Leaving ECO on reoccupancy bypasses the minimum mode duration ("vacancy transition").
- A-2: The record immediately after a > 5 min gap is treated as `DATA_UNAVAILABLE`; control
  resumes on the next valid record. Vacancy must be re-observed after a gap.
- A-3: An interval counts toward runtime only if both endpoint records are valid.
- A-4: The baseline uses the same thermostat, hysteresis, hold and data-unavailable rules, is ECO
  outside the schedule window, and never receives manual commands.
- A-5: Settings changes apply to the next session, not the one in progress.
- A-6: Live sessions are in memory; after a server restart they are marked INTERRUPTED (logs and
  any stored report remain).

## How to work in this repo

1. Read the relevant SRS requirement and the matching row in the map above before coding.
2. Put rules in `control/` first, with a pytest that covers the boundary (e.g. 19.99/20.0/20.5,
   exactly 5 min vs 5.5 min, exactly 10 min of vacancy). Then expose it via service → route →
   schema → `types.ts` → UI.
3. Never introduce wall-clock time, randomness, or ML into control decisions.
4. Never word the UI or reports as measured energy savings.
5. Before committing: `cd backend && ruff check . && pytest -q` and
   `cd frontend && npm run typecheck && npm test && npm run build`.
6. Small, focused commits referencing the requirement ID (e.g. `FR-06: ...`).

## Commands

```bash
# backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
# frontend
cd frontend && npm install && npm run dev                                  # http://localhost:5173
# real dataset (optional; otherwise the synthetic sample is used)
python scripts/fetch_dataset.py
```

## Remaining work by SRS timeline

- Week 1: confirm assumptions A-1…A-6; Jira tasks per FR; Confluence page linking this prompt.
- Weeks 2–5: core features are scaffolded and tested; extend UI polish (responsive layout,
  dataset validation panel on the Dashboard, event-table paging/filtering, baseline event view).
- Weeks 6–7: add boundary cases for every FR, a 100-sequential-update performance check
  (< 1 s per displayed record), usability review.
- Week 8: user guide, API notes (FastAPI `/docs`), final report, demo script.
