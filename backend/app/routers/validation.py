"""Model-validation endpoints: 'does the prediction model work?'."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PickStrategy
from app.services.snapshots import (
    forward_returns_for_strategy,
    latest_top_picks,
    run_backtest,
    run_daily_snapshot,
)

router = APIRouter(prefix="/api/validation", tags=["validation"])

HORIZONS = [1, 7, 30, 90]


@router.post("/run-snapshot")
def trigger_snapshot(db: Session = Depends(get_db)) -> dict:
    """Manual trigger — wired to scheduler in task #11 for daily auto-runs."""
    return run_daily_snapshot(db)


@router.post("/run-backtest")
def trigger_backtest(days: int = 90, db: Session = Depends(get_db)) -> dict:
    """Replay the last N days using only signals that have historical backdata.

    P/E percentile and WSB mention-delta return confidence=0 for past dates, so the
    composite during backtest is effectively momentum-only — honest about what
    could've been known at the time. Use to fill the validation dashboard.
    """
    return run_backtest(db, days=days)


@router.get("/performance")
def model_performance(db: Session = Depends(get_db)) -> dict:
    return {
        strat.value: forward_returns_for_strategy(db, strat.value, HORIZONS)
        for strat in PickStrategy
    }


@router.get("/latest-picks")
def latest_picks(db: Session = Depends(get_db)) -> dict:
    return {strat.value: latest_top_picks(db, strat.value) for strat in PickStrategy}
