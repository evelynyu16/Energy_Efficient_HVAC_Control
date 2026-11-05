from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.api.deps import settings_repo
from app.control.settings import ControlSettings
from app.repositories.settings_repo import SettingsRepository

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(repo: SettingsRepository = Depends(settings_repo)) -> dict:
    return repo.get().model_dump(mode="json")


@router.put("")
def put_settings(body: dict, repo: SettingsRepository = Depends(settings_repo)) -> dict:
    """FR-07: validate, persist, and record old/new values. Applies to the next session."""
    try:
        new = ControlSettings.model_validate({**repo.get().model_dump(), **body})
    except ValidationError as e:
        raise HTTPException(422, [err["msg"] for err in e.errors()]) from e
    changes = repo.save(new)
    return {"settings": new.model_dump(mode="json"), "changes": changes}


@router.get("/changes")
def settings_changes(repo: SettingsRepository = Depends(settings_repo)) -> list[dict]:
    return repo.changes()
