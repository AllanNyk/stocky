"""Model-validation endpoints: 'does the prediction model work?'."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PickStrategy
from app.services.snapshots import (
    forward_returns_for_strategy,
    latest_top_picks,
    run_daily_snapshot,
)

router = APIRouter(prefix="/api/validation", tags=["validation"])

HORIZONS = [1, 7, 30, 90]


@router.post("/run-snapshot")
def trigger_snapshot(db: Session = Depends(get_db)) -> dict:
    """Manual trigger — wired to scheduler in task #11 for daily auto-runs."""
    return run_daily_snapshot(db)


@router.get("/performance")
def model_performance(db: Session = Depends(get_db)) -> dict:
    return {
        strat.value: forward_returns_for_strategy(db, strat.value, HORIZONS)
        for strat in PickStrategy
    }


@router.get("/latest-picks")
def latest_picks(db: Session = Depends(get_db)) -> dict:
    return {strat.value: latest_top_picks(db, strat.value) for strat in PickStrategy}
