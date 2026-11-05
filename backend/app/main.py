"""FastAPI application factory.  Run: uvicorn app.main:app --reload  (from backend/)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import routes_data, routes_sessions, routes_settings
from app.db import Database
from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.dataset_service import DatasetService
from app.services.playback import PlaybackService


def create_app(
    db_path: Path | str | None = None,
    data_dir: Path | None = None,
    fallback_dir: Path | None = config.SAMPLE_DATA_DIR,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = Database(db_path or config.DB_PATH)
        session_repo = SessionRepository(db)
        session_repo.mark_interrupted()
        app.state.db = db
        app.state.session_repo = session_repo
        app.state.settings_repo = SettingsRepository(db)
        app.state.datasets = DatasetService(data_dir or config.DATA_DIR, fallback_dir)
        app.state.playback = PlaybackService(session_repo)
        yield
        db.close()

    app = FastAPI(
        title="Occupancy-Aware HVAC Control Simulator",
        description="SIMULATION ONLY. Recorded sensor data is replayed; HVAC outputs are "
                    "simulated commands. Runtime differences are not measured energy savings.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "simulation": True}

    app.include_router(routes_data.router)
    app.include_router(routes_settings.router)
    app.include_router(routes_sessions.router)
    return app


app = create_app()
