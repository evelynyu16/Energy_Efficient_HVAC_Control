# Occupancy-Aware HVAC Control Simulator

Course project (Fanchao Yu, Minyuan Wang). A web application that replays recorded office-room
temperature, humidity and occupancy readings and selects **simulated** HVAC modes with
configurable rules, then compares commanded heating/cooling time with a fixed-schedule baseline.

> **Simulation only.** Recorded temperatures do not respond to commands, and runtime differences
> are not measured energy savings.

- Requirements: [`docs/Energy_Efficient_HVAC_Control_SRS.pdf`](docs/Energy_Efficient_HVAC_Control_SRS.pdf)
- Architecture + agent prompt: [`docs/ARCHITECTURE_PROMPT.md`](docs/ARCHITECTURE_PROMPT.md)

## Stack

React + TypeScript + Tailwind + Recharts (Vite) · FastAPI + Pandas · SQLite · Pytest / Vitest ·
GitHub Actions

## Run locally

Backend (Python 3.11+):

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Frontend (Node 20+), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend.

## Dataset

Without extra steps the backend uses `data/sample/sample_occupancy.txt`, a **synthetic** file in
the UCI format for development. To use the real UCI Occupancy Detection dataset
(Candanedo, 2016), download it into `data/raw/`:

```bash
python scripts/fetch_dataset.py
```

## Tests

```bash
cd backend && ruff check . && pytest -q
cd frontend && npm run typecheck && npm test && npm run build
```
