from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.deps import datasets
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("")
def dataset_report(
    issues_limit: int = Query(100, ge=0, le=5000), svc: DatasetService = Depends(datasets)
) -> dict:
    """FR-01: validation summary shown before playback, including invalid rows."""
    ds = svc.get()
    report = asdict(ds.report)
    report["issues_total"] = len(report["issues"])
    report["issues"] = report["issues"][:issues_limit]
    return {"label": ds.label, "report": report}
