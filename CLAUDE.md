# CLAUDE.md

Read `docs/ARCHITECTURE_PROMPT.md` before making changes. It defines the architecture, layer
boundaries, controller rules, API contract, and the requirement → code → test map for this
occupancy-aware HVAC control **simulator** (requirements: `docs/Energy_Efficient_HVAC_Control_SRS.pdf`).

Key rules:
- `backend/app/control/` is pure and deterministic: no FastAPI, SQL, pandas, wall clock or randomness.
- SQL only in `backend/app/repositories/`; `fetch` only in `frontend/src/api/client.ts`.
- Keep `frontend/src/api/types.ts` in sync with `backend/app/schemas.py`.
- Every page is labelled as a simulation; never present runtime differences as energy savings.

Checks before committing:
- `cd backend && ruff check . && pytest -q`
- `cd frontend && npm run typecheck && npm test && npm run build`
