"""Dev-only manual triggers for ingestion + scoring jobs.

Phase 1 keeps these unauthenticated for local-dev convenience. Lock down before deploying.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.fx import refresh_fx_rates
from app.services.gdelt import refresh_country_tone
from app.services.ingestion import refresh_all_prices
from app.services.news_sentiment import refresh_news_sentiment
from app.services.reddit import refresh_reddit_mentions

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh-fx")
def trigger_fx_refresh(db: Session = Depends(get_db)) -> dict:
    return refresh_fx_rates(db)


@router.post("/refresh-prices")
def trigger_price_refresh(period: str = "1y", db: Session = Depends(get_db)) -> dict[str, int]:
    return refresh_all_prices(db, period=period)


@router.post("/refresh-reddit")
def trigger_reddit_refresh(db: Session = Depends(get_db)) -> dict:
    """Pull today's Reddit mention counts across r/wallstreetbets, r/stocks, r/investing."""
    return refresh_reddit_mentions(db)


@router.post("/refresh-news")
def trigger_news_refresh(db: Session = Depends(get_db)) -> dict:
    """Pull per-ticker headlines via yfinance, run VADER, persist daily aggregates."""
    return refresh_news_sentiment(db)


@router.post("/refresh-gdelt")
def trigger_gdelt_refresh(db: Session = Depends(get_db)) -> dict:
    """Pull last 7 days of GDELT mean tone per country in the universe."""
    return refresh_country_tone(db)
