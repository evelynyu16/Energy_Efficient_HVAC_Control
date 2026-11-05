"""Dependency wiring: services live on app.state and are fetched per request."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.dataset_service import DatasetService
from app.services.playback import PlaybackService, SimulationSession


def playback(request: Request) -> PlaybackService:
    return request.app.state.playback


def datasets(request: Request) -> DatasetService:
    return request.app.state.datasets


def settings_repo(request: Request) -> SettingsRepository:
    return request.app.state.settings_repo


def session_repo(request: Request) -> SessionRepository:
    return request.app.state.session_repo


def live_session(session_id: str, request: Request) -> SimulationSession:
    s = request.app.state.playback.get(session_id)
    if s is None:
        raise HTTPException(404, f"no live session {session_id}")
    return s
