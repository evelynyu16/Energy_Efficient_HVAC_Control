# Roomwise · Energy-Efficient HVAC Control
**Fanchao Yu and Minyuan Wang** · Single-room software simulation

## Run locally (macOS / Linux)
Use Python 3.12. From the extracted project folder:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m uvicorn server:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. The compiled English interface and the original UCI dataset are included; no Node installation or data download is needed for this path. Local, single-user classroom app. Stop with Ctrl+C. Windows: activate with .venv\Scripts\activate.

## Two-minute demonstration
1. Open Overview and click **Play**. Watch the timestamp and temperature; **Pause** freezes recorded time. **Step** processes one row.
2. In Settings, narrow the comfort range to 20–22 °C, save, and return to Overview. Watch for a Cooling command. Select Standby under Manual override, step once, then restore Automatic.
3. Select **New replay** to start from the beginning with current settings. **Run to end** processes all remaining rows. Visit Report to compare commanded heating/cooling minutes with the daily baseline. Select a previous session to inspect its settings changes and events.
4. For the reference result below, use defaults (20–24 °C, hysteresis 0.5 °C, minimum duration 5 min, vacancy delay 10 min, baseline 08:00–18:00), then start a new replay and run to end without manual intervention.

## Reference result
On all 20,560 readings: occupancy-aware **125.0 minutes**, baseline **1,215.1 minutes**, excluded **2,185.0 minutes** (including **2,183.0 minutes** in gaps). Each interval uses the previous command until the next sample. Gap and unavailable intervals and manual intervals count in neither policy. The baseline uses the same sampled thermostat, with schedule evaluated at each reading. Zero baseline yields N/A. Runtime differences are not measured electricity savings. Recorded temperatures do not respond to commands.

## Develop and verify
Python/FastAPI + SQLite; React/TypeScript + Recharts + CSS. With Node 24:
    
    npm ci
    npm run build
    python -m pip install -r requirements-dev.txt
    python -m pytest -q

Interactive endpoint reference: http://127.0.0.1:8000/docs. The React build is served by FastAPI. The local database is created on first launch. Override its location with HVAC_DB. The latest session and previous events persist across restarts. Playback advances while the dashboard is open; it is not a background hardware controller.

## Code map
- engine.py — import rules, deterministic thermostat, timers and runtime comparison.
- server.py — session API, SQLite storage, event history and static server.
- web/ — English dashboard, settings and reports; dist/ — compiled frontend.
- tests/ — boundary, import, manual, gap, history, performance/API tests.
- docs/ — SRS and an implementation-to-requirement map.
- data/ — UCI Occupancy Detection; see data/NOTICE.md.
