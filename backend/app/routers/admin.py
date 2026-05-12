"""Manual triggers for ingestion + scoring jobs.

Locked behind ADMIN_TOKEN (X-Admin-Token header) when the env var is set.
If unset, endpoints remain open for local-dev convenience.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.fx import refresh_fx_rates
from app.services.gdelt import refresh_country_tone
from app.services.ingestion import refresh_all_prices
from app.services.insider import refresh_insider_activity
from app.services.news_sentiment import refresh_news_sentiment
from app.services.reddit import refresh_reddit_mentions


async def require_admin(request: Request) -> None:
    """If ADMIN_TOKEN env var is set, require X-Admin-Token header to match.
    If unset, endpoints stay open (dev convenience).
    """
    if not settings.admin_enforced:
        return
    provided = request.headers.get("X-Admin-Token", "")
    if provided != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid or missing X-Admin-Token")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


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


@router.post("/refresh-insider")
def trigger_insider_refresh(db: Session = Depends(get_db)) -> dict:
    """Pull 30-day insider transactions per US stock from Finnhub."""
    return refresh_insider_activity(db)
