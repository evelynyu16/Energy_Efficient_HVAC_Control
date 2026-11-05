from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import datasets, live_session, playback, session_repo, settings_repo
from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas import (
    AutoRequest,
    DecisionOut,
    EventPage,
    FrameOut,
    ManualRequest,
    SessionStateOut,
    StepRequest,
    StepResponse,
)
from app.services.dataset_service import DatasetService
from app.services.playback import PlaybackError, PlaybackService, SimulationSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _guard(fn, *args):
    try:
        return fn(*args)
    except (PlaybackError, ValueError) as e:
        raise HTTPException(409, str(e)) from e


@router.post("", response_model=SessionStateOut, status_code=201)
def start_session(
    svc: PlaybackService = Depends(playback),
    ds: DatasetService = Depends(datasets),
    settings: SettingsRepository = Depends(settings_repo),
) -> SessionStateOut:
    """Start a new session (also used for Reset). Earlier sessions and logs are kept."""
    return SessionStateOut.of(svc.create(ds.get(), settings.get()))


@router.get("")
def list_sessions(repo: SessionRepository = Depends(session_repo)) -> list[dict]:
    return repo.list()


@router.get("/{session_id}")
def session_detail(session_id: str, repo: SessionRepository = Depends(session_repo)) -> dict:
    row = repo.get(session_id)
    if row is None:
        raise HTTPException(404, "session not found")
    return row


@router.get("/{session_id}/state", response_model=SessionStateOut)
def state(s: SimulationSession = Depends(live_session)) -> SessionStateOut:
    return SessionStateOut.of(s)


@router.post("/{session_id}/play", response_model=SessionStateOut)
def play(s: SimulationSession = Depends(live_session),
         svc: PlaybackService = Depends(playback)) -> SessionStateOut:
    _guard(svc.play, s)
    return SessionStateOut.of(s)


@router.post("/{session_id}/pause", response_model=SessionStateOut)
def pause(s: SimulationSession = Depends(live_session),
          svc: PlaybackService = Depends(playback)) -> SessionStateOut:
    _guard(svc.pause, s)
    return SessionStateOut.of(s)


@router.post("/{session_id}/step", response_model=StepResponse)
def step(body: StepRequest, s: SimulationSession = Depends(live_session),
         svc: PlaybackService = Depends(playback)) -> StepResponse:
    frames = _guard(svc.step, s, body.count)
    return StepResponse(frames=[FrameOut.of(f) for f in frames], state=SessionStateOut.of(s))


@router.post("/{session_id}/manual", response_model=DecisionOut)
def manual(body: ManualRequest, s: SimulationSession = Depends(live_session),
           svc: PlaybackService = Depends(playback)) -> DecisionOut:
    return DecisionOut.of(_guard(svc.set_manual, s, body.mode, body.reason))


@router.post("/{session_id}/auto", response_model=DecisionOut)
def auto(body: AutoRequest, s: SimulationSession = Depends(live_session),
         svc: PlaybackService = Depends(playback)) -> DecisionOut:
    return DecisionOut.of(_guard(svc.release_manual, s, body.reason))


@router.post("/{session_id}/end")
def end(s: SimulationSession = Depends(live_session),
        svc: PlaybackService = Depends(playback)) -> dict:
    return svc.end(s)


@router.get("/{session_id}/events", response_model=EventPage)
def events(
    session_id: str,
    controller: str = Query("PROPOSED", pattern="^(PROPOSED|BASELINE)$"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repo: SessionRepository = Depends(session_repo),
) -> EventPage:
    items, total = repo.events(session_id, controller, limit, offset)
    return EventPage(items=items, total=total)


@router.get("/{session_id}/report")
def report(session_id: str, svc: PlaybackService = Depends(playback),
           repo: SessionRepository = Depends(session_repo)) -> dict:
    """FR-09/FR-10: live report for an active session, stored report for a past one."""
    live = svc.get(session_id)
    if live is not None:
        return svc.report(live)
    row = repo.get(session_id)
    if row is None or row["report"] is None:
        raise HTTPException(404, "no report for this session")
    return row["report"]
