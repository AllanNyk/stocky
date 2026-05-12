from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.movers import movers as movers_service

router = APIRouter(prefix="/api", tags=["movers"])


@router.get("/movers")
def get_movers(
    lookback_days: int = Query(1, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    """Top picks today + biggest composite-score risers and fallers since N days ago."""
    return movers_service(db, lookback_days=lookback_days, limit=limit)
